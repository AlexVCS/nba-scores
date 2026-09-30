"""Ask tool registry and router options (ADR 0001, ADR 0010 stage 1).

A tool is one answerable question family: a typed request model that Python validates,
the interpreter fields it reads, and a router description. The router is the `intent`
Choice every interpreter answers: one of the registered tools, or `unsupported`.
Execution is bound separately, by tool name, in `server.ask.resolvers.EXECUTORS`, so
this module stays free of NBA service imports and adapters can import it cheaply.

Adding a family (ADR 0004) means: register an `AskTool` here, add the request model to
the contract, a normalizer builder, an executor, an answer template, and a spoiler
classification. `server/tests/ask/test_tools.py` fails until every layer covers every
registered tool. A family that fails its gate stays out of `TOOLS`; the router then
reads it as `unsupported` (ADR 0010).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import get_args

from pydantic import BaseModel

from server.ask.models.common import Intent
from server.ask.models.request import (
    BoxscoreStatRequest,
    GameSearchRequest,
    PlayoffSeriesRequest,
    PostseasonSummaryRequest,
    CareerStatsRequest,
    PlayerSeasonStatsRequest,
    SeasonLeadersRequest,
    TeamRecordsRequest,
)

# The router's extra option; an interpreter choosing it returns outcome="unsupported".
UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class AskTool:
    name: Intent
    # Router criterion shown to every interpreter. Changing it changes prompts and
    # parse-cache keys, so it is part of the frozen evaluation surface.
    description: str
    request_model: type[BaseModel]
    # Interpreter fields the tool reads besides `intent`. A read on any other field is
    # ignored, so a stray value never changes or blocks the request.
    fields: frozenset[str]


# Order is the router's option order; it feeds the prompts, so keep it stable.
TOOLS: tuple[AskTool, ...] = (
    AskTool(
        name="game_search",
        description=(
            "Find NBA games on one date or within a span of up to seven days, optionally for "
            "specific teams (e.g. 'Cavs games last week', 'games on Jan 23, 2025'). "
            "A date range longer than seven days still has this intent; the date field "
            "will need a range_too_long clarification. An unknown team name does not "
            "make the request unsupported."
        ),
        request_model=GameSearchRequest,
        fields=frozenset({"date", "teams", "location"}),
    ),
    AskTool(
        name="boxscore_stat",
        description=(
            "Statistics from one game's box score, selected by date, teams, player, or "
            "playoff game: one player's line or statistic, one team's totals, or who "
            "led the game in a statistic (e.g. 'How many points did "
            "Tatum score in game 4 of the 2024 Finals?', 'Who had the most assists last night "
            "in Knicks vs Heat?'). An unknown player or team name still has this intent; "
            "its entity field must be no_matching_candidate. A game statistic asked "
            "without naming the game ('How many assists did Jordan have?') still has "
            "this intent; the missing date requires clarification."
        ),
        request_model=BoxscoreStatRequest,
        fields=frozenset({"stat_scope", "stat", "aggregation", "player", "teams", "target_team", "date",
                          "season", "round", "game_number"}),
    ),
    AskTool(
        name="playoff_series",
        description=(
            "A request framed as a playoff series, matchup, or particular round. "
            "It stays this intent when only a season or one team is given; the missing "
            "round or opponent requires clarification. 'Series' alone, singular or "
            "plural, does not ask for every series (e.g. 'Who won the Finals?', "
            "'a team's playoff series', 'conference finals')."
        ),
        request_model=PlayoffSeriesRequest,
        fields=frozenset({"season", "teams", "round"}),
    ),
    AskTool(
        name="postseason_summary",
        description=(
            "An explicitly whole postseason tournament, all/every series, or one "
            "team's overall playoff run (e.g. '2016 playoffs', 'Show every 2024 "
            "playoff series', 'How did the Nuggets do in the 2023 playoffs?'). "
            "One named team does not imply whole-run scope when the request is "
            "framed as a series."
        ),
        request_model=PostseasonSummaryRequest,
        fields=frozenset({"season", "teams"}),
    ),
    AskTool(
        name="player_season_stats",
        description=("One player's totals or per-game averages in one NBA season, regular season "
                     "or playoffs (e.g. 'Jokic rebounds per game in 2023-24'). A named team "
                     "limits the answer to that stint. Missing player or season requires clarification. "
                     "Career totals, month/date splits, advanced metrics and comparisons are unsupported."),
        request_model=PlayerSeasonStatsRequest,
        fields=frozenset({"player", "teams", "season", "stat", "aggregation", "season_type"}),
    ),
    AskTool(
        name="team_records",
        description=("One team's regular-season wins and losses or NBA league/conference standings "
                     "in one season (e.g. 'Celtics record in 2007-08', '2023-24 Eastern standings'). "
                     "Missing season requires clarification. Division, home/away, date, month and opponent "
                     "splits, seeds, predictions and best-record/streak comparisons are unsupported. "
                     "Playoff results use postseason_summary instead."),
        request_model=TeamRecordsRequest,
        fields=frozenset({"teams", "season", "standings_scope", "season_type"}),
    ),
    AskTool(
        name="season_leaders",
        description=("Who led the whole NBA in one statistic in one season, regular season or "
                     "playoffs, as season totals, per-game averages or a shooting percentage "
                     "(e.g. 'Who led the league in assists per game in 2019-20?', 'top 5 in total "
                     "rebounds in 2023-24'). Missing season or statistic requires clarification. "
                     "Leaders of one game are boxscore_stat. Team, conference, position or rookie "
                     "leaders, a player's rank, career/all-time leaders and advanced metrics are not this tool."),
        request_model=SeasonLeadersRequest,
        fields=frozenset({"season", "stat", "aggregation", "season_type"}),
    ),
    AskTool(
        name="career_stats",
        description=("A whole NBA career: one player's career totals or career averages, the all-time "
                     "leaders in a counting statistic, or where a player ranks all-time (e.g. 'LeBron James "
                     "career points', 'Who has the most career assists?', 'Where does Curry rank in career "
                     "3-pointers?'). Regular season or playoffs. Career highs, single-season or single-game "
                     "records, franchise leaders and comparisons are unsupported."),
        request_model=CareerStatsRequest,
        fields=frozenset({"player", "stat", "aggregation", "season_type"}),
    ),
)

UNSUPPORTED_DESCRIPTION = (
    "Anything else: career highs, season or game records, team or franchise leaders, unsupported statistical splits, comparisons across games or seasons, averages over several "
    "games, predictions, follow-ups that depend on an earlier answer, glossary or "
    "biography questions, or questions not about NBA basketball."
)

REGISTRY: dict[str, AskTool] = {tool.name: tool for tool in TOOLS}


def router_options() -> dict[str, str]:
    """The router Choice: every registered tool, then `unsupported`, with descriptions."""
    return {**{tool.name: tool.description for tool in TOOLS}, UNSUPPORTED: UNSUPPORTED_DESCRIPTION}


def route(choice: str) -> AskTool | None:
    """The tool a router choice names, or None for `unsupported` or an unregistered name."""
    return REGISTRY.get(choice)


def check_registry() -> None:
    """Raise if the registry and the contract's `Intent` enum disagree."""
    if len(REGISTRY) != len(TOOLS):
        raise AssertionError("duplicate tool name")
    if set(REGISTRY) != set(get_args(Intent)):
        raise AssertionError(f"tool registry and Intent differ: {sorted(set(REGISTRY) ^ set(get_args(Intent)))}")
    for tool in TOOLS:
        declared = tool.request_model.model_fields["intent"].default
        if declared != tool.name:
            raise AssertionError(f"{tool.name}: request model declares intent {declared!r}")


check_registry()
