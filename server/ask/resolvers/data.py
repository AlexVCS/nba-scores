"""Reads from the existing cached services, mapped to resolver outcomes.

Upstream failures become ``UnavailableError``; responses that prove a record
does not exist become ``NotFoundError``. Nothing here fetches directly except
the player game lookup, which has no shared service yet and gets its own
bounded cache.
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime, timedelta

from server.services import game_data, nba_stats_client
from server.services import playoffs as playoffs_service
from server.services import scoreboard as scoreboard_service
from server.ask.resolvers.errors import NotFoundError, UnavailableError
from server.utils.season import nba_today
from server.utils.ttl_cache import TTLCache

logger = logging.getLogger(__name__)

PROVIDER = nba_stats_client.PROVIDER

PLAYER_GAME_CACHE_MAX_ENTRIES = 512
PLAYER_GAME_RECENT_TTL_SECONDS = 5 * 60
PLAYER_GAME_SETTLED_TTL_SECONDS = 24 * 3600
PLAYER_GAME_SETTLED_AFTER = timedelta(days=3)

# stats.nba holds no player game logs before the 1983-84 season (regular season
# or playoffs): LeagueGameFinder is empty for every earlier date, whoever played.
PLAYER_GAME_LOG_FIRST_DATE = date(1983, 10, 28)

# (player ID, YYYY-MM-DD) -> frozenset of (game ID, team ID, player name) rows.
_player_game_cache: TTLCache[tuple[int, str], frozenset[tuple[str, int, str]]] = TTLCache(PLAYER_GAME_CACHE_MAX_ENTRIES)


def _is_upstream_http_error(error: Exception) -> bool:
    # playoffs.fetch_playoff_team_games_df converts upstream outages to a
    # FastAPI HTTPException. Recognize it by shape so this package does not
    # import the web framework.
    return isinstance(getattr(error, "status_code", None), int) and error.status_code >= 500


def scoreboard(day: date) -> dict:
    try:
        return scoreboard_service.get_scoreboard(day.isoformat())
    except nba_stats_client.UpstreamError as error:
        raise UnavailableError.from_upstream(error) from error


def boxscore(game_id: str) -> dict:
    try:
        return game_data.get_boxscore(game_id)
    except nba_stats_client.UpstreamError as error:
        raise UnavailableError.from_upstream(error) from error
    except ValueError as error:
        # The source answered but holds no usable boxscore for this game.
        raise NotFoundError("no_record", "boxscore_not_recorded", str(error), details={"gameId": game_id}) from error


def game_date(game_id: str) -> date | None:
    """A game's Eastern date from its cached summary metadata (for game-ID selectors)."""
    try:
        context = game_data.get_game_context(game_id)
    except nba_stats_client.UpstreamError as error:
        raise UnavailableError.from_upstream(error) from error
    except ValueError as error:
        raise NotFoundError("no_record", "game_not_recorded", str(error), details={"gameId": game_id}) from error
    value = context.get("gameDate")
    return date.fromisoformat(value) if value else None


def playoffs(season: str) -> dict:
    try:
        return playoffs_service.get_playoff_games_and_series(season)
    except nba_stats_client.UpstreamError as error:
        raise UnavailableError.from_upstream(error) from error
    except Exception as error:
        if _is_upstream_http_error(error):
            raise UnavailableError("upstream_unavailable", str(getattr(error, "detail", error))) from error
        raise


def _bad_finder(message: str) -> UnavailableError:
    return UnavailableError(
        "upstream_bad_response",
        f"LeagueGameFinder {message}",
        details={"provider": PROVIDER, "endpoint": "LeagueGameFinder"},
    )


def _finder_date(value) -> date:
    text = str(value or "").strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"unexpected GAME_DATE {text!r}")


def _load_player_games(player_id: int, day: date, end: date | None = None) -> frozenset[tuple[str, int, str]]:
    """One LeagueGameFinder read: the player's games on ``day``, or from ``day`` through ``end``."""
    end = end or day
    requested = day.strftime("%m/%d/%Y")
    try:
        response = nba_stats_client.fetch_league_game_finder(
            player_or_team_abbreviation="P",
            player_id_nullable=str(player_id),
            date_from_nullable=requested,
            date_to_nullable=end.strftime("%m/%d/%Y"),
            league_id_nullable=nba_stats_client.NBA_LEAGUE_ID,
        )
        data = response.get_normalized_dict()
    except nba_stats_client.UpstreamError as error:
        raise UnavailableError.from_upstream(error) from error
    except Exception as error:
        raise _bad_finder(f"response unreadable: {type(error).__name__}") from error

    rows = data.get("LeagueGameFinderResults") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        raise _bad_finder("response has no result rows")
    found = set()
    for row in rows:
        if not isinstance(row, dict):
            raise _bad_finder("row is not an object")
        game_id, row_player, team_id = row.get("GAME_ID"), row.get("PLAYER_ID"), row.get("TEAM_ID")
        if not isinstance(game_id, str) or not re.fullmatch(r"\d{10}", game_id):
            raise _bad_finder("row has an invalid GAME_ID")
        try:
            row_player, team_id = int(row_player), int(team_id)
            row_day = _finder_date(row.get("GAME_DATE"))
        except (TypeError, ValueError) as error:
            raise _bad_finder(f"row is malformed: {error}") from error
        # The finder filters by player and date; keep only exact matches anyway.
        if row_player == player_id and day <= row_day <= end:
            found.add((game_id, team_id, str(row.get("PLAYER_NAME") or "").strip()))
    return frozenset(found)


def player_games_on(player_id: int, day: date) -> frozenset[tuple[str, int, str]]:
    """Return (game ID, team ID, player name) rows for a player's games on exactly ``day``.

    The team is the one recorded for that game, never a current roster.
    """

    def ttl(rows) -> float:
        # Game logs can lag the final buzzer, so recent days and empty answers
        # stay short-lived.
        settled = rows and day < nba_today() - PLAYER_GAME_SETTLED_AFTER
        return PLAYER_GAME_SETTLED_TTL_SECONDS if settled else PLAYER_GAME_RECENT_TTL_SECONDS

    return _player_game_cache.get_or_load((player_id, day.isoformat()), lambda: _load_player_games(player_id, day), ttl)


def player_game_ids_between(player_id: int, start: date, end: date) -> frozenset[str]:
    """IDs of the games a player appeared in from ``start`` through ``end``, in one read.

    Empty before 1983-84 (``PLAYER_GAME_LOG_FIRST_DATE``), whoever played.
    """

    def ttl(rows) -> float:
        settled = rows and end < nba_today() - PLAYER_GAME_SETTLED_AFTER
        return PLAYER_GAME_SETTLED_TTL_SECONDS if settled else PLAYER_GAME_RECENT_TTL_SECONDS

    rows = _player_game_cache.get_or_load(
        (player_id, f"{start.isoformat()}..{end.isoformat()}"), lambda: _load_player_games(player_id, start, end), ttl
    )
    return frozenset(row[0] for row in rows)
