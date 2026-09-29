"""Value types shared by every part of the Ask contract.

Frozen contract (docs/ask-contract.md). Coordinate before changing.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Generic, Literal, TypeVar

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints, model_validator

SCHEMA_VERSION = "1"
NEW_YORK_TZ = "America/New_York"
MAX_GAME_SEARCH_DAYS = 7
MAX_QUESTION_LENGTH = 300


class ContractModel(BaseModel):
    """Strict, immutable base for contract models (unknown keys are errors)."""

    model_config = ConfigDict(extra="forbid", frozen=True)


Intent = Literal["game_search", "boxscore_stat", "playoff_series", "postseason_summary"]

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
    count: int | None = Field(default=None, ge=1, le=MAX_GAME_SEARCH_DAYS)

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


T = TypeVar("T")


class Guarded(ContractModel, Generic[T]):
    """A value that may be a spoiler.

    When ``spoiler`` is true and results are hidden, the UI must omit ``value``
    from the DOM and accessibility text (not merely hide it visually).
    """

    value: T
    spoiler: bool
