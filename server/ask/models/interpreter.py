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

from .candidates import CandidateField, CandidateLookupResult
from .common import ClarifyField, ClarifyReason, ContractModel, DateComponents
from .request import AskContext, AskRequest

AdapterName = Literal["laya", "jev", "openai_responses", "cascade"]

# Fields an interpreter fills. Candidate-backed fields ("player", "teams",
# "target_team", "date", "season", "round", "game_number") select candidate IDs;
# closed-set fields ("intent", "stat_scope", "stat", "aggregation") select literal
# values from the enums in common.py.
#
# "teams" lists every team the question names, opponents included (a matchup).
# "target_team" is the one team whose own statistics a team-scope boxscore question
# asks for; it is never inferred from the order of "teams".
InterpreterField = Literal[
    "intent",
    "stat_scope",
    "stat",
    "aggregation",
    "player",
    "teams",
    "target_team",
    "date",
    "season",
    "round",
    "game_number",
    "location",
]
CANDIDATE_BACKED_FIELDS: frozenset[str] = frozenset(
    {"player", "teams", "target_team", "date", "season", "round", "game_number", "location"}
)

# Interpreter field -> candidate set it selects from. "teams" (an interpreter may
# select two) and "target_team" (one) both select from the "team" candidate set.
INTERPRETER_TO_CANDIDATE_FIELD: dict[str, CandidateField] = {
    "player": "player",
    "teams": "team",
    "target_team": "team",
    "date": "date",
    "season": "season",
    "round": "round",
    "game_number": "game_number",
    "location": "location",
}

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
    "unsupported_leader_stat",  # leaders by a percentage or full stat line (no ranking rule)
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


TierReadAction = Literal[
    "accepted",  # this tier's read decided the field
    "escalated",  # below the tier's accept_min; passed to the next tier
    "vetoed",  # a confident read that contradicted an earlier selection (ADR 0002)
    "unused",  # the field was already decided and this read did not contest it
]

FieldOutcome = Literal[
    "accepted",  # decided by the first tier that read it
    "escalated",  # decided by a later tier after an earlier read fell below threshold
    "vetoed",  # tiers disagreed; the field is clarified, never executed
    "undecided",  # no tier decided it (every read below threshold or tiers unavailable)
]


class TierRead(ContractModel):
    """One tier's read of one field. No values, only status and confidence."""

    tier: str = Field(max_length=20)  # "laya", "jev", "luna"
    status: FieldStatus | Literal["unsupported"]
    confidence: float | None = Field(default=None, ge=0, le=1)
    action: TierReadAction


class FieldDecision(ContractModel):
    """Per-field cascade diagnostics (ADRs 0002, 0009, 0010). Dev details and logs only."""

    field: InterpreterField
    # "lookup", "laya", "jev", "luna", or "veto"; None when no tier decided the field.
    decided_by: str | None = Field(default=None, max_length=20)
    # Native confidence of the deciding read (the best pending read when undecided);
    # None for lookup, vetoes, and tiers without confidences (Luna).
    confidence: float | None = Field(default=None, ge=0, le=1)
    outcome: FieldOutcome
    reads: list[TierRead] = Field(default_factory=list, max_length=4)


class InterpreterMetadata(ContractModel):
    adapter: AdapterName
    provider: str = Field(max_length=40)  # "typesafe", "openai"
    model: str = Field(max_length=80)  # pinned request model, e.g. "jev-1.13.0"
    resolved_model: str | None = Field(default=None, max_length=80)  # version the provider reports
    latency_ms: int = Field(ge=0)
    usage: InterpreterUsage = Field(default_factory=InterpreterUsage)
    # Cascade only: interpreter field -> tier ("laya", "jev", "luna") that decided it.
    field_tiers: dict[InterpreterField, str] = Field(default_factory=dict)
    # Cascade only: how each field was decided, tier by tier.
    field_decisions: list[FieldDecision] = Field(default_factory=list, max_length=12)


class InterpreterInput(ContractModel):
    question: str = Field(min_length=1, max_length=300)
    context: AskContext
    candidates: CandidateLookupResult
    deadline_ms: int = Field(ge=0)  # remaining wall-clock budget for this attempt
    max_cost_usd: float = Field(ge=0)  # remaining spend this attempt may reserve


class InterpreterOutput(ContractModel):
    outcome: InterpreterOutcome
    # At most one entry per field. Missing fields are treated as "absent".
    fields: list[FieldInterpretation] = Field(default_factory=list, max_length=12)
    unsupported_reason: UnsupportedReason | None = None
    # outcome == "unsupported" only: the adapter's confidence that the request is out of
    # scope (Jev's "unsupported" intent probability). None when the adapter has none.
    unsupported_confidence: float | None = Field(default=None, ge=0, le=1)
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
        if self.unsupported_confidence is not None and self.outcome != "unsupported":
            raise ValueError("unsupported_confidence is only for unsupported outcomes")
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
    clarify_field: ClarifyField | None = None
    clarify_reason: ClarifyReason | None = None
    unsupported_reason: UnsupportedReason | None = None
    # invalid: adapter produced something Python rejects (unknown candidate
    # ID, impossible combination). Never executed; feeds the cascade policy.
    errors: list[str] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def _shape(self) -> NormalizationResult:
        if (self.status == "valid") != (self.request is not None):
            raise ValueError("request is required iff status is valid")
        if (self.status == "needs_clarification") != (self.clarify_field is not None and self.clarify_reason is not None):
            raise ValueError("clarify_field and clarify_reason are required iff status is needs_clarification")
        if self.status == "unsupported" and self.unsupported_reason is None:
            raise ValueError("unsupported needs unsupported_reason")
        return self
