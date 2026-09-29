"""Interpreter input/output shared by every adapter (#199).

Adapters (Jev, OpenAI Responses for gpt-4.1-mini and Luna) translate their
provider-native answers into ``InterpreterOutput``. Python then normalizes
it into an ``AskRequest`` (see ``NormalizationResult``). Model output never
reaches data tools directly, and a schema-valid guess is still a failure:
adapters must report ``absent``/``ambiguous``/``no_matching_candidate``
rather than pick.

Frozen contract (docs/ask-contract.md). Coordinate before changing.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from .candidates import CandidateLookupResult
from .common import ContractModel, DateComponents
from .request import AskContext, AskRequest

AdapterName = Literal["jev", "openai_responses"]

# Fields an interpreter fills. Candidate-backed fields ("player", "teams",
# "date", "season", "round", "game_number") select candidate IDs; closed-set
# fields ("intent", "stat_scope", "stat", "aggregation") select literal values
# from the enums in common.py.
InterpreterField = Literal[
    "intent",
    "stat_scope",
    "stat",
    "aggregation",
    "player",
    "teams",
    "date",
    "season",
    "round",
    "game_number",
]
CANDIDATE_BACKED_FIELDS: frozenset[str] = frozenset({"player", "teams", "date", "season", "round", "game_number"})

FieldStatus = Literal[
    "selected",  # exactly the value(s) in `selected`
    "absent",  # the question does not specify this field
    "ambiguous",  # several `alternatives` remain valid; ask the user
    "no_matching_candidate",  # the question mentions it but no candidate fits
]

InterpreterOutcome = Literal[
    "interpreted",  # `fields` describe a potentially supported request
    "unsupported",  # outside enabled scope; `unsupported_reason` set
    "unreliable",  # ran, but cannot interpret reliably (fallback candidate)
    "unavailable",  # provider error/timeout/quota; nothing interpreted
]

UnsupportedReason = Literal[
    "career_stats",
    "season_stats",
    "season_leaders",
    "historical_comparison",
    "prediction",
    "follow_up",
    "regular_season_record",
    "standings",
    "reference_question",  # glossary/biography (#202)
    "multi_game_average",  # per-game averages across games
    "not_basketball",
    "other",
]


class FieldInterpretation(ContractModel):
    field: InterpreterField
    status: FieldStatus
    # status == "selected": 1 value (2 allowed only for "teams").
    selected: list[str] = Field(default_factory=list, max_length=2)
    # status == "ambiguous": the 2+ values that remain plausible.
    alternatives: list[str] = Field(default_factory=list, max_length=12)
    # Adapter-native confidence normalized to 0..1 (Jev score, logprob-derived,
    # etc.). None when the adapter exposes none. Used by the cascade policy;
    # thresholds are calibrated in #199, not copied from cookbooks.
    confidence: float | None = Field(default=None, ge=0, le=1)
    mention: str | None = Field(default=None, max_length=120)  # question text for this field

    @model_validator(mode="after")
    def _status_shape(self) -> FieldInterpretation:
        if self.status == "selected":
            if not self.selected:
                raise ValueError("selected fields need a value")
            if len(self.selected) > 1 and self.field != "teams":
                raise ValueError("only `teams` may select two values")
        elif self.selected:
            raise ValueError(f"{self.status} fields must not select values")
        if self.status == "ambiguous" and len(self.alternatives) < 2:
            raise ValueError("ambiguous fields need at least two alternatives")
        return self


class InterpreterUsage(ContractModel):
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    cached_input_tokens: int | None = Field(default=None, ge=0)
    provider_calls: int = Field(default=1, ge=0)
    cost_usd: float | None = Field(default=None, ge=0)  # list-price estimate


class InterpreterMetadata(ContractModel):
    adapter: AdapterName
    provider: str = Field(max_length=40)  # "typesafe", "openai"
    model: str = Field(max_length=80)  # pinned request model, e.g. "jev-1.13.0"
    resolved_model: str | None = Field(default=None, max_length=80)  # version the provider reports
    latency_ms: int = Field(ge=0)
    usage: InterpreterUsage = Field(default_factory=InterpreterUsage)


class InterpreterInput(ContractModel):
    question: str = Field(min_length=1, max_length=300)
    context: AskContext
    candidates: CandidateLookupResult
    deadline_ms: int = Field(ge=0)  # remaining wall-clock budget for this attempt
    max_cost_usd: float = Field(ge=0)  # remaining spend this attempt may reserve


class InterpreterOutput(ContractModel):
    outcome: InterpreterOutcome
    # At most one entry per field. Missing fields are treated as "absent".
    fields: list[FieldInterpretation] = Field(default_factory=list, max_length=10)
    unsupported_reason: UnsupportedReason | None = None
    # Only for adapters that extract dates directly (OpenAI) when the date
    # candidate set had no match. Python validates it; it never overrides a
    # selected date candidate.
    extracted_date: DateComponents | None = None
    error_code: str | None = Field(default=None, max_length=60)  # no raw provider text
    metadata: InterpreterMetadata

    @model_validator(mode="after")
    def _consistent(self) -> InterpreterOutput:
        names = [f.field for f in self.fields]
        if len(names) != len(set(names)):
            raise ValueError("at most one interpretation per field")
        if (self.outcome == "unsupported") != (self.unsupported_reason is not None):
            raise ValueError("unsupported_reason is required iff outcome is unsupported")
        if self.outcome == "unavailable" and self.fields:
            raise ValueError("unavailable outputs carry no fields")
        return self

    def get_field(self, name: InterpreterField) -> FieldInterpretation | None:
        return next((f for f in self.fields if f.field == name), None)


class NormalizationResult(ContractModel):
    """Result of validating an InterpreterOutput against its candidates."""

    status: Literal["valid", "needs_clarification", "unsupported", "invalid"]
    request: AskRequest | None = None
    # needs_clarification: which field, and why.
    clarify_field: InterpreterField | None = None
    clarify_reason: Literal["ambiguous", "missing", "no_matching_candidate", "year_required", "range_too_long"] | None = None
    unsupported_reason: UnsupportedReason | None = None
    # invalid: adapter produced something Python rejects (unknown candidate
    # ID, impossible combination). Never executed; feeds the cascade policy.
    errors: list[str] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def _shape(self) -> NormalizationResult:
        if (self.status == "valid") != (self.request is not None):
            raise ValueError("request is required iff status is valid")
        if self.status == "needs_clarification" and self.clarify_field is None:
            raise ValueError("needs_clarification needs clarify_field")
        if self.status == "unsupported" and self.unsupported_reason is None:
            raise ValueError("unsupported needs unsupported_reason")
        return self
