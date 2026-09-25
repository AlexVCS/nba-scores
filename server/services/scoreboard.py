"""Cached ScoreboardV3 lookups with lifetimes chosen from the fetched game statuses."""

import copy
from datetime import date, datetime, time as day_time, timedelta

from server.services import nba_stats_client
from server.utils.season import NBA_TIMEZONE, nba_now
from server.utils.ttl_cache import TTLCache

LIVE_TTL_SECONDS = 15
SCHEDULED_TTL_SECONDS = 60
RECENT_FINAL_TTL_SECONDS = 15 * 60
SETTLED_TTL_SECONDS = 24 * 3600
UNKNOWN_TTL_SECONDS = 15
RECENT_FINAL_WINDOW = timedelta(hours=72)

SCOREBOARD_CACHE_MAX_ENTRIES = 256

_scoreboard_cache: TTLCache[str, dict] = TTLCache(SCOREBOARD_CACHE_MAX_ENTRIES)


def _status(game) -> int | None:
    if not isinstance(game, dict):
        return None
    value = game.get("gameStatus")
    if isinstance(value, bool):
        return None
    try:
        status = int(value)
    except (TypeError, ValueError):
        return None
    return status if status in (1, 2, 3) else None


def scoreboard_ttl(scoreboard: dict, game_date: date, now: datetime | None = None) -> float:
    """Pick a lifetime for a freshly fetched scoreboard."""
    now = now or nba_now()
    games = scoreboard["games"]
    if not games:
        return SCHEDULED_TTL_SECONDS if game_date >= now.astimezone(NBA_TIMEZONE).date() else SETTLED_TTL_SECONDS

    statuses = {_status(game) for game in games}
    if None in statuses:
        return UNKNOWN_TTL_SECONDS
    if 2 in statuses:
        return LIVE_TTL_SECONDS
    if 1 in statuses:
        return SCHEDULED_TTL_SECONDS
    # Every game is final; measure recency from the end of the game day.
    day_end = datetime.combine(game_date + timedelta(days=1), day_time(), NBA_TIMEZONE)
    return RECENT_FINAL_TTL_SECONDS if now - day_end < RECENT_FINAL_WINDOW else SETTLED_TTL_SECONDS


def _load(game_date: str) -> dict:
    scoreboard = nba_stats_client.fetch_scoreboard_v3(game_date)
    if not isinstance(scoreboard.get("games"), list):
        raise nba_stats_client.UpstreamBadResponseError(
            endpoint="ScoreboardV3",
            error_type="UnexpectedSchema",
            duration_ms=0,
            message="ScoreboardV3 games is not a list",
        )
    return scoreboard


def get_scoreboard(game_date: str) -> dict:
    """Return a caller-owned copy of the scoreboard for a YYYY-MM-DD date."""
    parsed = date.fromisoformat(game_date)
    key = parsed.isoformat()
    scoreboard = _scoreboard_cache.get_or_load(
        key,
        lambda: _load(key),
        lambda board: scoreboard_ttl(board, parsed),
    )
    return copy.deepcopy(scoreboard)
