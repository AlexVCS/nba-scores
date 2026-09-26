"""Bounded, thread-safe in-memory cache with per-entry expiry and request coalescing.

Values are cached per process only. Lifetimes are chosen at insertion from the
freshly loaded value, reads never extend them, and failed loads are never
cached. Pass ``copy`` to hand every reader its own copy of mutable values;
otherwise values must be treated as read-only.
"""

import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Callable, Generic, Hashable, TypeVar

K = TypeVar("K", bound=Hashable)
V = TypeVar("V")


class LoadInProgressError(Exception):
    """Raised for non-waiting lookups when another caller is already loading the key."""


@dataclass
class _Entry(Generic[V]):
    value: V
    expires_at: float


@dataclass
class _Flight(Generic[V]):
    tag: Any
    done: threading.Event = field(default_factory=threading.Event)
    value: V | None = None
    error: BaseException | None = None


class TTLCache(Generic[K, V]):
    def __init__(
        self,
        max_entries: int,
        *,
        clock: Callable[[], float] | None = None,
        copy: Callable[[V], V] | None = None,
    ):
        if max_entries < 1:
            raise ValueError("max_entries must be >= 1")
        self.max_entries = max_entries
        self._clock = clock
        self._copy = copy
        self._entries: OrderedDict[K, _Entry[V]] = OrderedDict()
        self._flights: dict[K, _Flight[V]] = {}
        self._lock = threading.Lock()

    def _now(self) -> float:
        return self._clock() if self._clock else time.monotonic()

    def _isolated(self, value: V) -> V:
        return self._copy(value) if self._copy else value

    def _live_entry(self, key: K) -> _Entry[V] | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        if entry.expires_at <= self._now():
            del self._entries[key]
            return None
        return entry

    def _store(self, key: K, value: V, ttl_seconds: float) -> None:
        if ttl_seconds <= 0:
            return
        now = self._now()
        self._entries.pop(key, None)
        for stale in [k for k, e in self._entries.items() if e.expires_at <= now]:
            del self._entries[stale]
        while len(self._entries) >= self.max_entries:
            self._entries.popitem(last=False)
        self._entries[key] = _Entry(value, now + ttl_seconds)

    def get(self, key: K) -> V | None:
        with self._lock:
            entry = self._live_entry(key)
        return self._isolated(entry.value) if entry else None

    def expires_in(self, key: K) -> float | None:
        with self._lock:
            entry = self._live_entry(key)
            return entry.expires_at - self._now() if entry else None

    def set(self, key: K, value: V, ttl_seconds: float) -> None:
        with self._lock:
            self._store(key, value, ttl_seconds)

    def pop(self, key: K) -> None:
        with self._lock:
            self._entries.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)

    def get_or_load(
        self,
        key: K,
        loader: Callable[[], V],
        ttl: Callable[[V], float],
        *,
        accept: Callable[[V], bool] | None = None,
        wait: bool = True,
        tag: Any = None,
        retry_after: Callable[[Any], bool] | None = None,
    ) -> V:
        """Return a live cached value or load it, sharing one load per key.

        ``accept`` rejects cached or shared values this caller cannot use, in
        which case it loads again. ``wait=False`` raises LoadInProgressError
        instead of joining another caller's load. When a joined load fails,
        its error is shared unless ``retry_after(flight_tag)`` says that load
        used a weaker policy than this caller, in which case it loads again.
        """
        while True:
            with self._lock:
                entry = self._live_entry(key)
                hit = entry is not None and (accept is None or accept(entry.value))
                if not hit:
                    flight = self._flights.get(key)
                    leader = flight is None
                    if leader:
                        flight = _Flight(tag=tag)
                        self._flights[key] = flight
                    elif not wait:
                        raise LoadInProgressError(key)

            # Copy outside the lock so large values do not block other keys.
            if hit:
                return self._isolated(entry.value)
            if leader:
                return self._isolated(self._lead(key, flight, loader, ttl))

            flight.done.wait()
            if flight.error is not None:
                if retry_after is not None and retry_after(flight.tag):
                    continue
                raise flight.error
            if accept is None or accept(flight.value):
                return self._isolated(flight.value)

    def _lead(self, key: K, flight: _Flight[V], loader: Callable[[], V], ttl: Callable[[V], float]) -> V:
        try:
            value = loader()
            lifetime = ttl(value)
        except BaseException as error:
            with self._lock:
                self._flights.pop(key, None)
            flight.error = error
            flight.done.set()
            raise
        with self._lock:
            self._store(key, value, lifetime)
            self._flights.pop(key, None)
        flight.value = value
        flight.done.set()
        return value
