"""Single-game boxscore statistics: one player's line, team totals, game leaders.

Calculators take a ``ResolvedGame`` (from ``games`` or ``playoffs``) and read
the cached BoxScoreTraditionalV3 entry the boxscore route serves. Values are
single-game totals; a per-game aggregation is rejected as
``multi_game_average`` rather than answered as a total.

A requested statistic the source did not record is returned with
``value=None``; when none of the requested values were recorded the
calculator raises ``NotFoundError("no_record")``.
"""

from __future__ import annotations

from typing import Sequence

from server.ask.models.common import Aggregation, PlayerRef, Stat, TeamRef
from server.ask.models.response import BoxscoreStatResult, LeaderRow, PlayerStatLine, StatValue, TeamStatLine
from server.ask.resolvers import data
from server.ask.resolvers.errors import NotFoundError, UnsupportedError
from server.ask.resolvers.games import ResolvedGame, game_context, int_or_none, team_ref
from server.ask.resolvers.stats import (
    PLAYER_LINE,
    TEAM_LINE,
    StatDef,
    check_aggregation,
    stat_defs,
    stat_value,
)

MAX_LEADERS = 10


def _boxscore(game: ResolvedGame) -> dict:
    if game.status == 1:
        raise NotFoundError("no_record", "game_not_started", details={"gameId": game.game_id})
    if not game.game.get("boxscoreAvailable"):
        raise NotFoundError("no_record", "boxscore_not_available", details={"gameId": game.game_id})
    return data.boxscore(game.game_id)


def _sides(boxscore: dict, game: ResolvedGame) -> list[tuple[TeamRef, dict]]:
    sides = []
    for key, fallback in (("homeTeam", game.home), ("awayTeam", game.away)):
        side = boxscore.get(key) if isinstance(boxscore.get(key), dict) else {}
        sides.append((team_ref(side) or fallback, side))
    return sides


def _player_ref(player: dict, person_id: int) -> PlayerRef | None:
    name = " ".join(filter(None, (str(player.get("firstName") or "").strip(), str(player.get("familyName") or "").strip())))
    name = name or str(player.get("nameI") or player.get("name") or "").strip()
    return PlayerRef(player_id=person_id, name=name) if name else None


def _played(player: dict) -> bool:
    # Matches StatsTable: an empty minutes string means the player did not play.
    statistics = player.get("statistics")
    minutes = statistics.get("minutes") if isinstance(statistics, dict) else None
    if isinstance(minutes, str):
        return minutes.strip() != ""
    return not str(player.get("comment") or "").strip()


def _values(statistics, definitions: Sequence[StatDef], game: ResolvedGame) -> list[StatValue]:
    values = [stat_value(statistics, definition) for definition in definitions]
    if all(value.value is None for value in values):
        raise NotFoundError(
            "no_record", "stat_not_recorded", details={"gameId": game.game_id, "stats": [d.key for d in definitions]}
        )
    return values


def _result(game: ResolvedGame, scope, stat: Stat, **payload) -> BoxscoreStatResult:
    return BoxscoreStatResult(scope=scope, stat=stat, aggregation="total", game=game_context(game), **payload)


def player_stat(game: ResolvedGame, player_id: int, stat: Stat, aggregation: Aggregation = "total") -> BoxscoreStatResult:
    """One player's statistic (or full line with ``stat_line``) in one game.

    A player listed but not playing returns status ``did_not_play`` or
    ``inactive`` with no values. A player not listed at all is
    ``player_did_not_play``.
    """
    check_aggregation(aggregation)
    definitions = stat_defs(stat, PLAYER_LINE)
    boxscore = _boxscore(game)
    for team, side in _sides(boxscore, game):
        for player in side.get("players") or []:
            if not isinstance(player, dict) or int_or_none(player.get("personId")) != player_id:
                continue
            ref = _player_ref(player, player_id)
            if ref is None:
                continue
            if _played(player):
                line = PlayerStatLine(
                    player=ref, team=team, status="played",
                    values=_values(player.get("statistics"), definitions, game),
                )
            else:
                inactive = str(player.get("status") or "").upper() == "INACTIVE"
                line = PlayerStatLine(player=ref, team=team, status="inactive" if inactive else "did_not_play", values=[])
            return _result(game, "player", stat, player_line=line)
    raise NotFoundError("player_did_not_play", "player_not_in_boxscore", details={"playerId": player_id, "gameId": game.game_id})


def team_stat(
    game: ResolvedGame, stat: Stat, team_ids: Sequence[int] = (), aggregation: Aggregation = "total"
) -> BoxscoreStatResult:
    """Team totals for one game: the listed teams (one or two), or both when empty."""
    check_aggregation(aggregation)
    definitions = stat_defs(stat, TEAM_LINE)
    missing = [team_id for team_id in team_ids if team_id not in game.team_ids]
    if missing:
        raise NotFoundError("no_record", "team_not_in_game", details={"teamIds": missing, "gameId": game.game_id})
    boxscore = _boxscore(game)
    lines = [
        TeamStatLine(team=team, values=_values(side.get("statistics"), definitions, game))
        for team, side in _sides(boxscore, game)
        if not team_ids or team.team_id in team_ids
    ]
    return _result(game, "team", stat, team_lines=lines)


def stat_leaders(
    game: ResolvedGame, stat: Stat, team_id: int | None = None, aggregation: Aggregation = "total"
) -> BoxscoreStatResult:
    """Each team's leader(s) in one statistic, ranked together; ties share a rank.

    With ``team_id``, only that team's leader(s). Only players who played are
    ranked; if any of them lacks the statistic the ranking would be partial,
    so the calculator raises ``no_record``.
    """
    check_aggregation(aggregation)
    if stat == "stat_line":
        raise UnsupportedError("unsupported_leader_stat", "leaders_need_one_stat")
    (definition,) = stat_defs(stat, ())
    if not definition.rankable:
        # Percentage leaders need an attempts qualifier the contract does not define.
        raise UnsupportedError("unsupported_leader_stat", "stat_not_rankable", details={"stat": stat})
    if team_id is not None and team_id not in game.team_ids:
        raise NotFoundError("no_record", "team_not_in_game", details={"teamIds": [team_id], "gameId": game.game_id})
    boxscore = _boxscore(game)
    team_leaders: list[tuple[PlayerRef, TeamRef, StatValue]] = []
    any_players = False
    for team, side in _sides(boxscore, game):
        if team_id is not None and team.team_id != team_id:
            continue
        rows = []
        for player in side.get("players") or []:
            person_id = int_or_none(player.get("personId")) if isinstance(player, dict) else None
            ref = _player_ref(player, person_id) if person_id else None
            if ref is None or not _played(player):
                continue
            rows.append((ref, stat_value(player.get("statistics"), definition)))
        any_players = any_players or bool(rows)
        if any(value.value is None for _, value in rows):
            raise NotFoundError("no_record", "stat_not_recorded", details={"gameId": game.game_id, "stats": [stat]})
        if rows:
            best = max(value.value for _, value in rows)
            team_leaders.extend((ref, team, value) for ref, value in rows if value.value == best)
    if not any_players:
        raise NotFoundError("no_record", "player_stats_not_recorded", details={"gameId": game.game_id})
    team_leaders.sort(key=lambda row: -row[2].value)
    leaders = []
    for index, (ref, team, value) in enumerate(team_leaders[:MAX_LEADERS]):
        previous = leaders[-1] if leaders else None
        tied = previous is not None and previous.value.value == value.value
        leaders.append(LeaderRow(rank=previous.rank if tied else index + 1, player=ref, team=team, value=value))
    return _result(game, "leaders", stat, leaders=leaders)

