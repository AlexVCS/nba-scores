import time
import logging
import threading
from datetime import date, datetime

from server.services import nba_stats_client
from ..utils.season import get_nba_season


logger = logging.getLogger(__name__)

_cache: dict[str, dict] = {}
# Structure: { "2025-26": { "fetched_at": float, "game_dates": set[str] } }
_schedule_failure_until: dict[str, float] = {}
# Per-season locks so concurrent cold-cache callers trigger a single upstream fetch.
_season_locks: dict[str, threading.Lock] = {}
_season_locks_guard = threading.Lock()

CACHE_TTL_SECONDS = 6 * 3600  # 6 hours for the raw season blob
SCHEDULE_FAILURE_COOLDOWN_SECONDS = 60


class ScheduleLookupCooldownError(Exception):
    """Raised when an optional schedule lookup is cooling down after a failure."""


def _is_cache_valid(season: str) -> bool:
    if season not in _cache:
        return False
    age = time.time() - _cache[season]["fetched_at"]
    return age < CACHE_TTL_SECONDS


def _get_season_lock(season: str) -> threading.Lock:
    with _season_locks_guard:
        lock = _season_locks.get(season)
        if lock is None:
            lock = threading.Lock()
            _season_locks[season] = lock
        return lock


def _get_cached_dates(season: str, allow_completed_fallback: bool) -> set[str] | None:
    entry = _cache.get(season)
    if entry is None or not _is_cache_valid(season):
        return None
    if allow_completed_fallback or entry.get("is_schedule", False):
        return entry["game_dates"]
    return None


def _parse_schedule_v2(
    season: str,
    *,
    timeout: float | None = None,
    retries: int | None = None,
) -> set[str]:
    """
    Primary: Use ScheduleLeagueV2 to get all game dates for a season.
    Returns a set of date strings like {"2025-10-21", "2025-10-22", ...}.
    """
    if timeout is None and retries is None:
        schedule = nba_stats_client.fetch_schedule_league_v2(season)
    else:
        schedule = nba_stats_client.fetch_schedule_league_v2(
            season,
            timeout=timeout,
            retries=retries,
        )
    frames = schedule.get_data_frames()

    # ScheduleLeagueV2 returns a frame with a date column.
    # The exact column name can vary; common names:
    # "GAME_DATE", "gameDateTimeEst", etc.
    # Inspect with: print(frames[0].columns.tolist())
    df = frames[0]

    # Identify the date column (defensive)
    date_col = None
    for candidate in ["GAME_DATE", "gameDateEst", "gameDateTimeEst", "gameDate"]:
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
        value = str(raw)
        if "/" in value:
            parsed = datetime.strptime(value.split(" ")[0], "%m/%d/%Y").date()
        else:
            parsed = date.fromisoformat(value[:10])
        dates.add(parsed.isoformat())

    return dates


def _parse_game_log_fallback(season: str) -> set[str]:
    """
    Fallback: Use LeagueGameLog (only completed games).
    """
    log = nba_stats_client.fetch_league_game_log(
        season=season,
        season_type_all_star="Regular Season",
    )
    df = log.get_data_frames()[0]

    dates: set[str] = set()
    for raw in df["GAME_DATE"].dropna().unique():
        parsed = str(raw)[:10]
        dates.add(parsed)

    return dates


def get_season_game_dates(
    season: str,
    *,
    allow_completed_fallback: bool = True,
    optional_lookup: bool = False,
) -> set[str]:
    """
    Return all game dates (as 'YYYY-MM-DD' strings) for an NBA season.
    Uses in-memory cache; fetches from NBA API on miss. Concurrent callers
    for the same season share a single upstream fetch (per-season lock).
    """
    cached = _get_cached_dates(season, allow_completed_fallback)
    if cached is not None:
        return cached

    lock = _get_season_lock(season)
    # Optional homepage enrichment must not wait behind a long regular lookup.
    if not lock.acquire(blocking=not optional_lookup):
        raise ScheduleLookupCooldownError(f"Schedule lookup for {season} is already in progress")
    try:
        # Double-checked: another thread may have populated the cache while
        # we were waiting for the lock.
        cached = _get_cached_dates(season, allow_completed_fallback)
        if cached is not None:
            return cached
        return _fetch_season_game_dates(
            season,
            allow_completed_fallback=allow_completed_fallback,
            optional_lookup=optional_lookup,
        )
    finally:
        lock.release()


def _fetch_season_game_dates(
    season: str,
    *,
    allow_completed_fallback: bool,
    optional_lookup: bool,
) -> set[str]:
    """Fetch a season's game dates upstream and store them in the cache.
    Caller must hold the season lock."""
    if optional_lookup and time.monotonic() < _schedule_failure_until.get(season, 0):
        raise ScheduleLookupCooldownError(
            f"Schedule lookup for {season} is temporarily cooling down"
        )

    is_schedule = True
    try:
        game_dates = _parse_schedule_v2(
            season,
            timeout=2 if optional_lookup else None,
            retries=0 if optional_lookup else None,
        )
        _schedule_failure_until.pop(season, None)
        logger.info(
            "Fetched schedule via ScheduleLeagueV2 for %s: %d dates",
            season,
            len(game_dates),
        )
    except Exception as e:
        if not allow_completed_fallback:
            if optional_lookup:
                _schedule_failure_until[season] = (
                    time.monotonic() + SCHEDULE_FAILURE_COOLDOWN_SECONDS
                )
            raise
        logger.warning(
            "ScheduleLeagueV2 failed for %s (%s), falling back to "
            "LeagueGameLog",
            season,
            e,
        )
        game_dates = _parse_game_log_fallback(season)
        is_schedule = False

    _cache[season] = {
        "fetched_at": time.time(),
        "game_dates": game_dates,
        "is_schedule": is_schedule,
    }
    return game_dates


def get_game_days_in_month(year: int, month: int) -> list[str]:
    """
    Return a sorted list of dates (YYYY-MM-DD) that have ≥1 NBA game
    in the given year/month.
    """

    season = get_nba_season(year, month)
    all_dates = get_season_game_dates(season)

    prefix = f"{year}-{month:02d}"
    matching = sorted(d for d in all_dates if d.startswith(prefix))
    return matching


def get_recent_game_days(before: date, months: int = 12) -> list[str]:
    """
    Return game days (YYYY-MM-DD, newest first) strictly before `before`,
    within the `months` calendar months ending with `before`'s month.

    Best-effort across seasons: if one season's lookup fails but another
    succeeds, returns the dates available. Re-raises if every lookup fails.
    """
    if months < 1:
        raise ValueError("months must be >= 1")

    month_index = before.year * 12 + (before.month - 1) - (months - 1)
    window_start = date(month_index // 12, month_index % 12 + 1, 1)

    seasons: list[str] = []
    for offset in range(months):
        idx = month_index + offset
        season = get_nba_season(idx // 12, idx % 12 + 1)
        if season not in seasons:
            seasons.append(season)

    start_iso = window_start.isoformat()
    before_iso = before.isoformat()
    collected: set[str] = set()
    first_error: Exception | None = None
    succeeded = False
    for season in seasons:
        try:
            season_dates = get_season_game_dates(season)
        except Exception as error:
            logger.warning("Recent game days: lookup failed for %s: %s", season, error)
            if first_error is None:
                first_error = error
            continue
        succeeded = True
        collected.update(d for d in season_dates if start_iso <= d < before_iso)

    if not succeeded and first_error is not None:
        raise first_error
    return sorted(collected, reverse=True)


def get_next_game_date(after: date) -> str | None:
    """Find the next published game day, including next season in the off-season."""
    season = get_nba_season(after.year, after.month)
    start_year = int(season[:4])
    first_error: Exception | None = None
    for year in (start_year, start_year + 1):
        season = f"{year}-{str(year + 1)[-2:]}"
        try:
            game_dates = get_season_game_dates(
                season,
                allow_completed_fallback=False,
                optional_lookup=True,
            )
        except ScheduleLookupCooldownError as error:
            if first_error is None:
                first_error = error
            continue
        except Exception as error:
            logger.warning("Schedule lookup failed for %s: %s", season, error)
            if first_error is None:
                first_error = error
            continue
        future_dates = sorted(
            day for day in game_dates if day > after.isoformat()
        )
        if future_dates:
            return future_dates[0]
    if first_error is not None:
        raise first_error
    return None
