"""Per-process Ask request rates and bounded synchronous work."""

from __future__ import annotations

import hashlib
import secrets
import threading
import time
from collections import OrderedDict, deque
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from typing import Callable, TypeVar

T = TypeVar("T")


class AskRateLimited(Exception):
    pass


class AskBusy(Exception):
    pass


class AskTimeout(Exception):
    pass


class AskLimits:
    def __init__(self, per_client_per_minute: int = 10, per_worker_per_minute: int = 60,
                 max_in_flight: int = 2, *, clock: Callable[[], float] | None = None):
        if min(per_client_per_minute, per_worker_per_minute, max_in_flight) < 1:
            raise ValueError("Ask limits must be positive")
        self.per_client_per_minute = per_client_per_minute
        self.per_worker_per_minute = per_worker_per_minute
        self._clock = clock or time.monotonic
        self._salt = secrets.token_bytes(16)
        self._rates: OrderedDict[str, deque[float]] = OrderedDict()
        self._all: deque[float] = deque()
        self._lock = threading.Lock()
        self._slots = threading.BoundedSemaphore(max_in_flight)
        self._pool = ThreadPoolExecutor(max_workers=max_in_flight, thread_name_prefix="ask-work")

    def check_rate(self, client_id: str) -> None:
        client = hashlib.sha256(self._salt + client_id.encode()).hexdigest()
        now = self._clock()
        with self._lock:
            while self._all and now - self._all[0] >= 60:
                self._all.popleft()
            if len(self._all) >= self.per_worker_per_minute:
                raise AskRateLimited("Ask request rate exceeded")
            events = self._rates.get(client)
            if events is None:
                while len(self._rates) >= 1024:
                    self._rates.popitem(last=False)
                events = deque()
                self._rates[client] = events
            else:
                self._rates.move_to_end(client)
                while events and now - events[0] >= 60:
                    events.popleft()
                if len(events) >= self.per_client_per_minute:
                    raise AskRateLimited("Ask request rate exceeded")
            events.append(now)
            self._all.append(now)

    def run_bounded(self, work: Callable[[], T], timeout_seconds: float = 20) -> T:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if not self._slots.acquire(blocking=False):
            raise AskBusy("Ask workers busy")
        try:
            future = self._pool.submit(work)
        except Exception:
            self._slots.release()
            raise
        future.add_done_callback(lambda _: self._slots.release())
        try:
            return future.result(timeout=timeout_seconds)
        except FutureTimeout as exc:
            future.cancel()
            raise AskTimeout("Ask response deadline exceeded") from exc
