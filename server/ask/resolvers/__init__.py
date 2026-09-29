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

import dataclasses

from server.ask.models.request import (
    AskRequest,
    BoxscoreStatRequest,
    GameSearchRequest,
    PlayoffSeriesRequest,
    PostseasonSummaryRequest,
)
from server.ask.resolvers import boxscore, games, playoffs
from server.ask.resolvers.errors import AmbiguousError, NotFoundError
from server.ask.resolvers.games import ResolvedGame
from server.ask.resolvers.output import ResolverOutput, stats_source
from server.ask import links


def resolve_boxscore_game(request: BoxscoreStatRequest) -> ResolvedGame:
    """Find the one game a boxscore request refers to."""
    selector = request.game
    team_ids = [team.team_id for team in selector.teams]
    if request.team and request.team.team_id not in team_ids:
        team_ids.append(request.team.team_id)
    if selector.game_id:
        game = games.get_game(selector.game_id, selector.date)
    elif selector.date:
        if request.scope == "player" and not team_ids:
            game, _ = games.find_player_game(request.player.player_id, selector.date)
        else:
            game = games.find_game_on_date(selector.date, team_ids)
    else:
        game = playoffs.find_playoff_game(
            selector.season, selector.game_number, [team.team_id for team in selector.teams], selector.round, selector.conference
        )
    missing = [team_id for team_id in team_ids if team_id not in game.team_ids]
    if missing:
        raise NotFoundError("no_games", "team_not_in_game", details={"gameId": game.game_id, "teamIds": missing})
    return dataclasses.replace(game, named_team_ids=tuple(team_ids))


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
    game_links = tuple(link.model_copy(update={"spoiler": game.participants_inferred and not set(game.team_ids) <= set(game.named_team_ids)})
                       for link in (links.boxscore_link(game.game_id, game.date), links.scores_link(game.date)))
    return ResolverOutput(result, game_links, (stats_source(game.settled),))


def resolve(request: AskRequest) -> ResolverOutput:
    """Execute one validated request. Raises ``errors.ResolverError`` subclasses."""
    if isinstance(request, GameSearchRequest):
        return games.search_games(request.dates, [team.team_id for team in request.teams])
    if isinstance(request, BoxscoreStatRequest):
        return _boxscore(request)
    if isinstance(request, PlayoffSeriesRequest):
        return playoffs.series_result(request.season, [team.team_id for team in request.teams], request.round, request.conference)
    if isinstance(request, PostseasonSummaryRequest):
        if request.team is None:
            return playoffs.league_postseason(request.season)
        return playoffs.team_postseason(request.season, request.team)
    raise TypeError(f"Unsupported request {type(request).__name__}")


__all__ = ["AmbiguousError", "NotFoundError", "ResolverOutput", "resolve", "resolve_boxscore_game"]
