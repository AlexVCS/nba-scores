from datetime import date
from types import SimpleNamespace

import pandas as pd
import pytest

from server.services import last_matchups

CHI, ATL = 1610612741, 1610612737


@pytest.fixture(autouse=True)
def clear_cache():
    last_matchups._cache.clear()
    yield
    last_matchups._cache.clear()


def row(game_id, game_date, matchup, pts, margin, season="22025"):
    return {"SEASON_ID": season, "GAME_ID": game_id, "GAME_DATE": game_date, "MATCHUP": matchup, "PTS": pts, "PLUS_MINUS": margin}


def finder(*rows, calls=None):
    def fetch(**kwargs):
        if calls is not None:
            calls.append(kwargs)
        return SimpleNamespace(get_data_frames=lambda: [pd.DataFrame(list(rows))])
    return fetch


def test_builds_home_and_away_scores_newest_first(monkeypatch):
    monkeypatch.setattr(last_matchups.nba_stats_client, "fetch_league_game_finder", finder(
        row("0022500115", "2025-10-27", "CHI vs. ATL", 128, 5.0),
        row("0022500411", "2025-12-23", "CHI @ ATL", 126, 3.0),
    ))
    games = last_matchups.fetch_last_matchups(CHI, ATL, date(2026, 10, 3))["games"]
    assert [game["gameId"] for game in games] == ["0022500411", "0022500115"]
    assert games[0]["awayTeam"] == {"teamId": CHI, "teamTricode": "CHI", "score": 126}
    assert games[0]["homeTeam"] == {"teamId": ATL, "teamTricode": "ATL", "score": 123}
    assert games[1]["homeTeam"]["teamTricode"] == "CHI"


def test_skips_preseason_future_games_and_limits(monkeypatch):
    calls = []
    monkeypatch.setattr(last_matchups.nba_stats_client, "fetch_league_game_finder", finder(
        row("0012500001", "2025-10-10", "CHI vs. ATL", 100, 1.0, season="12025"),
        row("0022500001", "2025-11-01", "CHI vs. ATL", 100, 1.0),
        row("0022500002", "2025-11-02", "CHI vs. ATL", 100, 1.0),
        row("0022500003", "2025-11-03", "CHI vs. ATL", 100, 1.0),
        calls=calls,
    ))
    games = last_matchups.fetch_last_matchups(CHI, ATL, date(2025, 11, 3), limit=1)["games"]
    assert [game["gameId"] for game in games] == ["0022500002"]
    last_matchups.fetch_last_matchups(CHI, ATL, date(2025, 11, 3))
    assert len(calls) == 1


def test_rejects_same_team():
    with pytest.raises(ValueError):
        last_matchups.fetch_last_matchups(CHI, CHI, date(2026, 1, 1))
