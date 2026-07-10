import logging
import time
from typing import Callable, TypeVar

from nba_api.stats.endpoints import (
    LeagueGameLog,
    ScheduleLeagueV2,
    boxscoresummaryv2,
    boxscoresummaryv3,
    boxscoretraditionalv3,
    leaguegamefinder,
    scoreboardv2,
    scoreboardv3,
)
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import RequestException, Timeout

logger = logging.getLogger(__name__)

PROVIDER = "stats.nba.com"
NBA_API_TIMEOUT_SECONDS = 10
NBA_API_RETRIES = 2
NBA_API_BACKOFF_SECONDS = 0.75

NBA_STATS_HEADERS = {
    "Host": "stats.nba.com",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://stats.nba.com/",
    "Origin": "https://www.nba.com",
    "Pragma": "no-cache",
    "Cache-Control": "no-cache",
    "x-nba-stats-origin": "stats",
    "x-nba-stats-token": "true",
    "Sec-Ch-Ua": '"Chromium";v="140", "Google Chrome";v="140", "Not;A=Brand";v="24"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Fetch-Dest": "empty",
}


class UpstreamError(Exception):
    def __init__(
        self,
        endpoint: str,
        error_type: str,
        duration_ms: int,
        message: str = "",
    ):
        super().__init__(message or error_type)
        self.provider = PROVIDER
        self.endpoint = endpoint
        self.error_type = error_type
        self.duration_ms = duration_ms

    def public_detail(self):
        return {
            "provider": self.provider,
            "endpoint": self.endpoint,
            "errorType": self.error_type,
            "durationMs": self.duration_ms,
        }


class UpstreamUnavailableError(UpstreamError):
    pass


class UpstreamBadResponseError(UpstreamError):
    pass


T = TypeVar("T")


def _headers():
    return dict(NBA_STATS_HEADERS)


def _timeout():
    return NBA_API_TIMEOUT_SECONDS


def _run(endpoint: str, operation: Callable[[], T]) -> T:
    attempts = max(1, NBA_API_RETRIES + 1)
    started = time.monotonic()

    for attempt in range(1, attempts + 1):
        attempt_started = time.monotonic()
        try:
            result = operation()
            duration_ms = int((time.monotonic() - started) * 1000)
            logger.info(
                "nba_stats_success provider=%s endpoint=%s attempt=%s durationMs=%s",
                PROVIDER,
                endpoint,
                attempt,
                duration_ms,
            )
            return result
        except (Timeout, RequestsConnectionError, RequestException) as e:
            duration_ms = int((time.monotonic() - attempt_started) * 1000)
            logger.warning(
                "nba_stats_unavailable provider=%s endpoint=%s attempt=%s "
                "durationMs=%s errorType=%s",
                PROVIDER,
                endpoint,
                attempt,
                duration_ms,
                type(e).__name__,
            )
            if attempt == attempts:
                total_ms = int((time.monotonic() - started) * 1000)
                raise UpstreamUnavailableError(
                    endpoint=endpoint,
                    error_type=type(e).__name__,
                    duration_ms=total_ms,
                    message=str(e),
                ) from e
            time.sleep(NBA_API_BACKOFF_SECONDS * attempt)
        except UpstreamBadResponseError:
            raise
        except Exception as e:
            duration_ms = int((time.monotonic() - started) * 1000)
            logger.exception(
                "nba_stats_bad_response provider=%s endpoint=%s durationMs=%s "
                "errorType=%s",
                PROVIDER,
                endpoint,
                duration_ms,
                type(e).__name__,
            )
            raise UpstreamBadResponseError(
                endpoint=endpoint,
                error_type=type(e).__name__,
                duration_ms=duration_ms,
                message=str(e),
            ) from e

    raise AssertionError("unreachable")


def fetch_scoreboard_v3(game_date: str) -> dict:
    def operation():
        board = scoreboardv3.ScoreboardV3(
            game_date=game_date,
            league_id="00",
            headers=_headers(),
            timeout=_timeout(),
        )
        data = board.get_dict()
        scoreboard = data.get("scoreboard") if isinstance(data, dict) else None
        if not isinstance(scoreboard, dict) or "games" not in scoreboard:
            raise UpstreamBadResponseError(
                endpoint="ScoreboardV3",
                error_type="UnexpectedSchema",
                duration_ms=0,
                message="ScoreboardV3 response missing scoreboard.games",
            )
        return scoreboard

    return _run("ScoreboardV3", operation)


def fetch_scoreboard_v2(game_date: str):
    return _run(
        "ScoreboardV2",
        lambda: scoreboardv2.ScoreboardV2(
            game_date=game_date,
            headers=_headers(),
            timeout=_timeout(),
        ),
    )


def fetch_boxscore_traditional(game_id: str) -> dict:
    def operation():
        box = boxscoretraditionalv3.BoxScoreTraditionalV3(
            game_id=game_id,
            range_type=0,
            start_period=0,
            end_period=10,
            start_range=0,
            end_range=0,
            headers=_headers(),
            timeout=_timeout(),
        )
        data = box.get_dict()
        if not isinstance(data, dict):
            raise UpstreamBadResponseError(
                endpoint="BoxScoreTraditionalV3",
                error_type="UnexpectedSchema",
                duration_ms=0,
                message="BoxScoreTraditionalV3 response is not an object",
            )
        return data

    return _run("BoxScoreTraditionalV3", operation)


def fetch_boxscore_summary(game_id: str):
    return _run(
        "BoxScoreSummaryV2",
        lambda: boxscoresummaryv2.BoxScoreSummaryV2(
            game_id=game_id,
            headers=_headers(),
            timeout=_timeout(),
        ),
    )


def fetch_boxscore_summary_v3(game_id: str):
    return _run(
        "BoxScoreSummaryV3",
        lambda: boxscoresummaryv3.BoxScoreSummaryV3(
            game_id=game_id,
            headers=_headers(),
            timeout=_timeout(),
        ),
    )


def fetch_schedule_league_v2(season: str, league_id: str = "00"):
    return _run(
        "ScheduleLeagueV2",
        lambda: ScheduleLeagueV2(
            season=season,
            league_id=league_id,
            headers=_headers(),
            timeout=_timeout(),
        ),
    )


def fetch_league_game_log(**kwargs):
    return _run(
        "LeagueGameLog",
        lambda: LeagueGameLog(
            **kwargs,
            headers=_headers(),
            timeout=_timeout(),
        ),
    )


def fetch_league_game_finder(**kwargs):
    return _run(
        "LeagueGameFinder",
        lambda: leaguegamefinder.LeagueGameFinder(
            **kwargs,
            headers=_headers(),
            timeout=_timeout(),
        ),
    )
