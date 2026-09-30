"""Closed-set option descriptions shared by every adapter.

Keys come from the contract enums (`server.ask.models`); a test checks coverage, so an
enum change fails loudly instead of silently dropping an option.
"""

from __future__ import annotations

from typing import get_args

from server.ask import tools
from server.ask.models.common import Aggregation, Intent, Stat, StatScope, SeasonType, StandingsScope
from server.ask.models.interpreter import UnsupportedReason, LEGACY_UNSUPPORTED_REASONS

# Sentinel options for candidate-backed Choices.
NONE_OPTION = "__none__"
OTHER_OPTION = "__other__"
# Router options come from the tool registry: every registered tool, then "unsupported",
# which maps to outcome="unsupported".
UNSUPPORTED_INTENT = tools.UNSUPPORTED

INTENTS: dict[str, str] = tools.router_options()

UNSUPPORTED_REASONS: dict[str, str] = {
    "career_stats": "Career totals or career averages, when the question asks about a whole career",
    "historical_comparison": "Comparing players, teams, games, or eras",
    "prediction": "Predictions or future outcomes",
    "follow_up": "Refers to an earlier answer ('what about him?', 'and the next game?')",
    "reference_question": "Definitions, rules, glossary, or biography questions",
    "multi_game_average": "Averages or per-game figures across several games",
    "unsupported_leader_stat": "Game leaders for percentages or an entire stat line without a ranking rule",
    "not_basketball": "Not about NBA basketball",
    "other": "Some other request outside NBA games and playoff results",
}

STAT_SCOPES: dict[str, str] = {
    "player": "One player's statistics in the game",
    "team": "One team's totals in the game",
    "leaders": "Which player led the game (or one team in the game) in a statistic",
}

AGGREGATIONS: dict[str, str] = {
    "total": "Total over the requested game or season",
    "per_game": "Average per game over the requested season",
}

SEASON_TYPES = {"regular_season": "NBA regular season, excluding playoffs and play-in", "playoffs": "NBA playoffs only, excluding play-in"}
STANDINGS_SCOPES = {"league": "Whole NBA league, or no conference filter", "east": "Eastern conference only", "west": "Western conference only"}

STATS: dict[str, str] = {
    "stat_line": "The full stat line, or no particular statistic named ('how did he play?')",
    "points": "Points scored",
    "rebounds": "Total rebounds (boards)",
    "offensive_rebounds": "Offensive rebounds",
    "defensive_rebounds": "Defensive rebounds",
    "assists": "Assists (dimes)",
    "steals": "Steals",
    "blocks": "Blocked shots",
    "turnovers": "Turnovers",
    "fouls": "Personal fouls",
    "minutes": "Minutes played",
    "field_goals": "Field goals made/attempted (shots made)",
    "three_pointers": "Three-pointers made/attempted (threes, 3s)",
    "free_throws": "Free throws made/attempted",
    "field_goal_percentage": "Field goal percentage (shooting percentage)",
    "three_point_percentage": "Three-point percentage",
    "free_throw_percentage": "Free throw percentage",
    "plus_minus": "Plus-minus",
}


def check_coverage() -> None:
    """Raise if a contract enum value has no description here."""
    pairs = (
        (INTENTS, set(get_args(Intent)) | {UNSUPPORTED_INTENT}),
        (UNSUPPORTED_REASONS, set(get_args(UnsupportedReason)) - LEGACY_UNSUPPORTED_REASONS),
        (STAT_SCOPES, set(get_args(StatScope))),
        (AGGREGATIONS, set(get_args(Aggregation))),
        (STATS, set(get_args(Stat))),
        (SEASON_TYPES, set(get_args(SeasonType))),
        (STANDINGS_SCOPES, set(get_args(StandingsScope))),
    )
    for table, values in pairs:
        if set(table) != values:
            raise AssertionError(f"closed set mismatch: {sorted(set(table) ^ values)}")
