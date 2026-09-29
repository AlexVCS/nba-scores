"""Server-only Ask settings. The endpoint stays off until the release gate passes."""

from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from pathlib import Path

from server.ask.interpreters.pricing import price_for

_SERVER_DIR = Path(__file__).resolve().parents[1]


def _number(name: str, default: float, *, minimum: float = 0) -> float:
    try:
        value = float(os.environ.get(name, default))
    except ValueError as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if not math.isfinite(value) or value < minimum:
        raise ValueError(f"{name} must be finite and at least {minimum}")
    return value


def _integer(name: str, default: int, *, minimum: int = 1) -> int:
    try:
        value = int(os.environ.get(name, default))
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    return value


def _api_key(key: str = "OPENAI_API_KEY") -> str | None:
    if os.environ.get(key):
        return os.environ[key]
    path = _SERVER_DIR / ".env"
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            name, separator, value = line.partition("=")
            if separator and name.strip().removeprefix("export ").strip() == key:
                return value.strip().strip("\"'") or None
    except FileNotFoundError:
        pass
    return None


@dataclass(frozen=True)
class AskConfig:
    enabled: bool = False
    primary_model: str = "gpt-6-luna"
    primary_reasoning_effort: str = "low"
    fallback_model: str | None = None
    deadline_seconds: float = 20.0
    daily_budget_usd: float = 1.0
    state_dir: Path = _SERVER_DIR / ".ask-state"
    cache_version: str = "1"
    parse_ttl_seconds: float = 3600.0
    answer_ttl_seconds: float = 30.0
    cache_max_entries: int = 256
    per_client_per_minute: int = 10
    per_worker_per_minute: int = 60
    max_in_flight: int = 2
    api_key: str | None = field(default=None, repr=False)
    # Interpreter cascade (ADR 0002): Laya, then Jev, then Luna (`primary_model`).
    # A tier without its URL or key is skipped. Laya stays unset in production until
    # promoted (ADR 0007). Accept thresholds are UNCALIBRATED placeholders until #199.
    laya_base_url: str | None = None
    laya_model: str = "laya"
    laya_accept_min: float = 0.9
    jev_model: str = "jev-1.13.0"
    jev_accept_min: float = 0.9
    veto_min: float = 0.5
    typesafe_api_key: str | None = field(default=None, repr=False)

    @classmethod
    def from_env(cls) -> AskConfig:
        enabled = os.environ.get("ASK_ENABLED", "0").strip().lower() in ("1", "true", "yes")
        model = os.environ.get("ASK_PARSER_MODEL", "gpt-6-luna").strip()
        fallback = os.environ.get("ASK_FALLBACK_MODEL", "").strip() or None
        price_for(model)
        if fallback:
            price_for(fallback)
        return cls(
            enabled=enabled,
            primary_model=model,
            primary_reasoning_effort=os.environ.get("ASK_REASONING_EFFORT", "low").strip(),
            fallback_model=fallback,
            deadline_seconds=_number("ASK_DEADLINE_SECONDS", 20, minimum=0.001),
            daily_budget_usd=_number("ASK_DAILY_BUDGET_USD", 1),
            state_dir=Path(os.environ.get("ASK_STATE_DIR", str(_SERVER_DIR / ".ask-state"))),
            cache_version=os.environ.get("ASK_CACHE_VERSION", "1"),
            parse_ttl_seconds=_number("ASK_PARSE_TTL_SECONDS", 3600),
            answer_ttl_seconds=_number("ASK_ANSWER_TTL_SECONDS", 30),
            cache_max_entries=_integer("ASK_CACHE_MAX_ENTRIES", 256),
            per_client_per_minute=_integer("ASK_CLIENT_RATE_PER_MINUTE", 10),
            per_worker_per_minute=_integer("ASK_WORKER_RATE_PER_MINUTE", 60),
            max_in_flight=_integer("ASK_MAX_IN_FLIGHT", 2),
            api_key=_api_key(),
            laya_base_url=os.environ.get("LAYA_BASE_URL", "").strip() or None,
            laya_model=os.environ.get("LAYA_MODEL", "laya").strip(),
            laya_accept_min=_number("ASK_LAYA_ACCEPT_MIN", 0.9),
            jev_model=os.environ.get("ASK_JEV_MODEL", "jev-1.13.0").strip(),
            jev_accept_min=_number("ASK_JEV_ACCEPT_MIN", 0.9),
            veto_min=_number("ASK_VETO_MIN", 0.5),
            typesafe_api_key=_api_key("TYPESAFE_API_KEY"),
        )
