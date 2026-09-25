"""Small, process-safe controls for the natural-language ask endpoint."""

from __future__ import annotations

import fcntl
import hashlib
import json
import math
import os
import tempfile
import threading
import time
import uuid
from collections import OrderedDict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generic, TypeVar


class AskLimitsError(RuntimeError):
    pass


class RateLimitError(AskLimitsError):
    pass


class BudgetLimitError(AskLimitsError):
    pass


class BudgetUnavailable(AskLimitsError):
    pass


@dataclass(frozen=True)
class Reservation:
    id: str
    model: str
    reserved_usd: float
    input_tokens_reserved: int
    output_tokens_reserved: int
    day: str


def _positive_env(name: str) -> float | None:
    value = os.getenv(name)
    if value is None:
        return None
    try:
        number = float(value)
    except ValueError as error:
        raise BudgetUnavailable(f"{name} must be numeric") from error
    if not math.isfinite(number) or number <= 0:
        raise BudgetUnavailable(f"{name} must be finite and positive")
    return number


def _prices(model: str) -> tuple[float, float]:
    normalized = model.casefold()
    known_prices = {
        "gpt-4.1-mini": (0.4, 1.6),
        "gpt-4.1-mini-2025-04-14": (0.4, 1.6),
        "gpt-4.1-nano": (0.1, 0.4),
        "gpt-4.1-nano-2025-04-14": (0.1, 0.4),
    }
    if os.getenv("ASK_PARSER_PROVIDER", "openai") == "openai" and normalized in known_prices:
        return known_prices[normalized]
    input_price = _positive_env("ASK_INPUT_USD_PER_MILLION")
    output_price = _positive_env("ASK_OUTPUT_USD_PER_MILLION")
    if input_price is None or output_price is None:
        raise BudgetUnavailable("Unknown model requires explicit per-million-token prices")
    return input_price, output_price


def _payload_tokens(payload: Any) -> int:
    if isinstance(payload, bytes):
        size = len(payload)
    else:
        size = len(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    return size + 2048


class Budget:
    """Daily list-price USD guard, before discounts, safe across worker processes."""

    def __init__(self, state_dir: str | os.PathLike[str] | None = None, daily_budget_usd: float | None = None):
        self.state_dir = Path(state_dir or os.getenv("ASK_STATE_DIR", Path(__file__).parents[1] / ".ask-state"))
        self.ledger_path = self.state_dir / "budget.json"
        self.lock_path = self.state_dir / "budget.lock"
        configured_budget = _positive_env("ASK_DAILY_BUDGET_USD")
        self.daily_budget_usd = daily_budget_usd if daily_budget_usd is not None else (configured_budget or 1.0)
        if not isinstance(self.daily_budget_usd, (int, float)) or isinstance(self.daily_budget_usd, bool) or not math.isfinite(self.daily_budget_usd) or self.daily_budget_usd < 0:
            raise BudgetUnavailable("ASK_DAILY_BUDGET_USD must be finite and nonnegative")

    def _with_lock(self, callback):
        try:
            self.state_dir.mkdir(parents=True, exist_ok=True)
            with self.lock_path.open("a+") as lock_file:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                try:
                    return callback()
                finally:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        except BudgetUnavailable:
            raise
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
            raise BudgetUnavailable("Budget ledger is unavailable") from error

    def _read(self) -> dict[str, Any]:
        if not self.ledger_path.exists():
            return {"day": self._day(), "spent_usd": 0.0, "reserved_usd": 0.0, "reservations": {}}
        try:
            data = json.loads(self.ledger_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError) as error:
            raise BudgetUnavailable("Budget ledger is corrupt or unreadable") from error
        if not isinstance(data, dict) or not isinstance(data.get("reservations"), dict):
            raise BudgetUnavailable("Budget ledger has an invalid shape")
        for field in ("day", "spent_usd", "reserved_usd"):
            if field not in data:
                raise BudgetUnavailable("Budget ledger has an invalid shape")
        if not isinstance(data["day"], str):
            raise BudgetUnavailable("Budget ledger has an invalid day")
        for field in ("spent_usd", "reserved_usd"):
            value = data[field]
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value < 0:
                raise BudgetUnavailable("Budget ledger has invalid totals")
        reservation_total = 0.0
        for item in data["reservations"].values():
            if not isinstance(item, dict):
                raise BudgetUnavailable("Budget ledger has invalid reservations")
            value = item.get("reserved_usd")
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value < 0:
                raise BudgetUnavailable("Budget ledger has invalid reservations")
            reservation_total += float(value)
        if not math.isclose(reservation_total, float(data["reserved_usd"]), rel_tol=1e-9, abs_tol=1e-12):
            raise BudgetUnavailable("Budget ledger totals do not match reservations")
        if data.get("day") != self._day():
            data = {"day": self._day(), "spent_usd": 0.0, "reserved_usd": 0.0, "reservations": {}}
        return data

    @staticmethod
    def _day() -> str:
        return datetime.now(timezone.utc).date().isoformat()

    def _write(self, data: dict[str, Any]) -> None:
        try:
            fd, temp_name = tempfile.mkstemp(prefix="budget-", dir=self.state_dir)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as temp_file:
                    json.dump(data, temp_file, separators=(",", ":"))
                    temp_file.flush()
                    os.fsync(temp_file.fileno())
                os.replace(temp_name, self.ledger_path)
                directory_fd = os.open(self.state_dir, os.O_RDONLY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
            finally:
                if os.path.exists(temp_name):
                    os.unlink(temp_name)
        except OSError as error:
            raise BudgetUnavailable("Budget ledger cannot be written") from error

    def reserve(self, payload: Any, model: str) -> Reservation:
        input_price, output_price = _prices(model)
        input_tokens = _payload_tokens(payload)
        output_tokens = int(payload.get("max_output_tokens", 0)) if isinstance(payload, dict) else 0
        if output_tokens <= 0:
            raise BudgetUnavailable("Request payload must set a positive max_output_tokens")
        amount = input_tokens * input_price / 1_000_000 + output_tokens * output_price / 1_000_000

        def reserve_locked():
            data = self._read()
            available = self.daily_budget_usd - float(data["spent_usd"]) - float(data["reserved_usd"])
            if amount > available:
                raise BudgetLimitError("Daily ask budget exhausted")
            reservation_id = uuid.uuid4().hex
            data["reserved_usd"] = float(data["reserved_usd"]) + amount
            data["reservations"][reservation_id] = {"model": model, "reserved_usd": amount, "input_tokens": input_tokens, "output_tokens": output_tokens}
            self._write(data)
            return Reservation(reservation_id, model, amount, input_tokens, output_tokens, data["day"])

        return self._with_lock(reserve_locked)

    def settle(self, reservation: Reservation, usage: Any) -> None:
        if usage is None:
            return
        input_tokens = usage.get("input_tokens") if isinstance(usage, dict) else getattr(usage, "input_tokens", None)
        output_tokens = usage.get("output_tokens") if isinstance(usage, dict) else getattr(usage, "output_tokens", None)
        if not isinstance(input_tokens, int) or input_tokens < 0 or not isinstance(output_tokens, int) or output_tokens < 0:
            return
        input_price, output_price = _prices(reservation.model)
        actual = input_tokens * input_price / 1_000_000 + output_tokens * output_price / 1_000_000

        def settle_locked():
            data = self._read()
            raw = data["reservations"].pop(reservation.id, None)
            if raw is None:
                return
            reserved = float(raw["reserved_usd"])
            data["reserved_usd"] = max(0.0, float(data["reserved_usd"]) - reserved)
            data["spent_usd"] = float(data["spent_usd"]) + actual
            self._write(data)

        self._with_lock(settle_locked)


class RateLimiter:
    def __init__(self, per_ip: int = 10, global_limit: int = 60, window_seconds: int = 60, max_ips: int = 1024):
        self.per_ip, self.global_limit, self.window_seconds, self.max_ips = per_ip, global_limit, window_seconds, max_ips
        self._lock = threading.Lock()
        self._ips: OrderedDict[str, deque[float]] = OrderedDict()
        self._global: deque[float] = deque()

    def check(self, ip: str) -> None:
        now = time.monotonic()
        with self._lock:
            while self._global and now - self._global[0] >= self.window_seconds:
                self._global.popleft()
            events = self._ips.setdefault(ip, deque())
            self._ips.move_to_end(ip)
            while events and now - events[0] >= self.window_seconds:
                events.popleft()
            if len(self._ips) > self.max_ips:
                self._ips.popitem(last=False)
            if len(events) >= self.per_ip or len(self._global) >= self.global_limit:
                raise RateLimitError("Ask request rate limit exceeded")
            events.append(now)
            self._global.append(now)


T = TypeVar("T")


class TTLCache(Generic[T]):
    def __init__(self, max_entries: int = 256, version: str = "1"):
        self.max_entries = max_entries
        self.version = version
        self._lock = threading.Lock()
        self._entries: OrderedDict[str, tuple[float | None, str, T]] = OrderedDict()

    @staticmethod
    def key(value: Any) -> str:
        return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def get(self, key: str) -> T | None:
        with self._lock:
            item = self._entries.get(key)
            if item is None:
                return None
            expires, version, value = item
            if version != self.version or (expires is not None and time.monotonic() >= expires):
                self._entries.pop(key, None)
                return None
            self._entries.move_to_end(key)
            return value

    def set(self, key: str, value: T, ttl_seconds: float | None = None) -> None:
        with self._lock:
            expires = None if ttl_seconds is None else time.monotonic() + ttl_seconds
            self._entries[key] = (expires, self.version, value)
            self._entries.move_to_end(key)
            while len(self._entries) > self.max_entries:
                self._entries.popitem(last=False)

    def put(self, key: str, value: T, ttl: float | None = None) -> None:
        self.set(key, value, ttl)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def invalidate_version(self, version: str) -> None:
        with self._lock:
            self.version = version
            self._entries.clear()
