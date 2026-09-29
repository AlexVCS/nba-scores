"""Short-lived anonymous diagnostics for unsupported Ask requests."""

from __future__ import annotations

import hashlib
import secrets
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Callable

from server.ask.interpreters import closed_sets as cs

_OPERATIONS = frozenset({"ask", "game_search", "boxscore_stat", "playoff_series", "postseason_summary", "unknown"})
_FIELDS = frozenset({"intent", "stat_scope", "stat", "player", "teams", "date", "season", "round", "game_number", "location"})


@dataclass(frozen=True)
class DiagnosticEvent:
    question: str
    operation: str | None = None
    stat: str | None = None
    missing_fields: tuple[str, ...] = ()
    reason: str | None = None


class AskDiagnostics:
    def __init__(self, max_entries: int = 200, ttl_seconds: float = 7 * 86400,
                 *, clock: Callable[[], float] | None = None):
        if max_entries < 1 or ttl_seconds <= 0:
            raise ValueError("diagnostic limits must be positive")
        self.max_entries = max_entries
        self.ttl_seconds = ttl_seconds
        self._clock = clock or time.time
        self._salt = secrets.token_bytes(16)
        self._entries: deque[dict] = deque(maxlen=max_entries)
        self._lock = threading.Lock()

    def _prune(self) -> None:
        cutoff = self._clock() - self.ttl_seconds
        while self._entries and self._entries[0]["recorded_at"] <= cutoff:
            self._entries.popleft()

    def record(self, event: DiagnosticEvent) -> bool:
        # Only enumerated metadata survives; never copy arbitrary model text.
        digest = hashlib.sha256(self._salt + event.question.encode()).hexdigest()
        item = {
            "question_hash": digest,
            "recorded_at": self._clock(),
            "operation": event.operation if event.operation in _OPERATIONS else None,
            "stat": event.stat if event.stat in cs.STATS else None,
            "missing_fields": tuple(field for field in event.missing_fields if field in _FIELDS),
            "reason": event.reason if event.reason in cs.UNSUPPORTED_REASONS else None,
        }
        with self._lock:
            self._prune()
            self._entries.append(item)
        return True

    def unsupported_request_log(self) -> list[dict]:
        with self._lock:
            self._prune()
            return [dict(item) for item in self._entries]
