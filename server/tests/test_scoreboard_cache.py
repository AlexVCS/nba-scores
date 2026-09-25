import threading
import time
from datetime import date, datetime, timezone
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from server import main
from server.services import scoreboard
from server.services.nba_stats_client import UpstreamBadResponseError, UpstreamUnavailableError
from server.utils.season import NBA_TIMEZONE

NOW = datetime(2026, 1, 20, 21, 0, tzinfo=NBA_TIMEZONE)


def game(status, game_id="0022500001"):
    return {"gameId": game_id, "gameStatus": status}


def board(*statuses):
    return {"games": [game(status, f"00225{index:05d}") for index, status in enumerate(statuses)]}


@pytest.mark.parametrize("games, game_date, expected", [
    ([2, 2], "2026-01-20", scoreboard.LIVE_TTL_SECONDS),
    ([2, 3], "2026-01-20", scoreboard.LIVE_TTL_SECONDS),
    ([1, 2], "2026-01-20", scoreboard.LIVE_TTL_SECONDS),
    ([1, 1], "2026-01-20", scoreboard.SCHEDULED_TTL_SECONDS),
    ([1, 1], "2026-01-25", scoreboard.SCHEDULED_TTL_SECONDS),
    ([3, 3], "2026-01-19", scoreboard.RECENT_FINAL_TTL_SECONDS),
    ([3, 3], "2026-01-17", scoreboard.RECENT_FINAL_TTL_SECONDS),
    ([3, 3], "2026-01-16", scoreboard.SETTLED_TTL_SECONDS),
    ([3, 3], "2024-11-01", scoreboard.SETTLED_TTL_SECONDS),
    ([], "2026-01-19", scoreboard.SETTLED_TTL_SECONDS),
    ([], "2026-01-20", scoreboard.SCHEDULED_TTL_SECONDS),
    ([], "2026-01-21", scoreboard.SCHEDULED_TTL_SECONDS),
    ([3, None], "2024-11-01", scoreboard.UNKNOWN_TTL_SECONDS),
    ([3, "Final"], "2024-11-01", scoreboard.UNKNOWN_TTL_SECONDS),
    ([3, 7], "2024-11-01", scoreboard.UNKNOWN_TTL_SECONDS),
], ids=[
    "all_live", "live_and_final", "live_and_scheduled", "all_scheduled_today", "all_scheduled_future",
    "final_yesterday", "final_within_72h", "final_older_than_72h", "final_long_ago",
    "empty_past", "empty_today", "empty_future",
    "missing_status", "unparseable_status", "unknown_status",
])
def test_lifetime_is_chosen_from_fetched_statuses(games, game_date, expected):
    data = {"games": [game(status) for status in games]}
    assert scoreboard.scoreboard_ttl(data, date.fromisoformat(game_date), NOW) == expected


def test_all_final_window_uses_the_end_of_the_game_day():
    final = board(3)
    # Jan 17 ends at Jan 18 00:00 ET, so 72 hours later is Jan 21 00:00 ET.
    before = datetime(2026, 1, 20, 23, 59, tzinfo=NBA_TIMEZONE)
    after = datetime(2026, 1, 21, 0, 0, tzinfo=NBA_TIMEZONE)
    assert scoreboard.scoreboard_ttl(final, date(2026, 1, 17), before) == scoreboard.RECENT_FINAL_TTL_SECONDS
    assert scoreboard.scoreboard_ttl(final, date(2026, 1, 17), after) == scoreboard.SETTLED_TTL_SECONDS


@pytest.fixture
def clock(monkeypatch):
    now = [5000.0]
    monkeypatch.setattr(scoreboard._scoreboard_cache, "_clock", lambda: now[0])
    monkeypatch.setattr(scoreboard, "nba_now", lambda: NOW)
    return now


def test_live_entry_expires_quickly_and_final_refetch_gets_completed_lifetime(monkeypatch, clock):
    fetch = Mock(side_effect=[board(2, 3), board(3, 3)])
    monkeypatch.setattr(scoreboard.nba_stats_client, "fetch_scoreboard_v3", fetch)

    assert scoreboard.get_scoreboard("2026-01-20")["games"][0]["gameStatus"] == 2
    assert scoreboard._scoreboard_cache.expires_in("2026-01-20") == scoreboard.LIVE_TTL_SECONDS
    clock[0] += scoreboard.LIVE_TTL_SECONDS - 1
    assert scoreboard.get_scoreboard("2026-01-20")["games"][0]["gameStatus"] == 2
    assert fetch.call_count == 1

    clock[0] += 1
    assert scoreboard.get_scoreboard("2026-01-20")["games"][0]["gameStatus"] == 3
    assert fetch.call_count == 2
    assert scoreboard._scoreboard_cache.expires_in("2026-01-20") == scoreboard.RECENT_FINAL_TTL_SECONDS


def test_repeated_route_requests_reuse_cache_and_return_identical_bodies(monkeypatch):
    fetch = Mock(return_value=board(3, 1))
    monkeypatch.setattr(main.nba_stats_client, "fetch_scoreboard_v3", fetch)
    client = TestClient(main.app)

    first = client.get("/", params={"date": "2024-11-01"})
    second = client.get("/", params={"date": "2024-11-01"})

    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert [g["boxscoreAvailable"] for g in first.json()["games"]] == [True, False]
    fetch.assert_called_once_with("2024-11-01")


def test_default_and_explicit_today_share_one_entry(monkeypatch):
    monkeypatch.setattr(main, "nba_today", lambda: date(2026, 1, 20))
    fetch = Mock(return_value=board(1))
    monkeypatch.setattr(main.nba_stats_client, "fetch_scoreboard_v3", fetch)
    client = TestClient(main.app)

    default = client.get("/")
    explicit = client.get("/", params={"date": "2026-01-20"})

    assert default.json() == explicit.json()
    fetch.assert_called_once_with("2026-01-20")


def test_default_date_uses_nba_eastern_time(monkeypatch):
    # 03:30 UTC on Jan 21 is still the evening of Jan 20 in New York.
    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 1, 21, 3, 30, tzinfo=timezone.utc).astimezone(tz)

    from server.utils import season

    monkeypatch.setattr(season, "datetime", FrozenDateTime)
    assert season.nba_today() == date(2026, 1, 20)


def test_default_and_explicit_today_share_one_in_flight_call(monkeypatch):
    monkeypatch.setattr(main, "nba_today", lambda: date(2026, 1, 20))
    calls = []

    def slow_fetch(game_date):
        calls.append(game_date)
        time.sleep(0.2)
        return board(2)

    monkeypatch.setattr(main.nba_stats_client, "fetch_scoreboard_v3", slow_fetch)
    client = TestClient(main.app)
    responses = []
    requests = [lambda: client.get("/"), lambda: client.get("/", params={"date": "2026-01-20"})] * 2
    threads = [threading.Thread(target=lambda r=request: responses.append(r())) for request in requests]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(5)

    assert calls == ["2026-01-20"]
    assert len(responses) == 4
    assert all(response.json() == responses[0].json() for response in responses)


def test_different_dates_do_not_serialize(monkeypatch):
    def slow_fetch(game_date):
        time.sleep(0.3)
        return board(3)

    monkeypatch.setattr(scoreboard.nba_stats_client, "fetch_scoreboard_v3", slow_fetch)
    threads = [threading.Thread(target=scoreboard.get_scoreboard, args=(day,)) for day in ("2024-11-01", "2024-11-02")]
    started = time.monotonic()
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(5)
    assert time.monotonic() - started < 0.55


def test_mutating_a_response_does_not_alter_the_cached_entry(monkeypatch):
    monkeypatch.setattr(scoreboard.nba_stats_client, "fetch_scoreboard_v3", Mock(return_value=board(3)))

    first = scoreboard.get_scoreboard("2024-11-01")
    first["games"][0]["gameStatus"] = 99
    first["games"].append({"gameId": "extra"})
    first["nextGameDate"] = "2024-11-02"

    assert scoreboard.get_scoreboard("2024-11-01") == board(3)


def test_route_enrichment_does_not_leak_into_cache(monkeypatch):
    monkeypatch.setattr(main, "nba_today", lambda: date(2026, 9, 11))
    monkeypatch.setattr(main.nba_stats_client, "fetch_scoreboard_v3", Mock(return_value={"games": []}))
    monkeypatch.setattr(main, "get_next_game_date", Mock(return_value="2026-10-03"))
    client = TestClient(main.app)

    assert client.get("/").json() == {"games": [], "nextGameDate": "2026-10-03"}
    assert client.get("/", params={"date": "2026-09-11"}).json() == {"games": []}
    assert scoreboard._scoreboard_cache.get("2026-09-11") == {"games": []}


def test_upstream_failure_is_not_cached_and_retries(monkeypatch):
    error = UpstreamUnavailableError("ScoreboardV3", "Timeout", 10)
    fetch = Mock(side_effect=[error, board(3)])
    monkeypatch.setattr(main.nba_stats_client, "fetch_scoreboard_v3", fetch)
    client = TestClient(main.app)

    failed = client.get("/", params={"date": "2024-11-01"})
    assert failed.status_code == 503
    assert failed.json()["detail"]["endpoint"] == "ScoreboardV3"
    assert client.get("/", params={"date": "2024-11-01"}).status_code == 200
    assert fetch.call_count == 2


def test_malformed_games_are_a_bad_response_and_not_cached(monkeypatch):
    fetch = Mock(side_effect=[{"games": None}, board(3)])
    monkeypatch.setattr(main.nba_stats_client, "fetch_scoreboard_v3", fetch)
    client = TestClient(main.app)

    assert client.get("/", params={"date": "2024-11-01"}).status_code == 502
    assert client.get("/", params={"date": "2024-11-01"}).status_code == 200
    assert fetch.call_count == 2
    with pytest.raises(UpstreamBadResponseError):
        fetch.side_effect = [{"games": "nope"}]
        scoreboard._scoreboard_cache.clear()
        scoreboard.get_scoreboard("2024-11-01")


def test_impossible_calendar_date_is_rejected_without_upstream_call(monkeypatch):
    fetch = Mock()
    monkeypatch.setattr(main.nba_stats_client, "fetch_scoreboard_v3", fetch)
    response = TestClient(main.app).get("/", params={"date": "2026-02-30"})
    assert response.status_code == 400
    fetch.assert_not_called()


def test_game_details_date_hint_reuses_the_scoreboard_cache(monkeypatch):
    from server.services import game_details

    live = {
        "gameId": "0022500001",
        "gameStatus": 3,
        "gameStatusText": "Final",
        "homeTeam": {"teamId": 1, "teamTricode": "TOR"},
        "awayTeam": {"teamId": 2, "teamTricode": "MIA"},
    }
    fetch = Mock(return_value={"games": [live]})
    monkeypatch.setattr(main.nba_stats_client, "fetch_scoreboard_v3", fetch)

    TestClient(main.app).get("/", params={"date": "2024-11-01"})
    assert game_details.fetch_game_details("0022500001", "2024-11-01")["gameStatusText"] == "Final"
    fetch.assert_called_once_with("2024-11-01")
