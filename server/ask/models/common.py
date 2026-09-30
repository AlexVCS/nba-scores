"""Value types shared by every part of the Ask contract.

Frozen contract (docs/ask-contract.md). Coordinate before changing.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints, model_validator

SCHEMA_VERSION = "1"
NEW_YORK_TZ = "America/New_York"
NEW_YORK = ZoneInfo(NEW_YORK_TZ)
MAX_GAME_SEARCH_DAYS = 7
# Upper bound for relative day counts in date language ("past 30 days"). Counts
# above MAX_GAME_SEARCH_DAYS are representable so normalization can answer
# them with a ``range_too_long`` clarification; DateRange enforces the limit.
MAX_RELATIVE_DAY_COUNT = 366
MAX_QUESTION_LENGTH = 300


class ContractModel(BaseModel):
    """Strict base for contract models (unknown keys are errors).

    Models are *shallowly* frozen: attributes cannot be reassigned, but nested
    lists and dicts are ordinary mutable containers, so models are not
    hashable. Use ``canonical_json`` for cache keys, never ``hash()``.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)


def canonical_json(model: BaseModel) -> str:
    """Canonical serialization for cache keys: JSON mode, keys sorted, no
    whitespace. Equal models give equal strings. Hash the result if needed."""

    return json.dumps(model.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def to_new_york(value: datetime) -> datetime:
    """Require a timezone-aware datetime and convert it to America/New_York."""

    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime must be timezone-aware")
    return value.astimezone(NEW_YORK)


# Timezone-aware datetime normalized to America/New_York, so ``.date()`` is
# the New York calendar date (e.g. 2026-02-09T02:00Z becomes Feb 8, 21:00 EST).
NewYorkDateTime = Annotated[datetime, AfterValidator(to_new_york)]


Intent = Literal["game_search", "boxscore_stat", "playoff_series", "postseason_summary", "player_season_stats", "team_records", "season_leaders"]
SeasonType = Literal["regular_season", "playoffs"]
StandingsScope = Literal["league", "east", "west"]

# Fields that a clarification can ask about. Shared by normalization
# (NormalizationResult.clarify_field), the cascade (ClarifyDecision.field), and
# HTTP (Clarification.field). "teams" covers one team or a matchup.
# Measure choices apply to player season stats; single-game averages stay unsupported.
ClarifyField = Literal[
    "intent", "stat_scope", "stat", "player", "teams", "date", "season", "round", "game_number", "location", "aggregation", "season_type", "standings_scope"
]
ClarifyReason = Literal["ambiguous", "missing", "no_matching_candidate", "year_required", "range_too_long"]

# Scope of a boxscore_stat request: one player, team totals, or game leaders.
StatScope = Literal["player", "team", "leaders"]

# "stat_line" means the full line (player or team scope only, never leaders).
Stat = Literal[
    "stat_line",
    "points",
    "rebounds",
    "offensive_rebounds",
    "defensive_rebounds",
    "assists",
    "steals",
    "blocks",
    "turnovers",
    "fouls",
    "minutes",
    "field_goals",
    "three_pointers",
    "free_throws",
    "field_goal_percentage",
    "three_point_percentage",
    "free_throw_percentage",
    "plus_minus",
]
# A concrete statistic value (everything except the "stat_line" selector).
StatKey = Literal[
    "points",
    "rebounds",
    "offensive_rebounds",
    "defensive_rebounds",
    "assists",
    "steals",
    "blocks",
    "turnovers",
    "fouls",
    "minutes",
    "field_goals",
    "three_pointers",
    "free_throws",
    "field_goal_percentage",
    "three_point_percentage",
    "free_throw_percentage",
    "plus_minus",
]

# Stats that have no ranking rule for game leaders (percentages need a
# qualification threshold; stat_line is not one number). Normalization reports
# these as unsupported ("unsupported_leader_stat") before any data call.
# Made/attempted stats (field_goals, three_pointers, free_throws) rank by made.
NON_LEADER_STATS: frozenset[str] = frozenset(
    {"stat_line", "field_goal_percentage", "three_point_percentage", "free_throw_percentage"}
)

# Season leaderboards (docs/ask-stage3.md): stats.nba LeagueLeaders categories.
# Percentages rank qualified shooters and have no per-game measure.
LEADER_PERCENTAGES: frozenset[str] = frozenset(
    {"field_goal_percentage", "three_point_percentage", "free_throw_percentage"}
)
SEASON_LEADER_STATS: frozenset[str] = frozenset(
    {"points", "rebounds", "offensive_rebounds", "defensive_rebounds", "assists", "steals", "blocks",
     "turnovers", "minutes", "field_goals", "three_pointers", "free_throws"}
) | LEADER_PERCENTAGES
DEFAULT_LEADER_LIMIT = 10
MAX_LEADER_LIMIT = 25

# Total vs per-game. Single-game requests are always "total"; "per_game" exists
# so a question that asks for an average is represented explicitly (and then
# rejected as unsupported in Phase 1) instead of silently answered as a total.
Aggregation = Literal["total", "per_game"]

# Modern names; resolvers map historical round structures onto these.
PlayoffRound = Literal["first_round", "conference_semifinals", "conference_finals", "finals"]
Conference = Literal["east", "west"]

SEASON_PATTERN = r"^\d{4}-\d{2}$"


def validate_season(value: str) -> str:
    start, end = value.split("-")
    if (int(start) + 1) % 100 != int(end):
        raise ValueError(f"season {value!r} must span consecutive years, e.g. 2023-24")
    return value


# NBA season label, e.g. "2023-24" (the 2024 playoffs belong to season 2023-24).
Season = Annotated[str, StringConstraints(pattern=SEASON_PATTERN), AfterValidator(validate_season)]


class TeamRef(ContractModel):
    """A team resolved to its authoritative NBA team ID.

    ``name``/``tricode`` are as of the relevant date (historical names allowed,
    e.g. Seattle SuperSonics), ``team_id`` is the franchise ID.
    """

    team_id: int = Field(ge=1)
    tricode: str = Field(min_length=2, max_length=4)
    name: str = Field(min_length=1, max_length=80)


class HomeTenure(ContractModel):
    """A team's home arena was in the city from ``start`` to ``end`` (inclusive; None = present)."""

    team: TeamRef
    start: date
    end: date | None = None


class GameLocation(ContractModel):
    """Where games are played (ADR 0011): a city and which teams were based there, when.

    Game search keeps a game only if its home team had a tenure in this city on the
    game's date, so "games in Brooklyn" in 2005 matches nothing (the Nets were in
    New Jersey).
    """

    city: str = Field(min_length=1, max_length=40)
    homes: list[HomeTenure] = Field(min_length=1, max_length=4)

    def hosts(self, team_id: int, day: date) -> bool:
        return any(h.team.team_id == team_id and h.start <= day and (h.end is None or day <= h.end)
                   for h in self.homes)

    def any_tenure(self, start: date, end: date) -> bool:
        return any(h.start <= end and (h.end is None or start <= h.end) for h in self.homes)



class PlayerRef(ContractModel):
    player_id: int = Field(ge=1)
    name: str = Field(min_length=1, max_length=80)


class DateRange(ContractModel):
    """Inclusive America/New_York calendar range, at most seven days."""

    start: date
    end: date

    @model_validator(mode="after")
    def _check_span(self) -> DateRange:
        if self.end < self.start:
            raise ValueError("end must not be before start")
        if (self.end - self.start).days >= MAX_GAME_SEARCH_DAYS:
            raise ValueError(f"date ranges are limited to {MAX_GAME_SEARCH_DAYS} days")
        return self


RelativeDate = Literal[
    "today",
    "tonight",
    "yesterday",
    "last_night",
    "tomorrow",
    "this_week",  # Monday-Sunday containing the reference date
    "last_week",  # preceding Monday-Sunday
    "last_weekday",  # most recent past <weekday>, excluding today
    "this_weekday",  # <weekday> in the current Monday-Sunday week
    "past_days",  # the last <count> days ending on the reference date
]
Weekday = Literal["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


class DateComponents(ContractModel):
    """Date language decomposed into components; Python resolves them.

    A calendar date without a year is kept as ``year=None`` and must lead to
    clarification. Never default the year.
    """

    kind: Literal["calendar_date", "calendar_range", "relative"]
    year: int | None = Field(default=None, ge=1946, le=2100)
    month: int | None = Field(default=None, ge=1, le=12)
    day: int | None = Field(default=None, ge=1, le=31)
    end_year: int | None = Field(default=None, ge=1946, le=2100)
    end_month: int | None = Field(default=None, ge=1, le=12)
    end_day: int | None = Field(default=None, ge=1, le=31)
    relative: RelativeDate | None = None
    weekday: Weekday | None = None
    # Not capped at seven: "past 10 days" must reach range_too_long clarification.
    count: int | None = Field(default=None, ge=1, le=MAX_RELATIVE_DAY_COUNT)

    @model_validator(mode="after")
    def _check_kind(self) -> DateComponents:
        if self.kind == "relative":
            if self.relative is None:
                raise ValueError("relative dates need `relative`")
            if self.relative in ("last_weekday", "this_weekday") and self.weekday is None:
                raise ValueError(f"{self.relative} needs `weekday`")
            if self.relative == "past_days" and self.count is None:
                raise ValueError("past_days needs `count`")
        else:
            if self.relative is not None:
                raise ValueError("calendar dates must not set `relative`")
            if self.month is None or self.day is None:
                raise ValueError("calendar dates need month and day")
            if self.kind == "calendar_range" and (self.end_month is None or self.end_day is None):
                raise ValueError("calendar ranges need end_month and end_day")
        return self
