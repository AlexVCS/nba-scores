"""Game search and single-game resolution, backed by the cached ScoreboardV3.

Every resolved game comes from the scoreboard of its Eastern date, so a game
found another way (a player's game log, a game ID, a playoff series) is
verified there before any statistic is read.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import logging
import re
from typing import Sequence

from pydantic import ValidationError

from server.ask import links
from server.ask.models.common import DateRange, PlayoffRound, TeamRef
from server.ask.models.response import FinalScore, GameContext, GameDay, GameResultItem, GamesResult, ScoreboardGame
from server.ask.resolvers import data
from server.ask.resolvers.errors import AmbiguousError, ClarificationError, NotFoundError, UnavailableError
from server.ask.resolvers.output import ResolverOutput, stats_source
from server.ask.resolvers.spoiler_policy import conditional_playoff_game
from server.ask.spoilers import game_spoilers, guard
from server.services.playoffs import infer_round_from_game_id
from server.utils.boxscore_availability import is_boxscore_available_metadata, is_valid_nba_game_id
from server.utils.season import nba_today

logger = logging.getLogger(__name__)

MAX_SEARCH_DAYS = 7
MAX_TEAMS = 2
REGULATION_PERIODS = 4
# The first BAA game was played on November 1, 1946.
FIRST_RECORDED_DATE = dt.date(1946, 11, 1)
MAX_RESPONSE_LINKS = 6

SEASON_TYPES = {
    "1": "preseason",
    "2": "regular_season",
    "3": "all_star",
    "4": "playoffs",
    "5": "play_in",
    "6": "nba_cup_final",
}
ROUND_CODES: dict[int, PlayoffRound] = {
    1: "first_round",
    2: "conference_semifinals",
    3: "conference_finals",
    4: "finals",
}


def int_or_none(value) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def team_ref(team) -> TeamRef | None:
    """A TeamRef from a scoreboard, boxscore or playoffs team object.

    Names are as the dated record reports them (historical names included).
    """
    if not isinstance(team, dict):
        return None
    team_id = int_or_none(team.get("teamId", team.get("id")))
    tricode = str(team.get("teamTricode") or team.get("tricode") or "").strip()
    parts = (str(team.get("teamCity") or "").strip(), str(team.get("teamName") or "").strip())
    name = " ".join(filter(None, parts)) if parts[1] else str(team.get("name") or "").strip()
    try:
        return TeamRef(team_id=team_id, tricode=tricode, name=name or tricode)
    except ValidationError:
        return None


def validate_team_ids(team_ids: Sequence[int]) -> tuple[int, ...]:
    ids: list[int] = []
    for team_id in team_ids:
        if isinstance(team_id, bool) or not isinstance(team_id, int) or team_id <= 0:
            raise ValueError(f"Invalid team ID {team_id!r}")
        if team_id not in ids:
            ids.append(team_id)
    if len(ids) > MAX_TEAMS:
        raise ValueError(f"At most {MAX_TEAMS} teams are allowed")
    return tuple(ids)


def season_for_game_id(game_id: str) -> str:
    year = int(game_id[3:5])
    start = year + (1900 if year >= 46 else 2000)
    return f"{start}-{(start + 1) % 100:02d}"


@dataclasses.dataclass(frozen=True)
class ResolvedGame:
    """One scoreboard game plus what resolution learned about it."""

    date: dt.date
    game: dict  # ScoreboardV3 game with ``boxscoreAvailable`` added
    home: TeamRef
    away: TeamRef
    round: PlayoffRound | None = None
    game_number: int | None = None
    # True when the teams were found from results (e.g. "Game 3 of the Finals")
    # rather than named or scheduled; they reveal advancement.
    participants_inferred: bool = False
    named_team_ids: tuple[int, ...] = ()

    @property
    def game_id(self) -> str:
        return self.game["gameId"]

    @property
    def status(self) -> int | None:
        status = int_or_none(self.game.get("gameStatus"))
        return status if status in (1, 2, 3) else None

    @property
    def settled(self) -> bool:
        return self.status == 3

    @property
    def team_ids(self) -> tuple[int, int]:
        return (self.home.team_id, self.away.team_id)


def _check_day(day: dt.date) -> None:
    if day < FIRST_RECORDED_DATE:
        raise NotFoundError("no_record", "before_records", "No NBA or BAA games were played before November 1, 1946")


def _playoff_details(game_id: str, game: dict) -> tuple[PlayoffRound | None, int | None]:
    # Only trust ID round codes when the scoreboard also numbers the game:
    # older playoff IDs do not encode rounds reliably.
    match = re.fullmatch(r"Game (\d)", str(game.get("seriesGameNumber") or "").strip())
    if SEASON_TYPES.get(game_id[2]) != "playoffs" or not match:
        return None, None
    number = int(match[1])
    return ROUND_CODES.get(infer_round_from_game_id(game_id) or 0), number if 1 <= number <= 7 else None


def _day_games(day: dt.date) -> list[ResolvedGame]:
    board = data.scoreboard(day)
    games = []
    for raw in board.get("games") or []:
        game_id = str(raw.get("gameId") or "")
        home, away = team_ref(raw.get("homeTeam")), team_ref(raw.get("awayTeam"))
        if not is_valid_nba_game_id(game_id) or home is None or away is None:
            logger.info("Skipping unusable scoreboard game %r on %s", game_id, day)
            continue
        game = {**raw, "boxscoreAvailable": is_boxscore_available_metadata(game_id, int_or_none(raw.get("gameStatus")))}
        round_, number = _playoff_details(game_id, game)
        games.append(ResolvedGame(day, game, home, away, round_, number, game_id[2] in ("4", "5")))
    return games


def game_result_item(game: ResolvedGame) -> GameResultItem:
    try:
        payload = ScoreboardGame.model_validate(game.game)
    except ValidationError as error:
        raise UnavailableError("upstream_bad_response", f"Scoreboard game {game.game_id} is malformed: {error}") from error
    # Published Games 5-7 and any team-filtered postseason appearance can
    # disclose series length or advancement before the score is shown.
    conditional = conditional_playoff_game(game.game_id, game.game_number, bool(game.game.get("ifNecessary")))
    protected = conditional or (game.game_id[2] in ("4", "5") and bool(game.named_team_ids))
    item_links = [links.boxscore_link(game.game_id, game.date)] if game.game["boxscoreAvailable"] else []
    if protected:
        item_links = [link.model_copy(update={"spoiler": True}) for link in item_links]
    return GameResultItem(date=game.date, game=payload, spoilers=game_spoilers(game.status), links=item_links, spoiler=protected)


def search_games(dates: DateRange, team_ids: Sequence[int] = (),
                 home_team_ids: Sequence[int] = ()) -> ResolverOutput[GamesResult]:
    """Games on one date or up to seven consecutive days (``DateRange`` enforces
    the limit), optionally only those in which every listed team played, and only
    those hosted by one of ``home_team_ids`` (a venue filter, ADR 0011).

    One day's scoreboard failing makes the whole search ``unavailable`` rather
    than a silently partial answer.
    """
    days = (dates.end - dates.start).days + 1
    if days > MAX_SEARCH_DAYS:  # DateRange already rejects this; kept for direct callers.
        raise ClarificationError("date", "range_too_long", "range_too_long")
    _check_day(dates.end)
    wanted = set(validate_team_ids(team_ids))
    hosts = set(validate_team_ids(home_team_ids))
    game_days: list[GameDay] = []
    found: list[ResolvedGame] = []
    for offset in range(days):
        day = dates.start + dt.timedelta(days=offset)
        if day < FIRST_RECORDED_DATE:
            continue
        matches = [dataclasses.replace(game, named_team_ids=tuple(wanted)) for game in _day_games(day)
                   if wanted <= set(game.team_ids) and (not hosts or game.home.team_id in hosts)]
        if matches:
            found.extend(matches)
            game_days.append(GameDay(date=day, games=[game_result_item(game) for game in matches]))
    if not found:
        raise NotFoundError(
            "no_games",
            "no_matching_games",
            details={"start": dates.start.isoformat(), "end": dates.end.isoformat(), "teamIds": sorted(wanted),
                     **({"homeTeamIds": sorted(hosts)} if hosts else {})},
        )
    teams = []
    for team_id in team_ids:
        ref = next(team for game in found for team in (game.home, game.away) if team.team_id == team_id)
        teams.append(ref)
    protected = any(item.spoiler for day in game_days for item in day.games)
    result = GamesResult(
        dates=dates, teams=teams, days=game_days,
        total_games=guard(len(found), spoiler=protected),
        hidden_note="Some game listings may reveal a result. Show results to see them." if protected else None,
    )
    day_links = tuple(
        links.scores_link(day.date).model_copy(update={"spoiler": all(item.spoiler for item in day.games)})
        for day in game_days[:MAX_RESPONSE_LINKS]
    )
    return ResolverOutput(result, day_links, (stats_source(all(game.settled for game in found)),))


def find_game_on_date(day: dt.date, team_ids: Sequence[int] = ()) -> ResolvedGame:
    """The unique game on ``day`` involving every listed team (zero, one or two)."""
    _check_day(day)
    wanted = set(validate_team_ids(team_ids))
    games = [game for game in _day_games(day) if wanted <= set(game.team_ids)]
    if not games:
        raise NotFoundError("no_games", "no_matching_games", details={"date": day.isoformat(), "teamIds": sorted(wanted)})
    if len(games) > 1:
        # Matchups on a scheduled date are not spoilers.
        raise AmbiguousError(
            "teams",
            "several_games",
            options=[{"game_id": g.game_id, "date": day.isoformat(), "home": g.home, "away": g.away} for g in games],
        )
    return games[0]


def get_scoreboard_game(game_id: str, day: dt.date) -> ResolvedGame:
    """The game ``game_id`` as listed on the scoreboard for ``day``."""
    if not is_valid_nba_game_id(game_id):
        raise ValueError(f"Invalid game ID {game_id!r}")
    _check_day(day)
    for game in _day_games(day):
        if game.game_id == game_id:
            return game
    raise NotFoundError("no_record", "game_not_on_scoreboard", details={"gameId": game_id, "date": day.isoformat()})


def get_game(game_id: str, day: dt.date | None = None) -> ResolvedGame:
    """A game by ID; without a date, its date comes from the cached game summary."""
    if not is_valid_nba_game_id(game_id):
        raise ValueError(f"Invalid game ID {game_id!r}")
    day = day or data.game_date(game_id)
    if day is None:
        raise NotFoundError("no_record", "game_date_not_recorded", details={"gameId": game_id})
    return get_scoreboard_game(game_id, day)


def find_player_game(player_id: int, day: dt.date) -> tuple[ResolvedGame, TeamRef]:
    """The unique game ``player_id`` played on exactly ``day``, and his team in it.

    Uses the player's game log for that date, then verifies the game and the
    recorded team against the date's scoreboard. The team comes only from that
    dated record, never from a current roster. No game that day is
    ``player_did_not_play``; it is never a reason to try another player.
    """
    if isinstance(player_id, bool) or not isinstance(player_id, int) or player_id <= 0:
        raise ValueError(f"Invalid player ID {player_id!r}")
    _check_day(day)
    rows = data.player_games_on(player_id, day)
    game_ids = sorted({row[0] for row in rows})
    if not game_ids:
        today = nba_today()
        if day in (today, today - dt.timedelta(days=1)) and _day_games(day):
            # LeagueGameFinder can lag games still on the recent scoreboard.
            # Without a dated player record, none of those games is known to
            # be this player's; avoid claiming they did not play.
            raise NotFoundError("no_record", "recent_player_record_unverified",
                                details={"playerId": player_id, "date": day.isoformat()})
        raise NotFoundError(
            "player_did_not_play", "no_player_game_on_date", details={"playerId": player_id, "date": day.isoformat()}
        )
    if len(game_ids) > 1:
        raise AmbiguousError("game_number", "several_player_games", options=[{"game_id": game_id} for game_id in game_ids])
    game = get_scoreboard_game(game_ids[0], day)
    recorded = {row[1] for row in rows}
    teams = [team for team in (game.home, game.away) if team.team_id in recorded]
    if len(teams) != 1:
        raise NotFoundError(
            "no_record", "player_team_not_in_game", details={"gameId": game.game_id, "teamIds": sorted(recorded)}
        )
    return game, teams[0]


def game_context(game: ResolvedGame) -> GameContext:
    final = None
    if game.status == 3:
        home_score = int_or_none((game.game.get("homeTeam") or {}).get("score"))
        away_score = int_or_none((game.game.get("awayTeam") or {}).get("score"))
        if home_score is not None and away_score is not None:
            period = int_or_none(game.game.get("period")) or REGULATION_PERIODS
            final = FinalScore(away=away_score, home=home_score, periods=max(period, REGULATION_PERIODS))
    return GameContext(
        game_id=game.game_id,
        date=game.date,
        away=guard(game.away, game.participants_inferred and game.away.team_id not in game.named_team_ids),
        home=guard(game.home, game.participants_inferred and game.home.team_id not in game.named_team_ids),
        season=season_for_game_id(game.game_id),
        season_type=SEASON_TYPES.get(game.game_id[2], "regular_season"),
        round=game.round,
        game_number=game.game_number,
        final_score=guard(final),
    )
