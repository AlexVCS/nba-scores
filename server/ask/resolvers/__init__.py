"""Reusable basketball resolvers and calculators for Ask (#201).

These functions take typed arguments (contract ``AskRequest`` models, or
dates, integer team/player IDs, seasons and contract enums) and return
contract result payloads (``server.ask.models.response``) wrapped in a
``ResolverOutput`` with verified links and source metadata. They have no
dependency on any model, provider, prompt, HTTP request object or web
framework, so each can be wrapped as an allowlisted tool and called the same
way by the pipeline, direct navigation, validation, scripts and evaluations.
Entity names, aliases and relative dates are resolved before these run
(candidate lookup, #200); resolvers never guess an entity.

Data comes only from the existing cached services (scoreboard, game_data,
playoffs); the player-by-date game lookup adds its own bounded cache because
no shared one exists.

Outcomes: a result, or an exception from ``errors`` that maps onto one
``AskResponse`` outcome (``not_found``, ``unavailable``,
``needs_clarification``, ``unsupported``). ``ValueError`` means a caller
passed arguments the contract models would have rejected.

Request types:

* game search: ``games.search_games``
* single-game boxscore statistics: resolve the game (``games.get_game``,
  ``games.find_game_on_date``, ``games.find_player_game``,
  ``playoffs.find_playoff_game``), then ``boxscore.player_stat``,
  ``boxscore.team_stat`` or ``boxscore.stat_leaders``
* playoff series result: ``playoffs.series_result``
* postseason summary: ``playoffs.league_postseason`` or ``playoffs.team_postseason``

``resolve`` dispatches a validated ``AskRequest`` to them.
"""

from __future__ import annotations

from typing import Callable

from server.ask.models.request import (
    AskRequest,
    BoxscoreStatRequest,
    GameSearchRequest,
    PlayoffSeriesRequest,
    PostseasonSummaryRequest,
    PlayerSeasonStatsRequest,
    TeamRecordsRequest,
)
from server.ask.resolvers import boxscore, career, games, leaders, playoffs, seasons
from server.ask.resolvers.errors import AmbiguousError, ClarificationError, NotFoundError
from server.ask.resolvers.games import ResolvedGame
from server.ask.resolvers.output import ResolverOutput, stats_source
from server.ask.resolvers.spoiler_policy import outcome_may_reveal_result
from server.ask import links, tools
from server.utils.deadline import Deadline


def resolve_boxscore_game(request: BoxscoreStatRequest) -> ResolvedGame:
    """Find the one game a boxscore request refers to."""
    selector = request.game
    team_ids = [team.team_id for team in selector.teams]
    if request.team and request.team.team_id not in team_ids:
        team_ids.append(request.team.team_id)
    if selector.game_id:
        game = games.get_game(selector.game_id, selector.date)
    elif selector.season and selector.game_number and (selector.round or len(team_ids) == 2):
        game = playoffs.find_playoff_game(
            selector.season, selector.game_number, team_ids, selector.round, selector.conference
        )
    elif selector.date:
        if request.scope == "player" and not team_ids:
            game, _ = games.find_player_game(request.player.player_id, selector.date)
        else:
            game = games.find_game_on_date(selector.date, team_ids)
    else:
        game = playoffs.find_playoff_game(
            selector.season, selector.game_number, team_ids, selector.round, selector.conference
        )
    # GameSelector permits a date together with playoff details. Both describe
    # the same game; neither can be discarded merely because one located it.
    if selector.date and game.date != selector.date:
        raise NotFoundError("no_games", "date_not_matching_game", details={"date": selector.date.isoformat()})
    if selector.date and selector.season and games.season_for_game_id(game.game_id) != selector.season:
        raise NotFoundError("no_games", "season_not_matching_game", details={"season": selector.season})
    if selector.date and selector.round:
        if game.round is None:
            raise ClarificationError("round", "missing", "round_unverifiable")
        if game.round != selector.round:
            raise NotFoundError("no_games", "round_not_matching_game", details={"round": selector.round})
    if selector.date and selector.game_number:
        if game.game_number is None:
            raise ClarificationError("game_number", "missing", "game_number_unverifiable")
        if game.game_number != selector.game_number:
            raise NotFoundError("no_games", "game_number_not_matching_game", details={"gameNumber": selector.game_number})
    if selector.date and selector.conference and not (selector.season and selector.game_number and (selector.round or len(team_ids) == 2)):
        raise ClarificationError("teams", "missing", "conference_unverifiable")
    missing = [team_id for team_id in team_ids if team_id not in game.team_ids]
    if missing:
        raise NotFoundError("no_games", "team_not_in_game", details={"gameId": game.game_id, "teamIds": missing})
    return game


def _boxscore(request: BoxscoreStatRequest) -> ResolverOutput:
    game = resolve_boxscore_game(request)
    stat, aggregation = request.stat.stat, request.stat.aggregation
    if request.scope == "player":
        result = boxscore.player_stat(game, request.player.player_id, stat, aggregation)
    elif request.scope == "team":
        team_ids = [request.team.team_id] if request.team else [team.team_id for team in request.game.teams]
        result = boxscore.team_stat(game, stat, team_ids, aggregation)
    else:
        result = boxscore.stat_leaders(game, stat, request.team.team_id if request.team else None, aggregation)
    # Links to the game that was asked about are part of the answer, not spoilers.
    game_links = (links.boxscore_link(game.game_id, game.date), links.scores_link(game.date))
    return ResolverOutput(result, game_links, (stats_source(game.settled),))


def resolve(request: AskRequest, *, deadline: Deadline | None = None) -> ResolverOutput:
    """Execute one validated request. Raises ``errors.ResolverError`` subclasses.

    ``deadline`` is the time left in the Ask response. Executors named in
    ``DEADLINE_EXECUTORS`` share it across source attempts and fallback."""
    # Asking is consent, so answers are never gated (ADR 0006). Clarifications
    # are not answers: when a lookup-dependent choice list could reveal a
    # result, ask for teams first, before any result lookup.
    if isinstance(request, BoxscoreStatRequest) and outcome_may_reveal_result(request):
        selector = request.game
        named_teams = bool(selector.teams or request.team)
        unique_series = bool(selector.season and selector.game_number and (
            selector.round == "finals" or
            (selector.round == "conference_finals" and selector.conference)
        ))
        ambiguous_round = bool(selector.round and not selector.date and not unique_series)
        ambiguous_date = bool(selector.date and request.scope in ("leaders", "team") and not unique_series)
        if not named_teams and not selector.game_id and (ambiguous_round or ambiguous_date):
            # A lookup-dependent clarification would reveal whether a
            # conditional playoff game took place on this date or in this round.
            raise ClarificationError("teams", "missing", "hidden_game_needs_teams")
    return _resolve(request, deadline)


def _search_games(request: GameSearchRequest) -> ResolverOutput:
    return games.search_games(request.dates, [team.team_id for team in request.teams], request.location)


def _series(request: PlayoffSeriesRequest) -> ResolverOutput:
    return playoffs.series_result(request.season, [team.team_id for team in request.teams], request.round, request.conference)


def _postseason(request: PostseasonSummaryRequest) -> ResolverOutput:
    if request.team is None:
        return playoffs.league_postseason(request.season)
    return playoffs.team_postseason(request.season, request.team)


# Executor per registered tool (`server.ask.tools`); `test_tools.py` checks coverage.
EXECUTORS: dict[str, Callable[..., ResolverOutput]] = {
    "game_search": _search_games,
    "boxscore_stat": _boxscore,
    "playoff_series": _series,
    "postseason_summary": _postseason,
    "player_season_stats": seasons.player_season,
    "team_records": seasons.team_records,
    "season_leaders": leaders.season_leaders,
    "career_stats": career.career_stats,
}
# Executors that accept ``deadline=``. Others keep their own source timeouts,
# bounded overall by the HTTP response deadline.
DEADLINE_EXECUTORS: frozenset[str] = frozenset({"player_season_stats", "team_records", "season_leaders", "career_stats"})


def _resolve(request: AskRequest, deadline: Deadline | None = None) -> ResolverOutput:
    tool = tools.route(getattr(request, "intent", ""))
    if tool is None or not isinstance(request, tool.request_model):
        raise TypeError(f"Unsupported request {type(request).__name__}")
    if deadline is not None and tool.name in DEADLINE_EXECUTORS:
        return EXECUTORS[tool.name](request, deadline=deadline)
    return EXECUTORS[tool.name](request)


__all__ = ["DEADLINE_EXECUTORS", "EXECUTORS", "AmbiguousError", "NotFoundError", "ResolverOutput", "resolve", "resolve_boxscore_game"]
