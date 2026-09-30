"""Retryable Basketball-Reference quarter-score fallback under the shared rate limit."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import requests
from fastapi.testclient import TestClient

from server import main
from server.services import basketball_reference, game_summary
from server.tests.cache_helpers import wait_for_waiters
from server.utils.ttl_cache import LoadInProgressError

GAME_ID = "0024600001"
HUS = 1610610035
NYK = 1610612752
BREF_KEY = ("1946-11-01", "HUS")

BREF_LINE_SCORE_HTML = """
<table id="line_score"><tbody>
  <tr><th data-stat="team">NYK</th><td data-stat="1">16</td><td data-stat="2">21</td>
    <td data-stat="3">6</td><td data-stat="4">25</td><td data-stat="T">68</td></tr>
  <tr><th data-stat="team">TRH</th><td data-stat="1">12</td><td data-stat="2">17</td>
    <td data-stat="3">19</td><td data-stat="4">18</td><td data-stat="T">66</td></tr>
</tbody></table>
"""


def v3_summary_without_periods():
    """A final V3 summary whose quarter scores NBA never recorded."""
    game = {
        "gameId": GAME_ID,
        "gameStatus": 3,
        "gameStatusText": "Final",
        "period": 4,
        "gameEt": "1946-11-01T20:00:00",
        "homeTeam": {"teamId": HUS, "teamTricode": "HUS", "teamCity": "Toronto", "teamName": "Huskies", "score": 66, "periods": []},
        "awayTeam": {"teamId": NYK, "teamTricode": "NYK", "teamCity": "New York", "teamName": "Knicks", "score": 68, "periods": []},
    }
    return Mock(get_dict=Mock(return_value={"boxScoreSummary": game}))


@pytest.fixture
def clock(monkeypatch):
    # The limiter and the line-score cache both read time.monotonic.
    now = [1000.0]
    monkeypatch.setattr(basketball_reference.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(basketball_reference, "_next_start", 0.0)
    return now


@pytest.fixture
def bref_requests(monkeypatch):
    calls = []

    def fake_get(url, **kwargs):
        calls.append(url)
        return SimpleNamespace(text=BREF_LINE_SCORE_HTML, status_code=200, raise_for_status=lambda: None)

    monkeypatch.setattr(basketball_reference.requests, "get", fake_get)
    monkeypatch.setattr(
        game_summary.nba_stats_client, "fetch_boxscore_summary_v3", lambda game_id: v3_summary_without_periods()
    )
    return calls


def test_throttled_fallback_is_retryable_and_recovers_after_cooldown(clock, bref_requests):
    client = TestClient(main.app)
    # Other fallback traffic took the only start in the current interval.
    basketball_reference._next_start = clock[0] + basketball_reference.INTERVAL_SECONDS

    throttled = client.get(f"/gamesummary/{GAME_ID}")

    body = throttled.json()
    assert throttled.status_code == 200
    assert body["periodScoreSource"] == "unavailable"
    assert body["periodScoreRetryAfter"] == game_summary.BREF_THROTTLED_RETRY_AFTER_SECONDS
    assert throttled.headers["Retry-After"] == str(game_summary.BREF_THROTTLED_RETRY_AFTER_SECONDS)
    assert throttled.headers["Cache-Control"] == "no-store"
    # Reliable NBA details survive without quarter scores.
    assert (body["homeTeam"]["score"], body["awayTeam"]["score"]) == ("66", "68")
    assert body["gameStatusText"] == "Final"
    assert body["homeTeam"]["periods"] == body["awayTeam"]["periods"] == []
    assert bref_requests == []
    assert len(game_summary.BREF_LINE_SCORE_CACHE) == 0

    clock[0] += game_summary.BREF_THROTTLED_RETRY_AFTER_SECONDS
    recovered = client.get(f"/gamesummary/{GAME_ID}")

    body = recovered.json()
    assert body["periodScoreSource"] == "basketball-reference"
    assert body["periodScoreRetryAfter"] is None
    assert "Retry-After" not in recovered.headers
    assert [period["score"] for period in body["homeTeam"]["periods"]] == ["12", "17", "19", "18"]
    assert len(bref_requests) == 1

    # The success is cached, so later views need no fallback capacity at all.
    clock[0] += 60
    assert client.get(f"/gamesummary/{GAME_ID}").json()["periodScoreSource"] == "basketball-reference"
    assert len(bref_requests) == 1


def test_line_score_success_and_missing_page_have_different_lifetimes(clock, monkeypatch):
    pages = [BREF_LINE_SCORE_HTML, "<html></html>"]
    calls = []

    def fake_get(url, **kwargs):
        calls.append(url)
        return SimpleNamespace(text=pages[len(calls) - 1], status_code=200, raise_for_status=lambda: None)

    monkeypatch.setattr(basketball_reference.requests, "get", fake_get)
    assert game_summary.fetch_bref_line_score("1946-11-01", "HUS")
    assert game_summary.BREF_LINE_SCORE_CACHE.expires_in(BREF_KEY) == game_summary.BREF_LINE_SCORE_TTL_SECONDS

    clock[0] += game_summary.BREF_LINE_SCORE_TTL_SECONDS
    assert game_summary.fetch_bref_line_score("1946-11-01", "HUS") is None
    assert game_summary.BREF_LINE_SCORE_CACHE.expires_in(BREF_KEY) == game_summary.BREF_MISSING_LINE_SCORE_TTL_SECONDS
    assert len(calls) == 2


def test_concurrent_views_of_one_game_share_one_fallback_fetch(monkeypatch):
    entered, release = Event(), Event()
    calls = []

    def slow(*args, **kwargs):
        calls.append(args)
        entered.set()
        assert release.wait(2)
        return SimpleNamespace(text=BREF_LINE_SCORE_HTML, raise_for_status=lambda: None)

    monkeypatch.setattr(game_summary.basketball_reference, "get", slow)
    with ThreadPoolExecutor(max_workers=3) as pool:
        leader = pool.submit(game_summary.load_bref_line_score, GAME_ID, "1946-11-01", "HUS")
        assert entered.wait(2)
        followers = [pool.submit(game_summary.load_bref_line_score, GAME_ID, "1946-11-01", "HUS") for _ in range(2)]
        wait_for_waiters(game_summary.BREF_LINE_SCORE_CACHE, BREF_KEY, 2)
        release.set()
        results = [leader.result(2), *(follower.result(2) for follower in followers)]

    assert len(calls) == 1
    assert all(line_score["HUS"]["total"] == 66 and retry_after is None for line_score, retry_after in results)


def test_joined_view_waits_a_bounded_time_then_offers_retry(monkeypatch):
    entered, release = Event(), Event()
    calls = []

    def slow(*args, **kwargs):
        calls.append(args)
        entered.set()
        assert release.wait(2)
        return SimpleNamespace(text=BREF_LINE_SCORE_HTML, raise_for_status=lambda: None)

    monkeypatch.setattr(game_summary.basketball_reference, "get", slow)
    monkeypatch.setattr(game_summary, "BREF_JOIN_WAIT_SECONDS", 0.01)
    with ThreadPoolExecutor(max_workers=1) as pool:
        leader = pool.submit(game_summary.fetch_bref_line_score, "1946-11-01", "HUS")
        assert entered.wait(2)
        joined = game_summary.load_bref_line_score(GAME_ID, "1946-11-01", "HUS")
        release.set()
        assert leader.result(2)["HUS"]["total"] == 66

    assert joined == (None, game_summary.BREF_THROTTLED_RETRY_AFTER_SECONDS)
    # The leader's fetch still filled the cache for the retry.
    assert game_summary.load_bref_line_score(GAME_ID, "1946-11-01", "HUS")[0]["HUS"]["total"] == 66
    assert len(calls) == 1


def _http_error(status):
    return requests.HTTPError(response=SimpleNamespace(status_code=status))


@pytest.mark.parametrize("error, expected", [
    (basketball_reference.FallbackRateLimited("cooling down"), game_summary.BREF_THROTTLED_RETRY_AFTER_SECONDS),
    (LoadInProgressError(BREF_KEY), game_summary.BREF_THROTTLED_RETRY_AFTER_SECONDS),
    (requests.Timeout("timed out"), game_summary.BREF_FAILED_RETRY_AFTER_SECONDS),
    (requests.ConnectionError("offline"), game_summary.BREF_FAILED_RETRY_AFTER_SECONDS),
    (_http_error(429), game_summary.BREF_FAILED_RETRY_AFTER_SECONDS),
    (_http_error(503), game_summary.BREF_FAILED_RETRY_AFTER_SECONDS),
    (_http_error(404), None),
    (ValueError("unparseable"), None),
], ids=["throttled", "joined_timeout", "timeout", "connection", "too_many_requests", "server_error", "missing_page", "parse_error"])
def test_only_transient_fallback_failures_are_retryable(error, expected):
    assert game_summary.bref_retry_after(error) == expected


def test_missing_page_is_not_offered_for_retry(monkeypatch):
    monkeypatch.setattr(game_summary.basketball_reference, "get", Mock(side_effect=_http_error(404)))
    monkeypatch.setattr(
        game_summary.nba_stats_client, "fetch_boxscore_summary_v3", lambda game_id: v3_summary_without_periods()
    )

    response = TestClient(main.app).get(f"/gamesummary/{GAME_ID}")

    assert response.json()["periodScoreSource"] == "unavailable"
    assert response.json()["periodScoreRetryAfter"] is None
    assert "Retry-After" not in response.headers
