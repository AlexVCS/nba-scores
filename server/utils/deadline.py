"""One monotonic deadline shared by every step of a bounded retrieval.

Callers create it once and pass it through source attempts, retry backoff,
fallback and joined-cache waits, so the steps together fit the time left.
It holds no global state; the clock and sleep are injectable for tests.
"""

from __future__ import annotations

import time
from typing import Callable


class Deadline:
    __slots__ = ("expires_at", "_clock", "_sleep")

    def __init__(self, expires_at: float, *, clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep):
        self.expires_at = float(expires_at)
        self._clock = clock
        self._sleep = sleep

    @classmethod
    def after(cls, seconds: float, *, clock: Callable[[], float] = time.monotonic,
              sleep: Callable[[float], None] = time.sleep) -> Deadline:
        return cls(clock() + seconds, clock=clock, sleep=sleep)

    def remaining(self) -> float:
        return max(0.0, self.expires_at - self._clock())

    def expired(self) -> bool:
        return self.remaining() <= 0

    def fits(self, seconds: float) -> bool:
        """Whether a step needing ``seconds`` can still start and finish in time."""
        remaining = self.remaining()
        return remaining > 0 and remaining >= seconds

    def cap(self, seconds: float) -> float:
        return min(seconds, self.remaining())

    def sleep(self, seconds: float) -> None:
        self._sleep(self.cap(seconds))

    def __repr__(self) -> str:
        return f"Deadline(remaining={self.remaining():.3f}s)"


def wait_timeout(deadline: Deadline | None, default: float | None) -> float | None:
    """A joined-cache wait bounded by both ``default`` and the deadline."""
    if deadline is None:
        return default
    remaining = deadline.remaining()
    return remaining if default is None else min(default, remaining)
