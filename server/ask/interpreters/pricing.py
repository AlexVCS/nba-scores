"""List prices and a hard spend guard for interpreter calls.

Prices were read from the provider model pages on 2026-09-29 (USD per 1M tokens).
They are list-price estimates, not billing records.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass


@dataclass(frozen=True)
class Price:
    input: float
    output: float
    cached_input: float | None = None


PRICES: dict[str, Price] = {
    # TypeSafe charges input tokens only; output tokens are free.
    "jev-1.13.0": Price(input=0.042, output=0.0),
    "gpt-4.1-mini-2025-04-14": Price(input=0.40, output=1.60, cached_input=0.10),
    "gpt-6-luna": Price(input=0.10, output=0.50, cached_input=0.01),
    "gpt-5.6-luna": Price(input=0.20, output=1.20, cached_input=0.02),
}


def price_for(model: str) -> Price:
    try:
        return PRICES[model]
    except KeyError:
        raise ValueError(f"No list price recorded for model {model!r}") from None


def cost_usd(model: str, input_tokens: int, output_tokens: int, cached_input_tokens: int = 0) -> float:
    price = price_for(model)
    cached = min(cached_input_tokens, input_tokens)
    cached_rate = price.cached_input if price.cached_input is not None else price.input
    # Reasoning tokens are already included in output_tokens for the Responses API.
    return (
        (input_tokens - cached) * price.input + cached * cached_rate + output_tokens * price.output
    ) / 1_000_000


def estimate_max_cost(model: str, prompt_chars: int, max_output_tokens: int) -> float:
    """Conservative upper bound: ~1 token per 2 characters plus the full output allowance."""
    price = price_for(model)
    input_tokens = prompt_chars // 2 + 64
    return (input_tokens * price.input + max_output_tokens * price.output) / 1_000_000


class SpendCapExceeded(Exception):
    pass


class SpendGuard:
    """Reserve-then-settle guard so the cap holds even with concurrent calls."""

    def __init__(self, cap_usd: float):
        if cap_usd <= 0:
            raise ValueError("Spend cap must be positive")
        self.cap_usd = cap_usd
        self.spent_usd = 0.0
        self._reserved_usd = 0.0
        self._lock = threading.Lock()

    @property
    def remaining_usd(self) -> float:
        with self._lock:
            return max(0.0, self.cap_usd - self.spent_usd - self._reserved_usd)

    def reserve(self, amount: float) -> float:
        with self._lock:
            if self.spent_usd + self._reserved_usd + amount > self.cap_usd:
                raise SpendCapExceeded(f"reserving ${amount:.6f} would exceed the ${self.cap_usd:.2f} cap")
            self._reserved_usd += amount
            return amount

    def settle(self, reserved: float, actual: float | None) -> None:
        """Release a reservation. Unknown actual cost keeps the full reservation as spent."""
        with self._lock:
            self._reserved_usd -= reserved
            self.spent_usd += reserved if actual is None else actual
