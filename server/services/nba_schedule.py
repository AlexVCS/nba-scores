import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from types import MappingProxyType
from typing import Mapping

from server.services import nba_stats_client
from ..utils.season import current_nba_season, get_nba_season
from ..utils.ttl_cache import LoadInProgressError, TTLCache


logger = logging.getLogger(__name__)

SOURCE_SCHEDULE = "ScheduleLeagueV2"
SOURCE_GAME_LOG = "LeagueGameLog"

# Lifetimes for (is current or upcoming season, source).
CURRENT_SCHEDULE_TTL_SECONDS = 6 * 3600
CURRENT_GAME_LOG_TTL_SECONDS = 5 * 60
PAST_SCHEDULE_TTL_SECONDS = 7 * 24 * 3600
PAST_GAME_LOG_TTL_SECONDS = 3600
SCHEDULE_CACHE_MAX_ENTRIES = 16
SCHEDULE_FAILURE_COOLDOWN_SECONDS = 60
SCHEDULE_COOLDOWN_MAX_ENTRIES = 16


@dataclass(frozen=True)
class SeasonSchedule:
    """One season's schedule, shared by the calendar, next-game and game-details lookups.

    ``games`` indexes published schedule games by gameId and is empty for the
    completed-games fallback, which only knows dates.
    """

    season: str
    source: str
    game_dates: frozenset[str]
    games: Mapping[str, Mapping] = field(default_factory=lambda: MappingProxyType({}))

    @property
    def is_schedule(self) -> bool:
        return self.source == SOURCE_SCHEDULE


# The ScheduleLeagueV2 payload is several megabytes and takes seconds to fetch,
# so every consumer reads the same entry, keyed by (league ID, season).
_schedule_cache: TTLCache[tuple[str, str], SeasonSchedule] = TTLCache(SCHEDULE_CACHE_MAX_ENTRIES)
# Seasons whose optional lookup recently failed, keyed like the schedule cache.
_schedule_cooldowns: TTLCache[tuple[str, str], bool] = TTLCache(SCHEDULE_COOLDOWN_MAX_ENTRIES)


class ScheduleLookupCooldownError(Exception):
    """Raised when an optional schedule lookup is cooling down after a failure."""


def season_schedule_ttl(schedule: SeasonSchedule, current_season: str | None = None) -> float:
    current_season = current_season or current_nba_season()
    is_past = int(schedule.season[:4]) < int(current_season[:4])
    if schedule.is_schedule:
        return PAST_SCHEDULE_TTL_SECONDS if is_past else CURRENT_SCHEDULE_TTL_SECONDS
    return PAST_GAME_LOG_TTL_SECONDS if is_past else CURRENT_GAME_LOG_TTL_SECONDS


def _normalize_date(value) -> str | None:
    if not value:
        return None
    text = str(value)
    if "/" in text:
        return datetime.strptime(text.split(" ")[0], "%m/%d/%Y").date().isoformat()
    return date.fromisoformat(text[:10]).isoformat()


def _parse_schedule_v2(
    season: str,
    *,
    league_id: str = nba_stats_client.NBA_LEAGUE_ID,
    timeout: float | None = None,
    retries: int | None = None,
) -> SeasonSchedule:
    """
    Primary: Use ScheduleLeagueV2 to get every published game for a season.
    """
    if timeout is None and retries is None:
        schedule = nba_stats_client.fetch_schedule_league_v2(season, league_id=league_id)
    else:
        schedule = nba_stats_client.fetch_schedule_league_v2(
            season,
            league_id=league_id,
            timeout=timeout,
            retries=retries,
        )
    data = schedule.get_dict()
    game_days = (data.get("leagueSchedule") or {}).get("gameDates") if isinstance(data, dict) else None
    if not isinstance(game_days, list):
        raise ValueError("Schedule response missing leagueSchedule.gameDates")

    dates: set[str] = set()
    games: dict[str, Mapping] = {}
    for day in game_days:
        for game in day.get("games") or []:
            game_date = _normalize_date(game.get("gameDateEst") or day.get("gameDate"))
            if game_date:
                dates.add(game_date)
            if game.get("gameId"):
                games[game["gameId"]] = MappingProxyType({**game, "gameDate": day.get("gameDate")})

    return SeasonSchedule(season, SOURCE_SCHEDULE, frozenset(dates), MappingProxyType(games))


def _parse_game_log_fallback(season: str, *, league_id: str = nba_stats_client.NBA_LEAGUE_ID) -> SeasonSchedule:
    """
    Fallback: Use LeagueGameLog (only completed games).
    """
    log = nba_stats_client.fetch_league_game_log(
        season=season,
        season_type_all_star="Regular Season",
        league_id=league_id,
    )
    df = log.get_data_frames()[0]

    dates: set[str] = set()
    for raw in df["GAME_DATE"].dropna().unique():
        parsed = str(raw)[:10]
        dates.add(parsed)

    return SeasonSchedule(season, SOURCE_GAME_LOG, frozenset(dates))


def get_season_schedule(
    season: str,
    *,
    allow_completed_fallback: bool = True,
    optional_lookup: bool = False,
    wait: bool | None = None,
    league_id: str = nba_stats_client.NBA_LEAGUE_ID,
) -> SeasonSchedule:
    """
    Return a season's schedule from the shared cache, fetching on a miss.

    Concurrent callers for the same season share one upstream fetch. Optional
    lookups use a short timeout, cool down after failures and, unless ``wait``
    is set, fail fast instead of waiting behind another caller's fetch.
    Strict callers (``allow_completed_fallback=False``) ignore fallback entries.
    """
    policy = (optional_lookup, allow_completed_fallback)

    def weaker_policy(tag) -> bool:
        # A failed fetch only answers callers whose policy it fully covered.
        other_optional, other_fallback = tag
        return (other_optional and not optional_lookup) or (allow_completed_fallback and not other_fallback)

    try:
        return _schedule_cache.get_or_load(
            (league_id, season),
            lambda: _fetch_season_schedule(
                season,
                allow_completed_fallback=allow_completed_fallback,
                optional_lookup=optional_lookup,
                league_id=league_id,
            ),
            season_schedule_ttl,
            accept=None if allow_completed_fallback else (lambda schedule: schedule.is_schedule),
            # Optional homepage enrichment must not wait behind a long regular lookup.
            wait=not optional_lookup if wait is None else wait,
            tag=policy,
            retry_after=weaker_policy,
        )
    except LoadInProgressError as error:
        raise ScheduleLookupCooldownError(f"Schedule lookup for {season} is already in progress") from error


def get_season_game_dates(
    season: str,
    *,
    allow_completed_fallback: bool = True,
    optional_lookup: bool = False,
) -> frozenset[str]:
    """
    Return all game dates (as 'YYYY-MM-DD' strings) for an NBA season.
    """
    return get_season_schedule(
        season,
        allow_completed_fallback=allow_completed_fallback,
        optional_lookup=optional_lookup,
    ).game_dates


def _fetch_season_schedule(
    season: str,
    *,
    allow_completed_fallback: bool,
    optional_lookup: bool,
    league_id: str = nba_stats_client.NBA_LEAGUE_ID,
) -> SeasonSchedule:
    """Fetch a season's schedule upstream. Runs once per in-flight season."""
    key = (league_id, season)
    if optional_lookup and _schedule_cooldowns.get(key):
        raise ScheduleLookupCooldownError(
            f"Schedule lookup for {season} is temporarily cooling down"
        )

    try:
        schedule = _parse_schedule_v2(
            season,
            league_id=league_id,
            timeout=2 if optional_lookup else None,
            retries=0 if optional_lookup else None,
        )
        _schedule_cooldowns.pop(key)
        logger.info(
            "Fetched schedule via ScheduleLeagueV2 for %s: %d dates",
            season,
            len(schedule.game_dates),
        )
        return schedule
    except Exception as e:
        if not allow_completed_fallback:
            if optional_lookup:
                _schedule_cooldowns.set(key, True, SCHEDULE_FAILURE_COOLDOWN_SECONDS)
            raise
        logger.warning(
            "ScheduleLeagueV2 failed for %s (%s), falling back to "
            "LeagueGameLog",
            season,
            e,
        )
        return _parse_game_log_fallback(season, league_id=league_id)


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
