from unittest.mock import Mock

import pandas as pd
import pytest
from requests.exceptions import Timeout

from server.services import nba_schedule, nba_stats_client
from server.tests.schedule_helpers import schedule_endpoint, season_schedule


def test_schedule_client_optional_policy_uses_one_short_attempt(monkeypatch):
    endpoint = Mock(side_effect=Timeout("offline"))
    sleep = Mock()
    monkeypatch.setattr(nba_stats_client, "ScheduleLeagueV2", endpoint)
    monkeypatch.setattr(nba_stats_client.time, "sleep", sleep)

    with pytest.raises(nba_stats_client.UpstreamUnavailableError):
        nba_stats_client.fetch_schedule_league_v2("2025-26", timeout=2, retries=0)

    endpoint.assert_called_once()
    assert endpoint.call_args.kwargs["timeout"] == 2
    sleep.assert_not_called()


def test_schedule_client_defaults_keep_configured_timeout_and_retries(monkeypatch):
    endpoint = Mock(side_effect=Timeout("offline"))
    sleep = Mock()
    monkeypatch.setattr(nba_stats_client, "ScheduleLeagueV2", endpoint)
    monkeypatch.setattr(nba_stats_client.time, "sleep", sleep)

    with pytest.raises(nba_stats_client.UpstreamUnavailableError):
        nba_stats_client.fetch_schedule_league_v2("2025-26")

    assert endpoint.call_count == nba_stats_client.NBA_API_RETRIES + 1
    assert endpoint.call_args.kwargs["timeout"] == nba_stats_client.NBA_API_TIMEOUT_SECONDS
    assert sleep.call_count == nba_stats_client.NBA_API_RETRIES


def test_optional_failure_suppresses_retry_until_cooldown_expires(monkeypatch):
    now = [100.0]
    fetch = Mock(side_effect=[Timeout("offline"), season_schedule({"2026-10-03"})])
    monkeypatch.setattr(nba_schedule.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(nba_schedule, "_parse_schedule_v2", fetch)

    with pytest.raises(Timeout):
        nba_schedule.get_season_game_dates(
            "2025-26", allow_completed_fallback=False, optional_lookup=True
        )
    with pytest.raises(nba_schedule.ScheduleLookupCooldownError):
        nba_schedule.get_season_game_dates(
            "2025-26", allow_completed_fallback=False, optional_lookup=True
        )
    assert fetch.call_count == 1

    now[0] += nba_schedule.SCHEDULE_FAILURE_COOLDOWN_SECONDS
    assert nba_schedule.get_season_game_dates(
        "2025-26", allow_completed_fallback=False, optional_lookup=True
    ) == {"2026-10-03"}
    assert fetch.call_count == 2
    assert "2025-26" not in nba_schedule._schedule_failure_until


def test_cooldown_is_per_season(monkeypatch):
    monkeypatch.setattr(nba_schedule.time, "monotonic", lambda: 100.0)
    fetch = Mock(side_effect=[Timeout("offline"), season_schedule({"2026-10-03"})])
    monkeypatch.setattr(nba_schedule, "_parse_schedule_v2", fetch)

    with pytest.raises(Timeout):
        nba_schedule.get_season_game_dates(
            "2025-26", allow_completed_fallback=False, optional_lookup=True
        )
    assert nba_schedule.get_season_game_dates(
        "2026-27", allow_completed_fallback=False, optional_lookup=True
    ) == {"2026-10-03"}


def test_valid_schedule_cache_wins_during_cooldown(monkeypatch):
    monkeypatch.setattr(nba_schedule.time, "monotonic", lambda: 100.0)
    nba_schedule._schedule_failure_until["2025-26"] = 160.0
    nba_schedule._schedule_cache.set("2025-26", season_schedule({"2026-04-12"}), 60)
    parse = Mock()
    monkeypatch.setattr(nba_schedule, "_parse_schedule_v2", parse)

    assert nba_schedule.get_season_game_dates("2025-26", optional_lookup=True) == {"2026-04-12"}
    parse.assert_not_called()


@pytest.mark.parametrize("dates", [set(), {"2026-10-03"}])
def test_successful_schedule_clears_failure_state(monkeypatch, dates):
    nba_schedule._schedule_failure_until["2025-26"] = 160.0
    monkeypatch.setattr(nba_schedule, "_parse_schedule_v2", Mock(return_value=season_schedule(dates)))

    assert nba_schedule.get_season_game_dates("2025-26") == dates
    assert "2025-26" not in nba_schedule._schedule_failure_until


def test_optional_parse_error_starts_cooldown(monkeypatch):
    schedule = Mock(get_dict=lambda: {"unexpected": ["2026-10-03"]})
    fetch = Mock(return_value=schedule)
    monkeypatch.setattr(nba_schedule.time, "monotonic", lambda: 100.0)
    monkeypatch.setattr(nba_schedule.nba_stats_client, "fetch_schedule_league_v2", fetch)

    with pytest.raises(ValueError, match="missing leagueSchedule.gameDates"):
        nba_schedule.get_season_game_dates(
            "2025-26", allow_completed_fallback=False, optional_lookup=True
        )
    with pytest.raises(nba_schedule.ScheduleLookupCooldownError):
        nba_schedule.get_season_game_dates(
            "2025-26", allow_completed_fallback=False, optional_lookup=True
        )
    fetch.assert_called_once_with("2025-26", timeout=2, retries=0)


def test_regular_lookup_ignores_optional_cooldown_and_keeps_fallback(monkeypatch):
    nba_schedule._schedule_failure_until["2025-26"] = float("inf")
    schedule = Mock(side_effect=Timeout("offline"))
    fallback = Mock(return_value=season_schedule({"2025-10-21"}, source=nba_schedule.SOURCE_GAME_LOG))
    monkeypatch.setattr(nba_schedule, "_parse_schedule_v2", schedule)
    monkeypatch.setattr(nba_schedule, "_parse_game_log_fallback", fallback)

    assert nba_schedule.get_season_game_dates("2025-26") == {"2025-10-21"}
    schedule.assert_called_once_with("2025-26", timeout=None, retries=None)
    fallback.assert_called_once_with("2025-26")


def test_next_game_date_uses_optional_schedule_policy(monkeypatch):
    fetch = Mock(return_value={"2026-10-03"})
    monkeypatch.setattr(nba_schedule, "get_season_game_dates", fetch)

    assert nba_schedule.get_next_game_date(pd.Timestamp("2026-09-11").date()) == "2026-10-03"
    fetch.assert_called_once_with(
        "2025-26",
        allow_completed_fallback=False,
        optional_lookup=True,
    )


def test_empty_published_schedules_are_cached_without_cooldown(monkeypatch):
    fetch = Mock(return_value=schedule_endpoint(set()))
    monkeypatch.setattr(nba_schedule.nba_stats_client, "fetch_schedule_league_v2", fetch)

    for _ in range(2):
        assert nba_schedule.get_next_game_date(pd.Timestamp("2026-09-11").date()) is None

    assert fetch.call_count == 2
    assert [call.args[0] for call in fetch.call_args_list] == ["2025-26", "2026-27"]
    assert all(call.kwargs == {"timeout": 2, "retries": 0} for call in fetch.call_args_list)
    assert nba_schedule._schedule_failure_until == {}
