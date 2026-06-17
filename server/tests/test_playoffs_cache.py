"""Tests for the playoff dataframe cache.

The current (in-progress) season must not be cached indefinitely, otherwise a
long-lived production server keeps serving a stale game count as new playoff
games are played. Past seasons are immutable and may be cached forever.

These tests are offline: the NBA Stats client and the clock are monkeypatched.
"""

import pandas as pd

from server.services import playoffs


def _patch_finder(monkeypatch):
    calls = {"n": 0}

    class _FakePlayoffClient:
        def __init__(self, *a, **k):
            calls["n"] += 1

        def get_data_frames(self):
            return [pd.DataFrame()]

    monkeypatch.setattr(
        playoffs.leaguegamefinder,
        "LeagueGameFinder",
        _FakePlayoffClient,
    )
    monkeypatch.setattr(playoffs, "LeagueGameLog", _FakePlayoffClient)
    monkeypatch.setattr(playoffs, "_df_cache", {})
    return calls


def _patch_clock(monkeypatch):
    fake_time = {"t": 1000.0}
    monkeypatch.setattr(playoffs.time, "monotonic", lambda: fake_time["t"])
    return fake_time


def test_current_season_cache_expires(monkeypatch):
    monkeypatch.setattr(playoffs, "get_current_season", lambda: "2025-26")
    calls = _patch_finder(monkeypatch)
    fake_time = _patch_clock(monkeypatch)

    playoffs.fetch_playoff_team_games_df("2025-26")
    assert calls["n"] == 1

    # Within TTL -> served from cache.
    fake_time["t"] += playoffs._CURRENT_SEASON_TTL_SECONDS - 1
    playoffs.fetch_playoff_team_games_df("2025-26")
    assert calls["n"] == 1

    # After TTL -> refetched so new games appear.
    fake_time["t"] += 2
    playoffs.fetch_playoff_team_games_df("2025-26")
    assert calls["n"] == 2


def test_past_season_cache_never_expires(monkeypatch):
    monkeypatch.setattr(playoffs, "get_current_season", lambda: "2025-26")
    calls = _patch_finder(monkeypatch)
    fake_time = _patch_clock(monkeypatch)

    playoffs.fetch_playoff_team_games_df("1983-84")
    fake_time["t"] += 10 * playoffs._CURRENT_SEASON_TTL_SECONDS
    playoffs.fetch_playoff_team_games_df("1983-84")

    assert calls["n"] == 1
