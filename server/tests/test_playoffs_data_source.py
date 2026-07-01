from datetime import date

import pandas as pd
import pytest
from fastapi import HTTPException
from requests.exceptions import ReadTimeout

from server.services import playoffs


def test_historical_season_uses_league_game_log():
    assert (
        playoffs.get_playoff_data_source("1983-84", date(2026, 6, 16))
        == "league_game_log"
    )


def test_current_season_during_playoff_window_uses_league_game_finder():
    assert (
        playoffs.get_playoff_data_source("2025-26", date(2026, 5, 15))
        == "league_game_finder"
    )


def test_current_season_outside_playoff_window_uses_league_game_log():
    assert (
        playoffs.get_playoff_data_source("2025-26", date(2026, 7, 1))
        == "league_game_log"
    )


def test_previous_season_during_playoff_window_uses_league_game_log():
    assert (
        playoffs.get_playoff_data_source("2024-25", date(2026, 5, 15))
        == "league_game_log"
    )


def test_fetch_uses_league_game_log_for_completed_season(monkeypatch):
    calls = []
    expected = pd.DataFrame([{"GAME_ID": "0048300047"}])
    monkeypatch.setattr(playoffs, "_df_cache", {})

    class FakeLeagueGameLog:
        def __init__(self, **kwargs):
            calls.append(kwargs)

        def get_data_frames(self):
            return [expected]

    monkeypatch.setattr(playoffs, "LeagueGameLog", FakeLeagueGameLog)

    df = playoffs.fetch_playoff_team_games_df("1983-84", date(2026, 6, 16))

    assert df is expected
    assert calls == [
        {
            "season": "1983-84",
            "season_type_all_star": "Playoffs",
            "league_id": "00",
            "timeout": None,
        }
    ]


def test_fetch_uses_league_game_finder_for_current_playoff_window(monkeypatch):
    calls = []
    expected = pd.DataFrame([{"GAME_ID": "0042500001"}])
    monkeypatch.setattr(playoffs, "_df_cache", {})

    class FakeLeagueGameFinder:
        def __init__(self, **kwargs):
            calls.append(kwargs)

        def get_data_frames(self):
            return [expected]

    monkeypatch.setattr(
        playoffs.leaguegamefinder,
        "LeagueGameFinder",
        FakeLeagueGameFinder,
    )

    df = playoffs.fetch_playoff_team_games_df("2025-26", date(2026, 5, 15))

    assert df is expected
    assert calls == [
        {
            "season_nullable": "2025-26",
            "season_type_nullable": "Playoffs",
            "league_id_nullable": "00",
            "timeout": None,
        }
    ]


def test_fetch_maps_data_frame_timeout_to_service_unavailable(monkeypatch):
    monkeypatch.setattr(playoffs, "_df_cache", {})

    class FakeLeagueGameLog:
        def __init__(self, **kwargs):
            pass

        def get_data_frames(self):
            raise ReadTimeout("boom")

    monkeypatch.setattr(playoffs, "LeagueGameLog", FakeLeagueGameLog)

    with pytest.raises(HTTPException) as exc:
        playoffs.fetch_playoff_team_games_df("1983-84", date(2026, 6, 16))

    assert exc.value.status_code == 503
    assert "NBA Stats API unavailable" in exc.value.detail
    assert isinstance(exc.value.__cause__, ReadTimeout)


def test_fetch_cache_is_source_aware(monkeypatch):
    log_df = pd.DataFrame([{"GAME_ID": "log"}])
    finder_df = pd.DataFrame([{"GAME_ID": "finder"}])
    monkeypatch.setattr(playoffs, "_df_cache", {})

    class FakeLeagueGameLog:
        def __init__(self, **kwargs):
            pass

        def get_data_frames(self):
            return [log_df]

    class FakeLeagueGameFinder:
        def __init__(self, **kwargs):
            pass

        def get_data_frames(self):
            return [finder_df]

    monkeypatch.setattr(playoffs, "LeagueGameLog", FakeLeagueGameLog)
    monkeypatch.setattr(
        playoffs.leaguegamefinder,
        "LeagueGameFinder",
        FakeLeagueGameFinder,
    )

    active = playoffs.fetch_playoff_team_games_df("2025-26", date(2026, 5, 15))
    completed = playoffs.fetch_playoff_team_games_df("2025-26", date(2026, 7, 1))

    assert active is finder_df
    assert completed is log_df
