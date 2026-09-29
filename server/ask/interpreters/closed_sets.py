"""Closed-set option descriptions shared by every adapter.

Keys come from the contract enums (`server.ask.models`); a test checks coverage, so an
enum change fails loudly instead of silently dropping an option.
"""

from __future__ import annotations

from typing import get_args

from server.ask.models.common import Aggregation, Intent, Stat, StatScope
from server.ask.models.interpreter import UnsupportedReason

# Sentinel options for candidate-backed Choices.
NONE_OPTION = "__none__"
OTHER_OPTION = "__other__"
# Extra intent option; maps to outcome="unsupported".
UNSUPPORTED_INTENT = "unsupported"

INTENTS: dict[str, str] = {
    "game_search": (
        "Find NBA games on one date or within a span of up to seven days, optionally for "
        "specific teams (e.g. 'Cavs games last week', 'games on Jan 23, 2025'). "
        "A date range longer than seven days still has this intent; the date field "
        "will need a range_too_long clarification. An unknown team name does not "
        "make the request unsupported."
    ),
    "boxscore_stat": (
        "Statistics from one game's box score, selected by date, teams, player, or "
        "playoff game: one player's line or statistic, one team's totals, or who "
        "led the game in a statistic (e.g. 'How many points did "
        "Tatum score in game 4 of the 2024 Finals?', 'Who had the most assists last night "
        "in Knicks vs Heat?'). An unknown player or team name still has this intent; "
        "its entity field must be no_matching_candidate."
    ),
    "playoff_series": (
        "The result or status of one playoff series or a specified playoff round, "
        "even if its teams or round need clarification (e.g. 'Who won the 2023 "
        "Finals?', 'Celtics vs Heat 2022 series', '2024 conference finals')."
    ),
    "postseason_summary": (
        "A whole postseason tournament, or one team's overall run through it "
        "(e.g. '2016 playoffs', 'How did the Nuggets do in the 2023 playoffs?'). "
        "A request for a particular series belongs to playoff_series even when "
        "the requested series is underspecified."
    ),
    UNSUPPORTED_INTENT: (
        "Anything else: career or season-long statistics, season leaders, standings or "
        "regular-season records, comparisons across games or seasons, averages over several "
        "games, predictions, follow-ups that depend on an earlier answer, glossary or "
        "biography questions, or questions not about NBA basketball."
    ),
}

UNSUPPORTED_REASONS: dict[str, str] = {
    "career_stats": "Career totals or career averages",
    "season_stats": "A player's or team's statistics over a whole season",
    "season_leaders": "Who led the league or a season in a statistic",
    "historical_comparison": "Comparing players, teams, games, or eras",
    "prediction": "Predictions or future outcomes",
    "follow_up": "Refers to an earlier answer ('what about him?', 'and the next game?')",
    "regular_season_record": "A team's regular-season win-loss record",
    "standings": "League or conference standings",
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
    "total": "The total in a single game (the normal case)",
    "per_game": "An average or per-game figure across several games",
}

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
        (UNSUPPORTED_REASONS, set(get_args(UnsupportedReason))),
        (STAT_SCOPES, set(get_args(StatScope))),
        (AGGREGATIONS, set(get_args(Aggregation))),
        (STATS, set(get_args(Stat))),
    )
    for table, values in pairs:
        if set(table) != values:
            raise AssertionError(f"closed set mismatch: {sorted(set(table) ^ values)}")
