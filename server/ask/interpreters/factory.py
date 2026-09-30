"""The one place Ask's interpreter cascade is built (ADRs 0002, 0007).

The live pipeline and the release evaluation both call `build_cascade` and
`build_policy`, so an evaluation measures the configuration that ships.

Production is Jev, then GPT Luna. Laya joins in front only on a development server
(`ASK_DEV=1`) with `LAYA_BASE_URL` set; production never builds it (ADR 0007). A tier
without its key is skipped: with no Jev key every field goes to Luna, and a Jev call
that fails at request time is skipped the same way (`TieredAdapter`). Nothing is
guessed; a field no tier decides is clarified.
"""

from __future__ import annotations

import logging
from dataclasses import fields

from server.ask.config import FROZEN_CASCADE, AskConfig
from server.ask.interpreters.cascade import ThresholdCascadePolicy
from server.ask.interpreters.jev import JevAdapter
from server.ask.interpreters.laya import LayaAdapter
from server.ask.interpreters.openai_responses import OpenAIConfig, OpenAIResponsesAdapter
from server.ask.interpreters.tiered import CASCADE_POLICY_THRESHOLDS, Tier, TieredAdapter

logger = logging.getLogger(__name__)


def frozen_config(**overrides) -> AskConfig:
    """An `AskConfig` with the frozen cascade settings; `overrides` supplies keys and paths."""
    unknown = set(overrides) - {f.name for f in fields(AskConfig)}
    if unknown:
        raise TypeError(f"unknown AskConfig fields: {sorted(unknown)}")
    return AskConfig(**{**FROZEN_CASCADE, **overrides})


def cascade_drift(config: AskConfig) -> list[str]:
    """Names of cascade settings that differ from the frozen, evaluated configuration."""
    return [name for name, value in FROZEN_CASCADE.items() if getattr(config, name) != value]


def build_cascade(config: AskConfig, *, include_laya: bool | None = None) -> TieredAdapter:
    """Jev, then Luna; Laya first only when `include_laya` (default: `config.dev`).

    Keys never appear in logs or errors."""
    include_laya = config.dev if include_laya is None else include_laya
    tiers: list[Tier] = []
    if include_laya and config.laya_base_url:
        tiers.append(Tier("laya", LayaAdapter(url=config.laya_base_url, model=config.laya_model),
                          config.laya_accept_min))
    if config.typesafe_api_key:
        tiers.append(Tier("jev", JevAdapter(config.typesafe_api_key, model=config.jev_model),
                          config.jev_accept_min))
    if config.api_key:
        tiers.append(Tier("luna", OpenAIResponsesAdapter(config.api_key, OpenAIConfig(
            model=config.primary_model, reasoning_effort=config.primary_reasoning_effort,
            timeout_s=config.deadline_seconds,
        )), None))
    if not tiers:
        raise RuntimeError("ASK_ENABLED requires TYPESAFE_API_KEY or OPENAI_API_KEY "
                           "(or LAYA_BASE_URL with ASK_DEV=1)")
    names = [tier.name for tier in tiers]
    if "jev" not in names:
        logger.warning("Ask cascade built without Jev (no TYPESAFE_API_KEY); every field goes to Luna")
    if "luna" not in names:
        logger.warning("Ask cascade built without Luna (no OPENAI_API_KEY); undecided fields are clarified")
    drift = [name for name in cascade_drift(config) if include_laya or name != "laya_base_url"]
    if drift:
        logger.warning("Ask cascade settings differ from the evaluated configuration: %s", ", ".join(drift))
    # Without Luna, fields the last System One tier cannot decide become clarifications.
    return TieredAdapter(tiers, veto_min=config.veto_min)


def build_policy() -> ThresholdCascadePolicy:
    """The cascade policy: accept only fields a tier decided; never a whole-request fallback.
    With no fallback configured, the policy's model name is only a label."""
    return ThresholdCascadePolicy("cascade", thresholds=CASCADE_POLICY_THRESHOLDS)
