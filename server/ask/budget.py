"""Durable UTC daily spend guard shared by backend worker processes."""

from __future__ import annotations

import fcntl
import json
import math
import os
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from server.ask.interpreters.pricing import price_for


class BudgetExhausted(Exception):
    pass


class BudgetUnavailable(Exception):
    pass


@dataclass(frozen=True)
class Reservation:
    id: str
    day: str
    model: str
    amount_usd: float


class DailyBudget:
    """Reserve before a paid call; unknown billing consumes the full reservation.

    Reservations from a previous UTC day remain in the ledger until settled.
    A crashed worker leaves its current-day reservation in place, failing safe.
    """

    def __init__(self, state_dir: str | Path | None = None, daily_budget_usd: float = 1.0,
                 *, clock: Callable[[], datetime] | None = None):
        if (isinstance(daily_budget_usd, bool) or not isinstance(daily_budget_usd, (int, float))
                or not math.isfinite(daily_budget_usd) or daily_budget_usd < 0):
            raise ValueError("daily budget must be finite and nonnegative")
        self.state_dir = Path(state_dir) if state_dir is not None else Path(__file__).resolve().parents[1] / ".ask-state"
        self.daily_budget_usd = float(daily_budget_usd)
        self.ledger_path = self.state_dir / "budget.json"
        self.lock_path = self.state_dir / "budget.lock"
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def _today(self) -> str:
        return self._clock().astimezone(timezone.utc).date().isoformat()

    @staticmethod
    def _amount(value: object) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise BudgetUnavailable("Invalid budget ledger amount")
        return float(value)

    def _read(self) -> dict:
        try:
            raw = self.ledger_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return {"version": 1, "days": {}}
        try:
            data = json.loads(raw)
            if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("days"), dict):
                raise BudgetUnavailable("Invalid budget ledger shape")
            for day, entry in data["days"].items():
                datetime.fromisoformat(day)
                if not isinstance(entry, dict) or not isinstance(entry.get("reservations"), dict):
                    raise BudgetUnavailable("Invalid budget ledger day")
                self._amount(entry.get("spent_usd"))
                for reservation in entry["reservations"].values():
                    if not isinstance(reservation, dict) or not isinstance(reservation.get("model"), str):
                        raise BudgetUnavailable("Invalid budget ledger reservation")
                    self._amount(reservation.get("amount_usd"))
            return data
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            raise BudgetUnavailable("Corrupt budget ledger") from exc

    def _write(self, data: dict) -> None:
        path: str | None = None
        try:
            fd, path = tempfile.mkstemp(prefix="budget-", dir=self.state_dir)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(data, handle, separators=(",", ":"), allow_nan=False)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(path, self.ledger_path)
            path = None
            directory_fd = os.open(self.state_dir, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except (OSError, ValueError) as exc:
            raise BudgetUnavailable("Budget ledger cannot be written") from exc
        finally:
            if path is not None:
                try:
                    os.unlink(path)
                except FileNotFoundError:
                    pass

    def _locked(self, operation):
        try:
            self.state_dir.mkdir(parents=True, exist_ok=True)
            with self.lock_path.open("a+") as handle:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                try:
                    return operation()
                finally:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        except BudgetUnavailable:
            raise
        except OSError as exc:
            raise BudgetUnavailable("Budget ledger unavailable") from exc

    @staticmethod
    def _available(entry: dict, cap: float) -> float:
        reserved = sum(float(item["amount_usd"]) for item in entry["reservations"].values())
        return max(0.0, cap - float(entry["spent_usd"]) - reserved)

    def remaining_usd(self) -> float:
        def read():
            data = self._read()
            entry = data["days"].get(self._today(), {"spent_usd": 0, "reservations": {}})
            return self._available(entry, self.daily_budget_usd)
        return self._locked(read)

    def reserve(self, model: str, amount_usd: float) -> Reservation:
        try:
            # A cascade reports its tiers joined with "+" (TieredAdapter.model).
            for part in model.split("+"):
                price_for(part)
        except ValueError as exc:
            raise BudgetUnavailable("No price for requested model") from exc
        amount = self._amount(amount_usd)
        if amount <= 0:
            raise ValueError("reservation must be positive")

        def write():
            data = self._read()
            day = self._today()
            entry = data["days"].setdefault(day, {"spent_usd": 0.0, "reservations": {}})
            if amount > self._available(entry, self.daily_budget_usd):
                raise BudgetExhausted("Daily Ask budget exhausted")
            token = uuid.uuid4().hex
            entry["reservations"][token] = {"model": model, "amount_usd": amount}
            self._write(data)
            return Reservation(token, day, model, amount)
        return self._locked(write)

    def settle(self, reservation: Reservation, actual_usd: float | None) -> None:
        actual = None if actual_usd is None else self._amount(actual_usd)

        def write():
            data = self._read()
            entry = data["days"].get(reservation.day)
            if entry is None or reservation.id not in entry["reservations"]:
                return
            saved = entry["reservations"][reservation.id]
            if saved != {"model": reservation.model, "amount_usd": reservation.amount_usd}:
                raise BudgetUnavailable("Budget reservation mismatch")
            # An estimate should bound the call. If billing exceeds it, record
            # the higher actual amount and block further reservations as needed.
            entry["spent_usd"] += reservation.amount_usd if actual is None else actual
            del entry["reservations"][reservation.id]
            self._write(data)
        self._locked(write)
