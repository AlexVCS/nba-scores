import threading
from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from requests.exceptions import Timeout

from server import main
from server.services import game_details, nba_schedule
from server.tests.schedule_helpers import schedule_endpoint, season_schedule

SEASON_DATES = {"2025-10-21", "2025-11-01", "2026-01-15", "2026-02-10", "2026-02-20"}


@pytest.fixture
def clock(monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(nba_schedule._schedule_cache, "_clock", lambda: now[0])
    monkeypatch.setattr(nba_schedule, "current_nba_season", lambda: "2025-26")
    return now


def game_log(dates):
    return SimpleNamespace(get_data_frames=lambda: [pd.DataFrame({"GAME_DATE": sorted(dates)})])


@pytest.mark.parametrize("season, source, expected", [
    ("2025-26", nba_schedule.SOURCE_SCHEDULE, 6 * 3600),
    ("2025-26", nba_schedule.SOURCE_GAME_LOG, 5 * 60),
    ("2026-27", nba_schedule.SOURCE_SCHEDULE, 6 * 3600),
    ("2024-25", nba_schedule.SOURCE_SCHEDULE, 7 * 24 * 3600),
    ("2024-25", nba_schedule.SOURCE_GAME_LOG, 3600),
])
def test_lifetime_depends_on_season_and_source(season, source, expected):
    schedule = season_schedule(set(), season=season, source=source)
    assert nba_schedule.season_schedule_ttl(schedule, "2025-26") == expected


def test_month_views_are_derived_from_one_cached_season(monkeypatch, clock):
    fetch = Mock(return_value=schedule_endpoint(SEASON_DATES))
    monkeypatch.setattr(nba_schedule.nba_stats_client, "fetch_schedule_league_v2", fetch)
    client = TestClient(main.app)

    months = [(2025, 10), (2025, 11), (2026, 1), (2026, 2), (2026, 2)]
    responses = [client.get("/api/game-days", params={"year": y, "month": m}).json() for y, m in months]

    assert [r["game_days"] for r in responses] == [
        ["2025-10-21"], ["2025-11-01"], ["2026-01-15"], ["2026-02-10", "2026-02-20"], ["2026-02-10", "2026-02-20"],
    ]
    fetch.assert_called_once_with("2025-26")


def test_fallback_entry_is_tagged_and_retried_after_short_lifetime(monkeypatch, clock):
    schedule = Mock(side_effect=[Timeout("offline"), schedule_endpoint(SEASON_DATES)])
    fallback = Mock(return_value=game_log({"2025-10-21"}))
    monkeypatch.setattr(nba_schedule.nba_stats_client, "fetch_schedule_league_v2", schedule)
    monkeypatch.setattr(nba_schedule.nba_stats_client, "fetch_league_game_log", fallback)

    assert nba_schedule.get_season_game_dates("2025-26") == {"2025-10-21"}
    cached = nba_schedule._schedule_cache.get("2025-26")
    assert cached.source == nba_schedule.SOURCE_GAME_LOG
    assert nba_schedule._schedule_cache.expires_in("2025-26") == nba_schedule.CURRENT_GAME_LOG_TTL_SECONDS

    clock[0] += nba_schedule.CURRENT_GAME_LOG_TTL_SECONDS - 1
    assert nba_schedule.get_season_game_dates("2025-26") == {"2025-10-21"}
    clock[0] += 1
    assert nba_schedule.get_season_game_dates("2025-26") == SEASON_DATES
    assert nba_schedule._schedule_cache.get("2025-26").source == nba_schedule.SOURCE_SCHEDULE
    assert schedule.call_count == 2


def test_past_season_uses_long_lifetime(monkeypatch, clock):
    fetch = Mock(return_value=schedule_endpoint({"2024-10-22"}))
    monkeypatch.setattr(nba_schedule.nba_stats_client, "fetch_schedule_league_v2", fetch)

    nba_schedule.get_season_game_dates("2024-25")
    assert nba_schedule._schedule_cache.expires_in("2024-25") == nba_schedule.PAST_SCHEDULE_TTL_SECONDS
    clock[0] += nba_schedule.CURRENT_SCHEDULE_TTL_SECONDS
    nba_schedule.get_season_game_dates("2024-25")
    fetch.assert_called_once()


def test_cache_capacity_is_bounded(monkeypatch, clock):
    monkeypatch.setattr(
        nba_schedule.nba_stats_client, "fetch_schedule_league_v2", Mock(return_value=schedule_endpoint(set()))
    )
    for year in range(1990, 1990 + nba_schedule.SCHEDULE_CACHE_MAX_ENTRIES + 4):
        nba_schedule.get_season_game_dates(f"{year}-{str(year + 1)[-2:]}")
    assert len(nba_schedule._schedule_cache) == nba_schedule.SCHEDULE_CACHE_MAX_ENTRIES


def test_game_details_and_calendar_share_one_schedule_fetch(monkeypatch, clock):
    scheduled = {
        "gameId": "0022500001",
        "gameDateEst": "2025-10-21T00:00:00Z",
        "arenaName": "Scotiabank Arena",
    }
    payload = {"leagueSchedule": {"gameDates": [{"gameDate": "10/21/2025 00:00:00", "games": [scheduled]}]}}
    fetch = Mock(return_value=SimpleNamespace(get_dict=lambda: payload))
    monkeypatch.setattr(nba_schedule.nba_stats_client, "fetch_schedule_league_v2", fetch)

    assert nba_schedule.get_game_days_in_month(2025, 10) == ["2025-10-21"]
    assert game_details._schedule_game("0022500001")["arenaName"] == "Scotiabank Arena"
    assert nba_schedule.get_next_game_date(date(2025, 10, 20)) == "2025-10-21"
    fetch.assert_called_once_with("2025-26")


def test_game_details_refetches_when_only_fallback_dates_are_cached(monkeypatch, clock):
    nba_schedule._schedule_cache.set(
        "2025-26", season_schedule({"2025-10-21"}, source=nba_schedule.SOURCE_GAME_LOG), 300
    )
    payload = {"leagueSchedule": {"gameDates": [{"games": [{"gameId": "0022500001", "arenaName": "TD Garden"}]}]}}
    fetch = Mock(return_value=SimpleNamespace(get_dict=lambda: payload))
    monkeypatch.setattr(nba_schedule.nba_stats_client, "fetch_schedule_league_v2", fetch)

    assert game_details._schedule_game("0022500001")["arenaName"] == "TD Garden"
    fetch.assert_called_once_with("2025-26", timeout=2, retries=0)
    assert nba_schedule._schedule_cache.get("2025-26").is_schedule


def test_regular_lookup_retries_with_fallback_after_joined_optional_failure(monkeypatch, clock):
    entered, release = threading.Event(), threading.Event()
    calls = []

    def schedule(season, **kwargs):
        calls.append(kwargs)
        if kwargs:
            entered.set()
            assert release.wait(2)
        raise Timeout("offline")

    monkeypatch.setattr(nba_schedule.nba_stats_client, "fetch_schedule_league_v2", schedule)
    monkeypatch.setattr(nba_schedule.nba_stats_client, "fetch_league_game_log", Mock(return_value=game_log({"2025-10-21"})))

    optional = threading.Thread(target=lambda: pytest.raises(Exception, game_details._schedule_game, "0022500001"))
    optional.start()
    assert entered.wait(2)
    result = []
    regular = threading.Thread(target=lambda: result.append(nba_schedule.get_season_game_dates("2025-26")))
    regular.start()
    release.set()
    optional.join(2)
    regular.join(2)

    assert result == [{"2025-10-21"}]
    assert calls[0] == {"timeout": 2, "retries": 0}
