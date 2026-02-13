import time
import logging
from datetime import date, datetime
from collections import defaultdict

from nba_api.stats.endpoints import ScheduleLeagueV2, LeagueGameLog

logger = logging.getLogger(__name__)

_cache: dict[str, dict] = {}
# Structure: { "2025-26": { "fetched_at": float, "game_dates": set[str] } }

CACHE_TTL_SECONDS = 6 * 3600  # 6 hours for the raw season blob


def _is_cache_valid(season: str) -> bool:
    if season not in _cache:
        return False
    age = time.time() - _cache[season]["fetched_at"]
    return age < CACHE_TTL_SECONDS


def _parse_schedule_v2(season: str) -> set[str]:
    """
    Primary: Use ScheduleLeagueV2 to get all game dates for a season.
    Returns a set of date strings like {"2025-10-21", "2025-10-22", ...}.
    """
    schedule = ScheduleLeagueV2(season=season)
    frames = schedule.get_data_frames()

    # ScheduleLeagueV2 returns a frame with a date column.
    # The exact column name can vary; common names:
    # "GAME_DATE", "gameDateTimeEst", etc.
    # Inspect with: print(frames[0].columns.tolist())
    df = frames[0]

    # Identify the date column (defensive)
    date_col = None
    for candidate in ["GAME_DATE", "gameDateEst", "gameDateTimeEst"]:
        if candidate in df.columns:
            date_col = candidate
            break

    if date_col is None:
        raise ValueError(
            f"Could not find date column. Columns: {df.columns.tolist()}"
        )

    # Normalize to YYYY-MM-DD strings
    dates: set[str] = set()
    for raw in df[date_col].dropna().unique():
        parsed = str(raw)[:10]  # handle datetime or "YYYY-MM-DD" strings
        dates.add(parsed)

    return dates


def _parse_game_log_fallback(season: str) -> set[str]:
    """
    Fallback: Use LeagueGameLog (only completed games).
    """
    log = LeagueGameLog(
        season=season,
        season_type_all_star="Regular Season",
    )
    df = log.get_data_frames()[0]

    dates: set[str] = set()
    for raw in df["GAME_DATE"].dropna().unique():
        parsed = str(raw)[:10]
        dates.add(parsed)

    return dates


def get_season_game_dates(season: str) -> set[str]:
    """
    Return all game dates (as 'YYYY-MM-DD' strings) for an NBA season.
    Uses in-memory cache; fetches from NBA API on miss.
    """
    if _is_cache_valid(season):
        return _cache[season]["game_dates"]

    try:
        game_dates = _parse_schedule_v2(season)
        logger.info(
            "Fetched schedule via ScheduleLeagueV2 for %s: %d dates",
            season,
            len(game_dates),
        )
    except Exception as e:
        logger.warning(
            "ScheduleLeagueV2 failed for %s (%s), falling back to "
            "LeagueGameLog",
            season,
            e,
        )
        game_dates = _parse_game_log_fallback(season)

    _cache[season] = {
        "fetched_at": time.time(),
        "game_dates": game_dates,
    }
    return game_dates


def get_game_days_in_month(year: int, month: int) -> list[str]:
    """
    Return a sorted list of dates (YYYY-MM-DD) that have ≥1 NBA game
    in the given year/month.
    """
    from ..utils.season import get_nba_season

    season = get_nba_season(year, month)
    all_dates = get_season_game_dates(season)

    prefix = f"{year}-{month:02d}"
    matching = sorted(d for d in all_dates if d.startswith(prefix))
    return matching