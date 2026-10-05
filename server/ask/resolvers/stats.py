"""Statistic definitions: contract ``StatKey`` -> BoxScoreTraditionalV3 fields.

Definitions live here, separate from the aliases candidate lookup maintains.
All values are single-game values read from a V3 ``statistics`` object.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Literal

from server.ask.models.common import Aggregation, Stat, StatKey
from server.ask.models.response import StatValue
from server.ask.resolvers.errors import UnsupportedError

StatKind = Literal["count", "shooting", "percentage", "minutes", "plus_minus"]


@dataclass(frozen=True)
class StatDef:
    key: StatKey
    kind: StatKind
    field: str  # count/percentage/minutes/plus_minus: the V3 field
    made: str | None = None  # shooting and percentage: made/attempted fields
    attempted: str | None = None

    @property
    def rankable(self) -> bool:
        # A 1-for-1 shooter would "lead" a percentage; no qualifier is defined.
        return self.kind != "percentage"


STATS: dict[str, StatDef] = {
    d.key: d
    for d in (
        StatDef("points", "count", "points"),
        StatDef("rebounds", "count", "reboundsTotal"),
        StatDef("offensive_rebounds", "count", "reboundsOffensive"),
        StatDef("defensive_rebounds", "count", "reboundsDefensive"),
        StatDef("assists", "count", "assists"),
        StatDef("steals", "count", "steals"),
        StatDef("blocks", "count", "blocks"),
        StatDef("turnovers", "count", "turnovers"),
        StatDef("fouls", "count", "foulsPersonal"),
        StatDef("minutes", "minutes", "minutes"),
        StatDef("field_goals", "shooting", "fieldGoalsMade", "fieldGoalsMade", "fieldGoalsAttempted"),
        StatDef("three_pointers", "shooting", "threePointersMade", "threePointersMade", "threePointersAttempted"),
        StatDef("free_throws", "shooting", "freeThrowsMade", "freeThrowsMade", "freeThrowsAttempted"),
        StatDef("field_goal_percentage", "percentage", "fieldGoalsPercentage", "fieldGoalsMade", "fieldGoalsAttempted"),
        StatDef("three_point_percentage", "percentage", "threePointersPercentage", "threePointersMade", "threePointersAttempted"),
        StatDef("free_throw_percentage", "percentage", "freeThrowsPercentage", "freeThrowsMade", "freeThrowsAttempted"),
        StatDef("plus_minus", "plus_minus", "plusMinusPoints"),
    )
}

# Order of a full line ("stat_line") for each scope.
PLAYER_LINE: tuple[StatKey, ...] = (
    "minutes", "points", "rebounds", "assists", "steals", "blocks", "turnovers", "fouls",
    "field_goals", "three_pointers", "free_throws", "plus_minus",
)
TEAM_LINE: tuple[StatKey, ...] = (
    "points", "rebounds", "offensive_rebounds", "assists", "steals", "blocks", "turnovers", "fouls",
    "field_goals", "three_pointers", "free_throws",
)

MISSING_DISPLAY = "—"


def check_aggregation(aggregation: Aggregation) -> None:
    """Single-game values are totals. A per-game average is never answered as a total."""
    if aggregation != "total":
        raise UnsupportedError("multi_game_average", "per_game_unsupported", "Per-game averages are not supported")


def stat_defs(stat: Stat, line: tuple[StatKey, ...]) -> tuple[StatDef, ...]:
    if stat == "stat_line":
        return tuple(STATS[key] for key in line)
    try:
        return (STATS[stat],)
    except KeyError:
        raise UnsupportedError("other", "unknown_stat", f"Unknown statistic {stat!r}") from None


def minutes_to_seconds(value) -> float | None:
    """Parse V3 minutes ("34:12", "PT34M12.00S") to seconds."""
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip()
    if match := re.fullmatch(r"(\d+):(\d{1,2})(?:\.\d+)?", text):
        return int(match[1]) * 60 + int(match[2])
    if match := re.fullmatch(r"PT(\d+)M(\d+(?:\.\d+)?)S", text):
        return int(match[1]) * 60 + float(match[2])
    return None


def _number(statistics: dict, field: str | None):
    value = statistics.get(field) if field else None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value if math.isfinite(value) else None


def _int(value) -> int | None:
    return None if value is None else int(value)


def stat_value(statistics, definition: StatDef) -> StatValue:
    """One contract ``StatValue``; ``value`` is None when the source lacks it."""
    statistics = statistics if isinstance(statistics, dict) else {}
    key = definition.key
    if definition.kind == "minutes":
        seconds = minutes_to_seconds(statistics.get(definition.field))
        if seconds is None:
            return StatValue(stat=key, value=None, display=MISSING_DISPLAY)
        whole = int(seconds)
        return StatValue(stat=key, value=round(seconds / 60, 2), display=f"{whole // 60}:{whole % 60:02d}")
    if definition.kind in ("shooting", "percentage"):
        made, attempted = _number(statistics, definition.made), _number(statistics, definition.attempted)
        made_int, attempted_int = _int(made), _int(attempted)
        if definition.kind == "shooting":
            if made is None or attempted is None:
                return StatValue(stat=key, value=None, display=MISSING_DISPLAY, made=made_int, attempted=attempted_int)
            return StatValue(stat=key, value=made, display=f"{made_int}-{attempted_int}", made=made_int, attempted=attempted_int)
        percentage = _number(statistics, definition.field)
        if percentage is None or attempted is None:
            return StatValue(stat=key, value=None, display=MISSING_DISPLAY, made=made_int, attempted=attempted_int)
        if attempted == 0:
            # 0-for-0 has no percentage; the source reports 0.0.
            return StatValue(stat=key, value=None, display=MISSING_DISPLAY, made=made_int, attempted=0)
        return StatValue(stat=key, value=percentage, display=f"{percentage * 100:.1f}%", made=made_int, attempted=attempted_int)
    value = _number(statistics, definition.field)
    if value is None:
        return StatValue(stat=key, value=None, display=MISSING_DISPLAY)
    whole = int(value) if float(value).is_integer() else value
    display = f"{whole:+d}" if definition.kind == "plus_minus" and isinstance(whole, int) and whole else str(whole)
    return StatValue(stat=key, value=value, display=display)
