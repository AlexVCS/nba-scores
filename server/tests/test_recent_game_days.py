import threading
import time
from datetime import date
from unittest.mock import Mock

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from server import main
from server.services import nba_schedule
from server.services.nba_stats_client import UpstreamUnavailableError


SEASON_DATES = {
    "2024-25": {"2024-10-22", "2024-12-25", "2025-04-13", "2025-06-22"},
    "2025-26": {"2025-10-21", "2025-11-01", "2026-01-15", "2026-02-10", "2026-02-20"},
}


@pytest.fixture(autouse=True)
def clear_schedule_state():
    nba_schedule._cache.clear()
    nba_schedule._schedule_failure_until.clear()
    nba_schedule._season_locks.clear()
    yield
    nba_schedule._cache.clear()
    nba_schedule._schedule_failure_until.clear()
    nba_schedule._season_locks.clear()


def _schedule_response(dates):
    return Mock(get_data_frames=lambda: [pd.DataFrame({"gameDateEst": sorted(dates)})])


def test_recent_game_days_spans_season_boundary_sorted_desc(monkeypatch):
    fetch = Mock(side_effect=lambda season, **_: SEASON_DATES[season])
    monkeypatch.setattr(nba_schedule, "get_season_game_dates", fetch)

    # Window: 2025-03-01 .. 2026-02-19 (exclusive)
    result = nba_schedule.get_recent_game_days(date(2026, 2, 20))

    assert result == [
        "2026-02-10",
        "2026-01-15",
        "2025-11-01",
        "2025-10-21",
        "2025-06-22",
        "2025-04-13",
    ]
    assert sorted(c.args[0] for c in fetch.call_args_list) == ["2024-25", "2025-26"]


def test_recent_game_days_respects_months_param(monkeypatch):
    fetch = Mock(side_effect=lambda season, **_: SEASON_DATES[season])
    monkeypatch.setattr(nba_schedule, "get_season_game_dates", fetch)

    # Window: 2026-01-01 .. 2026-02-19
    assert nba_schedule.get_recent_game_days(date(2026, 2, 20), months=2) == [
        "2026-02-10",
        "2026-01-15",
    ]
    assert [c.args[0] for c in fetch.call_args_list] == ["2025-26"]


def test_recent_game_days_returns_partial_when_one_season_fails(monkeypatch, caplog):
    def fetch(season, **_):
        if season == "2024-25":
            raise UpstreamUnavailableError("ScheduleLeagueV2", "Timeout", 10)
        return SEASON_DATES[season]

    monkeypatch.setattr(nba_schedule, "get_season_game_dates", Mock(side_effect=fetch))
    with caplog.at_level("WARNING", logger=nba_schedule.__name__):
        result = nba_schedule.get_recent_game_days(date(2026, 2, 20))

    assert result == ["2026-02-10", "2026-01-15", "2025-11-01", "2025-10-21"]
    assert any("2024-25" in r.getMessage() for r in caplog.records)


def test_recent_game_days_reraises_when_all_seasons_fail(monkeypatch):
    error = UpstreamUnavailableError("ScheduleLeagueV2", "Timeout", 10)
    monkeypatch.setattr(nba_schedule, "get_season_game_dates", Mock(side_effect=error))
    with pytest.raises(UpstreamUnavailableError):
        nba_schedule.get_recent_game_days(date(2026, 2, 20))


def test_recent_route_returns_payload(monkeypatch):
    monkeypatch.setattr(
        nba_schedule,
        "get_season_game_dates",
        Mock(side_effect=lambda season, **_: SEASON_DATES[season]),
    )
    response = TestClient(main.app).get(
        "/api/game-days/recent", params={"before": "2026-02-20", "months": 2}
    )
    assert response.status_code == 200
    assert response.json() == {
        "before": "2026-02-20",
        "game_days": ["2026-02-10", "2026-01-15"],
        "total": 2,
    }


def test_recent_route_all_failing_maps_upstream_error(monkeypatch):
    error = UpstreamUnavailableError("ScheduleLeagueV2", "Timeout", 10)
    monkeypatch.setattr(nba_schedule, "get_season_game_dates", Mock(side_effect=error))
    response = TestClient(main.app).get(
        "/api/game-days/recent", params={"before": "2026-02-20"}
    )
    assert response.status_code == 503


def test_recent_route_all_failing_generic_error_is_502(monkeypatch):
    monkeypatch.setattr(
        nba_schedule, "get_season_game_dates", Mock(side_effect=ValueError("bad"))
    )
    response = TestClient(main.app).get(
        "/api/game-days/recent", params={"before": "2026-02-20"}
    )
    assert response.status_code == 502


@pytest.mark.parametrize("params", [
    {"before": "not-a-date"},
    {"before": "2026-02-30"},
    {},
    {"before": "2026-02-20", "months": 0},
    {"before": "2026-02-20", "months": 25},
])
def test_recent_route_rejects_invalid_params(params):
    response = TestClient(main.app).get("/api/game-days/recent", params=params)
    assert response.status_code == 422


def test_existing_month_route_still_works(monkeypatch):
    monkeypatch.setattr(
        nba_schedule,
        "get_season_game_dates",
        Mock(side_effect=lambda season, **_: SEASON_DATES[season]),
    )
    response = TestClient(main.app).get("/api/game-days", params={"year": 2026, "month": 2})
    assert response.status_code == 200
    assert response.json()["game_days"] == ["2026-02-10", "2026-02-20"]


def test_concurrent_cold_cache_calls_fetch_season_once(monkeypatch):
    def slow_fetch(season, **_):
        time.sleep(0.2)
        return _schedule_response(SEASON_DATES[season])

    fetch = Mock(side_effect=slow_fetch)
    monkeypatch.setattr(nba_schedule.nba_stats_client, "fetch_schedule_league_v2", fetch)

    barrier = threading.Barrier(8)
    results: list[set[str]] = []
    errors: list[BaseException] = []

    def worker():
        try:
            barrier.wait()
            results.append(nba_schedule.get_season_game_dates("2025-26"))
        except BaseException as exc:  # pragma: no cover - surfaced below
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)

    assert not errors
    assert len(results) == 8
    assert all(r == SEASON_DATES["2025-26"] for r in results)
    assert fetch.call_count == 1


def test_concurrent_calls_for_different_seasons_do_not_serialize(monkeypatch):
    def slow_fetch(season, **_):
        time.sleep(0.3)
        return _schedule_response(SEASON_DATES[season])

    fetch = Mock(side_effect=slow_fetch)
    monkeypatch.setattr(nba_schedule.nba_stats_client, "fetch_schedule_league_v2", fetch)

    threads = [
        threading.Thread(target=nba_schedule.get_season_game_dates, args=(season,))
        for season in ("2024-25", "2025-26")
    ]
    start = time.monotonic()
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)
    elapsed = time.monotonic() - start

    assert fetch.call_count == 2
    assert elapsed < 0.55
