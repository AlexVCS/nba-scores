import threading
from datetime import date
from unittest.mock import Mock, call

import pytest
from fastapi.testclient import TestClient

from server import main
from server.services import nba_schedule
from server.services.nba_stats_client import UpstreamUnavailableError
from server.tests.schedule_helpers import schedule_endpoint, season_schedule


def test_next_date_crosses_offseason_and_uses_schedule_cache(monkeypatch):
    def schedule(season, *, timeout=None, retries=None):
        dates = ["2026-06-15"] if season == "2025-26" else ["2026-10-05", "2026-10-03"]
        return schedule_endpoint(dates)

    fetch = Mock(side_effect=schedule)
    monkeypatch.setattr(nba_schedule.nba_stats_client, "fetch_schedule_league_v2", fetch)
    for _ in range(2):
        assert nba_schedule.get_next_game_date(date(2026, 9, 11)) == "2026-10-03"
    assert [call.args[0] for call in fetch.call_args_list] == ["2025-26", "2026-27"]


def test_next_date_excludes_today_and_earlier_dates(monkeypatch):
    fetch = Mock(return_value={"2026-01-01", "2026-01-02", "2026-01-04"})
    monkeypatch.setattr(nba_schedule, "get_season_game_dates", fetch)
    assert nba_schedule.get_next_game_date(date(2026, 1, 2)) == "2026-01-04"
    fetch.assert_called_once_with(
        "2025-26",
        allow_completed_fallback=False,
        optional_lookup=True,
    )


def test_optional_lookup_does_not_wait_for_a_busy_season(monkeypatch):
    entered, release = threading.Event(), threading.Event()

    def slow_parse(season, **_):
        entered.set()
        assert release.wait(2)
        return season_schedule({"2025-10-21"})

    parse = Mock(side_effect=slow_parse)
    monkeypatch.setattr(nba_schedule, "_parse_schedule_v2", parse)
    regular = threading.Thread(target=nba_schedule.get_season_game_dates, args=("2025-26",))
    regular.start()
    try:
        assert entered.wait(2)
        with pytest.raises(nba_schedule.ScheduleLookupCooldownError):
            nba_schedule.get_season_game_dates("2025-26", optional_lookup=True)
    finally:
        release.set()
        regular.join(2)
    parse.assert_called_once()


@pytest.mark.parametrize("error", [
    ValueError("bad schedule"),
    UpstreamUnavailableError("ScheduleLeagueV2", "Timeout", 10),
], ids=["invalid_schedule", "upstream_unavailable"])
def test_next_date_checks_upcoming_season_after_older_season_failure(monkeypatch, error):
    fetch = Mock(side_effect=[error, {"2026-10-05", "2026-10-03", "2026-10-04"}])
    monkeypatch.setattr(nba_schedule, "get_season_game_dates", fetch)

    assert nba_schedule.get_next_game_date(date(2026, 9, 11)) == "2026-10-03"
    assert fetch.call_args_list == [
        call("2025-26", allow_completed_fallback=False, optional_lookup=True),
        call("2026-27", allow_completed_fallback=False, optional_lookup=True),
    ]


def test_no_published_future_dates_returns_none(monkeypatch):
    monkeypatch.setattr(nba_schedule, "get_season_game_dates", Mock(return_value=set()))
    assert nba_schedule.get_next_game_date(date(2026, 9, 11)) is None


def test_schedule_failure_does_not_fall_back_to_completed_games(monkeypatch):
    first_error = ValueError("bad older-season schedule")
    parse = Mock(side_effect=[first_error, ValueError("bad upcoming-season schedule")])
    monkeypatch.setattr(nba_schedule, "_parse_schedule_v2", parse)
    fetch = Mock(wraps=nba_schedule.get_season_game_dates)
    monkeypatch.setattr(nba_schedule, "get_season_game_dates", fetch)
    log = Mock()
    monkeypatch.setattr(nba_schedule, "_parse_game_log_fallback", log)
    with pytest.raises(ValueError) as exc_info:
        nba_schedule.get_next_game_date(date(2026, 9, 11))
    assert exc_info.value is first_error
    assert fetch.call_args_list == [
        call("2025-26", allow_completed_fallback=False, optional_lookup=True),
        call("2026-27", allow_completed_fallback=False, optional_lookup=True),
    ]
    assert parse.call_args_list == [
        call("2025-26", timeout=2, retries=0),
        call("2026-27", timeout=2, retries=0),
    ]
    log.assert_not_called()


def test_next_date_raises_original_failure_after_upcoming_season_is_empty(monkeypatch):
    error = UpstreamUnavailableError("ScheduleLeagueV2", "Timeout", 10)
    fetch = Mock(side_effect=[error, set()])
    monkeypatch.setattr(nba_schedule, "get_season_game_dates", fetch)

    with pytest.raises(UpstreamUnavailableError) as exc_info:
        nba_schedule.get_next_game_date(date(2026, 9, 11))
    assert exc_info.value is error
    assert fetch.call_args_list == [
        call("2025-26", allow_completed_fallback=False, optional_lookup=True),
        call("2026-27", allow_completed_fallback=False, optional_lookup=True),
    ]


def test_schedule_parser_accepts_nba_game_date_format(monkeypatch):
    schedule = schedule_endpoint({"2026-10-03"}, date_format="nba")
    monkeypatch.setattr(nba_schedule.nba_stats_client, "fetch_schedule_league_v2", Mock(return_value=schedule))
    assert nba_schedule.get_season_game_dates("2026-27") == {"2026-10-03"}


def test_default_scoreboard_includes_next_date(monkeypatch):
    fetch = Mock(return_value="2026-10-03")
    monkeypatch.setattr(main.nba_stats_client, "fetch_scoreboard_v3", Mock(return_value={"games": []}))
    monkeypatch.setattr(main, "get_next_game_date", fetch)
    response = TestClient(main.app).get("/")
    assert response.status_code == 200
    assert response.json() == {"games": [], "nextGameDate": "2026-10-03"}
    requested_date = main.nba_stats_client.fetch_scoreboard_v3.call_args.args[0]
    fetch.assert_called_once_with(date.fromisoformat(requested_date))


@pytest.mark.parametrize("explicit_date, games", [("2026-09-11", []), (None, [{"gameId": "0012600001", "gameStatus": 1}])])
def test_scoreboard_skips_lookup_for_explicit_dates_or_existing_games(monkeypatch, explicit_date, games):
    monkeypatch.setattr(main.nba_stats_client, "fetch_scoreboard_v3", Mock(return_value={"games": games}))
    fetch = Mock()
    monkeypatch.setattr(main, "get_next_game_date", fetch)
    response = TestClient(main.app).get("/", params={"date": explicit_date} if explicit_date else {})
    assert response.status_code == 200
    assert "nextGameDate" not in response.json()
    fetch.assert_not_called()


def test_default_scoreboard_keeps_empty_games_on_schedule_failure(monkeypatch):
    error = UpstreamUnavailableError("ScheduleLeagueV2", "Timeout", 10)
    monkeypatch.setattr(main.nba_stats_client, "fetch_scoreboard_v3", Mock(return_value={"games": []}))
    monkeypatch.setattr(main, "get_next_game_date", Mock(side_effect=error))
    response = TestClient(main.app).get("/")
    assert response.status_code == 200
    assert response.json() == {"games": []}


def test_default_scoreboard_suppresses_repeated_schedule_warning(monkeypatch, caplog):
    error = UpstreamUnavailableError("ScheduleLeagueV2", "Timeout", 10)
    parse = Mock(side_effect=error)
    monkeypatch.setattr(nba_schedule.time, "monotonic", lambda: 100.0)
    monkeypatch.setattr(main.nba_stats_client, "fetch_scoreboard_v3", Mock(return_value={"games": []}))
    monkeypatch.setattr(nba_schedule, "_parse_schedule_v2", parse)

    with caplog.at_level("WARNING", logger=main.__name__):
        first = TestClient(main.app).get("/")
        records_after_first_request = len(caplog.records)
        second = TestClient(main.app).get("/")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == {"games": []}
    assert second.json() == {"games": []}
    assert parse.call_count == 2
    assert len(caplog.records) == records_after_first_request
    assert [record.message for record in caplog.records].count("Next game date unavailable") == 1
