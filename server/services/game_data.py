"""Cached boxscore and summary retrieval shared by routes, game details and game context.

Each source has its own per-process cache keyed by validated game ID. Lifetimes
are chosen at insertion from authoritative status/date metadata, reads never
extend them, and failed or unusable responses are never cached.
"""

import copy
import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

import pandas as pd

from server.services import nba_stats_client
from server.utils.boxscore_availability import is_valid_nba_game_id
from server.utils.season import NBA_TIMEZONE, nba_now
from server.utils.stat_events import stat_events
from server.utils.ttl_cache import TTLCache

logger = logging.getLogger(__name__)

ACTIVE_TTL_SECONDS = 15
RECENT_FINAL_TTL_SECONDS = 15 * 60
SETTLED_TTL_SECONDS = 24 * 3600
UNKNOWN_TTL_SECONDS = 15
RECENT_FINAL_WINDOW = timedelta(hours=72)

# A boxscore holds roughly 40-100 KB in memory and a summary far less, so 256
# entries of each stays within a few tens of megabytes per process.
BOXSCORE_CACHE_MAX_ENTRIES = 256
SUMMARY_V3_CACHE_MAX_ENTRIES = 256
SUMMARY_V2_CACHE_MAX_ENTRIES = 256

V2_REQUIRED_COLUMNS = {
    "game_summary": {"GAME_ID", "GAME_STATUS_ID", "GAME_DATE_EST", "HOME_TEAM_ID", "VISITOR_TEAM_ID", "LIVE_PERIOD"},
    "line_score": {"TEAM_ID", "TEAM_ABBREVIATION"},
}

# The metadata lookup that sets a boxscore's lifetime runs before the boxscore
# fetch, so it uses a short, single-attempt policy.
LIFETIME_LOOKUP_TIMEOUT_SECONDS = 2

REGULATION_PERIODS = 4


@dataclass(frozen=True)
class GameMetadata:
    status: int | None
    status_text: str
    game_date: str | None
    datetime_utc: datetime | None


@dataclass(frozen=True)
class StatEventInputs:
    # Kept raw: stat_events applies NBA.com's strict and coerced comparisons.
    wh_status: object
    video_available_flag: object
    overtime_periods: int


@dataclass(frozen=True)
class _Boxscore:
    game: dict
    # Summary metadata and stat-link inputs fetched during the refresh that
    # produced this entry.
    metadata: GameMetadata | None
    stat_event_inputs: StatEventInputs | None


# Every reader receives its own deep copy so callers cannot alter shared entries.
_boxscore_cache: TTLCache[str, _Boxscore] = TTLCache(BOXSCORE_CACHE_MAX_ENTRIES, copy=copy.deepcopy)
_summary_v3_cache: TTLCache[str, dict | None] = TTLCache(SUMMARY_V3_CACHE_MAX_ENTRIES, copy=copy.deepcopy)
# Legacy summaries are cached as their game-summary and line-score frames.
_summary_v2_cache: TTLCache[str, dict] = TTLCache(SUMMARY_V2_CACHE_MAX_ENTRIES, copy=copy.deepcopy)


def _number(value) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError, OverflowError):
        return None


def _iso_date(value) -> str | None:
    text = str(value or "").strip()
    try:
        if "/" in text:
            return datetime.strptime(text.split(" ")[0], "%m/%d/%Y").date().isoformat()
        return date.fromisoformat(text[:10]).isoformat()
    except ValueError:
        return None


def _utc_datetime(value) -> datetime | None:
    text = str(value or "").strip()
    # A bare date would parse as midnight, inventing a tipoff time.
    if len(text) <= 10 or text[10] not in "T ":
        return None
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def v3_metadata(game: dict) -> GameMetadata:
    moment = _utc_datetime(game.get("gameTimeUTC"))
    # gameEt is the local Eastern date; gameCode starts with the same YYYYMMDD.
    code_date = str(game.get("gameCode") or "")[:8]
    game_date = _iso_date(game.get("gameEt")) or (
        _iso_date(f"{code_date[:4]}-{code_date[4:6]}-{code_date[6:]}") if code_date.isdigit() else None
    )
    if game_date is None and moment is not None:
        game_date = moment.astimezone(NBA_TIMEZONE).date().isoformat()
    return GameMetadata(_number(game.get("gameStatus")), str(game.get("gameStatusText") or "").strip(), game_date, moment)


def _period(value) -> int:
    # Only whole numbers count: rounding a malformed period could shorten
    # EndRange and drop overtime events from the linked pages.
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    raise ValueError(f"malformed period {value!r}")


def _overtime_periods(game: dict) -> int:
    # ``period`` is the game's latest period, the value NBA.com's period
    # options are built from. Team period rows cover summaries without it. A
    # malformed value in either raises rather than guessing a period count.
    period = game.get("period")
    period = None if period is None else _period(period)
    if period is None or period < 1:
        period = 0
        for side in ("homeTeam", "awayTeam"):
            team = game.get(side)
            rows = [] if team is None else team.get("periods") or []
            if not isinstance(rows, list):
                raise ValueError(f"malformed {side} periods")
            for row in rows:
                period = max(period, _period(row.get("period")))
    return max(period - REGULATION_PERIODS, 0)


def v3_stat_event_inputs(game: dict) -> StatEventInputs:
    """Return a summary's stat-link inputs; raises on a malformed period count."""
    return StatEventInputs(game.get("whStatus"), game.get("videoAvailableFlag"), _overtime_periods(game))


def v2_metadata(frames: dict) -> GameMetadata | None:
    rows = frames["game_summary"]
    if rows.empty:
        return None
    row = rows.iloc[0]
    # GAME_DATE_EST is a date only; there is no tipoff time to report.
    return GameMetadata(
        _number(row.get("GAME_STATUS_ID")),
        str(row.get("GAME_STATUS_TEXT") or "").strip(),
        _iso_date(row.get("GAME_DATE_EST")),
        None,
    )


def metadata_ttl(metadata: GameMetadata | None, now: datetime | None = None) -> float:
    """Pick a lifetime from metadata fetched with the value being cached."""
    if metadata is None or metadata.status not in (1, 2, 3):
        return UNKNOWN_TTL_SECONDS
    if metadata.status != 3:
        return ACTIVE_TTL_SECONDS

    # Completed games need a precise tipoff; a date alone is not enough.
    if metadata.datetime_utc is None:
        return UNKNOWN_TTL_SECONDS
    now = now or nba_now()
    if metadata.datetime_utc > now:
        # A final game whose tipoff is still ahead is inconsistent metadata.
        return UNKNOWN_TTL_SECONDS
    age = now - metadata.datetime_utc
    return RECENT_FINAL_TTL_SECONDS if age < RECENT_FINAL_WINDOW else SETTLED_TTL_SECONDS


def _has_teams(game: dict) -> bool:
    return all(
        isinstance(game.get(side), dict) and _number(game[side].get("teamId")) is not None
        for side in ("homeTeam", "awayTeam")
    )


def _load_summary_v3(game_id: str, optional: bool) -> dict | None:
    if optional:
        summary = nba_stats_client.fetch_boxscore_summary_v3(
            game_id, timeout=LIFETIME_LOOKUP_TIMEOUT_SECONDS, retries=0
        )
    else:
        summary = nba_stats_client.fetch_boxscore_summary_v3(game_id)
    data = summary.get_dict()
    game = data.get("boxScoreSummary") if isinstance(data, dict) else None
    if not isinstance(game, dict) or game.get("gameId") != game_id or not _has_teams(game):
        # Games outside V3 coverage have no usable summary; callers fall back.
        return None
    return game


def _summary_v3_ttl(game: dict | None) -> float:
    return 0 if game is None else metadata_ttl(v3_metadata(game))


def get_summary_v3(
    game_id: str, *, optional: bool = False, refresh: bool = False, wait_timeout: float | None = None
) -> dict | None:
    """Return a caller-owned BoxScoreSummaryV3 game, or None without a usable one.

    ``optional`` lookups use a short single-attempt policy; a strict caller
    joined to a failed optional load retries with its own policy. ``refresh``
    skips cached entries but still joins an in-flight fetch, waiting at most
    ``wait_timeout`` seconds for it.
    """
    if not is_valid_nba_game_id(game_id):
        return _load_summary_v3(game_id, optional)
    return _summary_v3_cache.get_or_load(
        game_id,
        lambda: _load_summary_v3(game_id, optional),
        _summary_v3_ttl,
        tag=optional,
        retry_after=lambda flight_optional: flight_optional and not optional,
        refresh=refresh,
        wait_timeout=wait_timeout,
    )


def _bad_v2_response(problem: str) -> nba_stats_client.UpstreamBadResponseError:
    return nba_stats_client.UpstreamBadResponseError(
        endpoint="BoxScoreSummaryV2",
        error_type="UnexpectedSchema",
        duration_ms=0,
        message=f"BoxScoreSummaryV2 {problem}",
    )


def _load_summary_v2(game_id: str) -> dict:
    summary = nba_stats_client.fetch_boxscore_summary(game_id)
    frames = {
        "game_summary": summary.game_summary.get_data_frame(),
        "line_score": summary.line_score.get_data_frame(),
    }
    if not all(isinstance(frame, pd.DataFrame) for frame in frames.values()):
        raise _bad_v2_response("is missing game summary or line score data")
    # Empty frames are legitimate sparse history; populated ones must carry
    # every column the summary view and game details read.
    for name, columns in V2_REQUIRED_COLUMNS.items():
        missing = columns - set(frames[name].columns)
        if missing and not frames[name].empty:
            raise _bad_v2_response(f"{name} is missing {sorted(missing)}")
    rows = frames["game_summary"]
    if not rows.empty and str(rows.iloc[0]["GAME_ID"]) != game_id:
        raise _bad_v2_response("game_summary is for another game")
    return frames


def _summary_v2_ttl(frames: dict) -> float:
    metadata = v2_metadata(frames)
    # A summary without a game row is returned to its callers but not retained.
    return 0 if metadata is None else metadata_ttl(metadata)


def get_summary_v2(game_id: str) -> dict:
    """Return caller-owned BoxScoreSummaryV2 ``game_summary`` and ``line_score`` frames."""
    if not is_valid_nba_game_id(game_id):
        return _load_summary_v2(game_id)
    return _summary_v2_cache.get_or_load(game_id, lambda: _load_summary_v2(game_id), _summary_v2_ttl)


def _fetch_boxscore(game_id: str) -> dict:
    data = nba_stats_client.fetch_boxscore_traditional(game_id)
    game = data.get("boxScoreTraditional")
    # Player lists may be empty for sparse history, but the game and teams must match.
    if not isinstance(game, dict) or game.get("gameId") != game_id or not _has_teams(game):
        raise ValueError("BoxscoreTraditionalV3 returned no usable game data")
    return game


def _refreshed_summary(game_id: str) -> dict | None:
    # Only metadata fetched for this refresh, or joined in flight, may extend a
    # boxscore's lifetime: a cached summary can predate the final buzzer. A
    # failed lookup only shortens the lifetime; it never fails the boxscore.
    # A joined fetch may run under the full retry policy, so wait no longer than
    # this lookup's own budget; that fetch still fills the summary cache.
    try:
        game = get_summary_v3(game_id, optional=True, refresh=True, wait_timeout=LIFETIME_LOOKUP_TIMEOUT_SECONDS)
    except Exception as exc:
        logger.info("Boxscore lifetime metadata unavailable for %s: %s", game_id, exc)
        return None
    return game


def _load_boxscore(game_id: str) -> _Boxscore:
    # Fetch metadata first so a game reported final is never paired with a
    # boxscore captured before it ended. Stat-link inputs come from the same
    # summary, so they share the entry's lifetime.
    summary = _refreshed_summary(game_id)
    if not summary:
        return _Boxscore(_fetch_boxscore(game_id), None, None)
    return _Boxscore(_fetch_boxscore(game_id), v3_metadata(summary), _stat_event_inputs(game_id, summary))


def _stat_event_inputs(game_id: str, summary: dict) -> StatEventInputs | None:
    # Stat links are optional: malformed inputs leave them null, never the boxscore.
    try:
        return v3_stat_event_inputs(summary)
    except Exception as exc:
        logger.info("Stat event inputs unusable for %s: %s", game_id, exc)
        return None


def _boxscore_entry(game_id: str) -> _Boxscore:
    if not is_valid_nba_game_id(game_id):
        return _Boxscore(_fetch_boxscore(game_id), None, None)
    return _boxscore_cache.get_or_load(
        game_id,
        lambda: _load_boxscore(game_id),
        lambda entry: metadata_ttl(entry.metadata),
    )


def get_boxscore(game_id: str) -> dict:
    """Return a caller-owned BoxScoreTraditionalV3 game."""
    return _boxscore_entry(game_id).game


def get_boxscore_with_stat_events(game_id: str) -> tuple[dict, dict | None]:
    """Return a caller-owned boxscore and its NBA.com stat-link parameters.

    Both come from one cached entry, so this never makes a summary request of
    its own. Stat events are None without a usable summary from that refresh.
    """
    entry = _boxscore_entry(game_id)
    inputs = entry.stat_event_inputs
    if inputs is None:
        return entry.game, None
    return entry.game, stat_events(game_id, inputs.wh_status, inputs.video_available_flag, inputs.overtime_periods)


def _summary_metadata(game_id: str) -> GameMetadata:
    try:
        game = get_summary_v3(game_id)
    except nba_stats_client.UpstreamError as exc:
        logger.info("BoxScoreSummaryV3 context fallback to V2 for %s: %s", game_id, exc)
        game = None
    if game is not None:
        return v3_metadata(game)
    return v2_metadata(get_summary_v2(game_id)) or GameMetadata(None, "", None, None)


def get_game_context(game_id: str) -> dict:
    """Return internal status, date and boxscore membership for a game.

    Membership lists every player in the cached boxscore entry the boxscore
    route serves, including DNP entries. It does not establish participation
    or a complete inactive roster. Metadata comes straight from the cached
    summaries, without period-score repair.
    """
    if not is_valid_nba_game_id(game_id):
        raise ValueError("Invalid game ID")
    boxscore = get_boxscore(game_id)
    metadata = _summary_metadata(game_id)

    def team(side):
        source = boxscore.get(side) or {}
        team_id = _number(source.get("teamId"))
        player_ids = (_number(player.get("personId")) for player in source.get("players") or [] if isinstance(player, dict))
        return {
            "teamId": team_id if team_id is not None else _number(boxscore.get(f"{side}Id")),
            "playerIds": list(dict.fromkeys(pid for pid in player_ids if pid is not None)),
        }

    return {
        "gameId": game_id,
        "gameStatus": metadata.status,
        "gameStatusText": metadata.status_text,
        "gameDate": metadata.game_date,
        "gameDatetimeUtc": metadata.datetime_utc,
        "homeTeam": team("homeTeam"),
        "awayTeam": team("awayTeam"),
    }
