"""Candidate lookup output (#200).

Interpreters choose among these candidates, so candidate recall bounds
accuracy. Candidate sets are bounded, typed per field, and say explicitly
when nothing matched. A missing candidate is never evidence that the user
meant a different entity.

Frozen contract (docs/ask-contract.md). Coordinate before changing.
"""

from __future__ import annotations

import datetime as dt
from typing import Annotated, Literal, Union

from pydantic import Field, model_validator

from .common import (
    Conference,
    ContractModel,
    DateComponents,
    DateRange,
    PlayerRef,
    PlayoffRound,
    Season,
    TeamRef,
)

MAX_CANDIDATES_PER_FIELD = 12
MAX_TOTAL_CANDIDATES = 48

CandidateField = Literal["player", "team", "date", "season", "round", "game_number"]
CANDIDATE_FIELDS: tuple[CandidateField, ...] = ("player", "team", "date", "season", "round", "game_number")

CandidateSource = Literal[
    "alias",  # maintained alias list (e.g. "Cavs", "KD")
    "player_catalog",  # historical player catalog
    "team_catalog",  # canonical current team names
    "historical_team_name",  # dated historical franchise names
    "date_parser",  # date language parsed in Python
    "pattern",  # rounds, game numbers, season/year patterns
    "app_context",  # the page/game/season the user is looking at
]


class PlayerCandidateValue(ContractModel):
    kind: Literal["player"] = "player"
    player: PlayerRef
    # Teams the player was on for the relevant date/season, from dated records
    # (never the current roster). Empty when not established.
    team_ids: list[int] = Field(default_factory=list, max_length=6)
    first_season: Season | None = None
    last_season: Season | None = None


class TeamCandidateValue(ContractModel):
    kind: Literal["team"] = "team"
    team: TeamRef
    # Validity window of this name, for historical names.
    valid_from: dt.date | None = None
    valid_to: dt.date | None = None


class DateCandidateValue(ContractModel):
    kind: Literal["date"] = "date"
    components: DateComponents
    # Resolved against AskContext.reference_time. None when the expression
    # cannot be resolved without clarification (e.g. no year, > 7 days).
    resolved: DateRange | None = None
    unresolved_reason: Literal["year_required", "range_too_long", "invalid_date"] | None = None


class SeasonCandidateValue(ContractModel):
    kind: Literal["season"] = "season"
    season: Season
    # "2024 Finals" -> year 2024 -> season "2023-24".
    from_year: int | None = None


class RoundCandidateValue(ContractModel):
    kind: Literal["round"] = "round"
    round: PlayoffRound
    conference: Conference | None = None


class GameNumberCandidateValue(ContractModel):
    kind: Literal["game_number"] = "game_number"
    game_number: int = Field(ge=1, le=7)


CandidateValue = Annotated[
    Union[
        PlayerCandidateValue,
        TeamCandidateValue,
        DateCandidateValue,
        SeasonCandidateValue,
        RoundCandidateValue,
        GameNumberCandidateValue,
    ],
    Field(discriminator="kind"),
]


class Candidate(ContractModel):
    # Stable within one lookup result, e.g. "player:1627759", "team:1610612752",
    # "date:0". Interpreters reference candidates only by this ID.
    id: str = Field(pattern=r"^[a-z_]+:[A-Za-z0-9_.-]+$", max_length=64)
    field: CandidateField
    label: str = Field(min_length=1, max_length=120)  # human/model-readable
    matched_text: str | None = Field(default=None, max_length=120)  # question substring
    span: tuple[int, int] | None = None  # character offsets into the question
    source: CandidateSource
    alias: str | None = Field(default=None, max_length=80)  # alias that matched
    match_score: float = Field(ge=0, le=1)  # lookup similarity, not interpreter confidence
    value: CandidateValue

    @model_validator(mode="after")
    def _field_matches_value(self) -> Candidate:
        if self.value.kind != self.field:
            raise ValueError(f"candidate field {self.field!r} does not match value kind {self.value.kind!r}")
        return self


class CandidateSet(ContractModel):
    """Candidates for one field.

    - ``candidates``: at least one candidate.
    - ``no_candidates``: the question mentions something of this type
      (``unmatched_text``) but nothing matched. Do not force a choice.
    - ``not_mentioned``: nothing of this type was detected.
    """

    field: CandidateField
    status: Literal["candidates", "no_candidates", "not_mentioned"]
    candidates: list[Candidate] = Field(default_factory=list, max_length=MAX_CANDIDATES_PER_FIELD)
    truncated: bool = False  # more matches existed than the limit
    unmatched_text: list[str] = Field(default_factory=list, max_length=4)

    @model_validator(mode="after")
    def _status_consistent(self) -> CandidateSet:
        if (self.status == "candidates") != bool(self.candidates):
            raise ValueError("status 'candidates' iff candidates is non-empty")
        if any(c.field != self.field for c in self.candidates):
            raise ValueError("every candidate must belong to the set's field")
        return self


class CandidateLookupResult(ContractModel):
    """One lookup: a set for every CandidateField, plus provenance."""

    sets: dict[CandidateField, CandidateSet]
    alias_version: str = Field(min_length=1, max_length=40)
    latency_ms: int = Field(ge=0)

    @model_validator(mode="after")
    def _complete(self) -> CandidateLookupResult:
        missing = set(CANDIDATE_FIELDS) - set(self.sets)
        if missing:
            raise ValueError(f"missing candidate sets: {sorted(missing)}")
        if any(key != s.field for key, s in self.sets.items()):
            raise ValueError("set keys must match set.field")
        ids = [c.id for s in self.sets.values() for c in s.candidates]
        if len(ids) != len(set(ids)):
            raise ValueError("candidate IDs must be unique")
        if len(ids) > MAX_TOTAL_CANDIDATES:
            raise ValueError(f"at most {MAX_TOTAL_CANDIDATES} candidates in total")
        return self

    def by_id(self, candidate_id: str) -> Candidate | None:
        for s in self.sets.values():
            for c in s.candidates:
                if c.id == candidate_id:
                    return c
        return None
