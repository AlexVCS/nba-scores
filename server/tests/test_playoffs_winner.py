"""Tests for playoff winner determination and series tallying.

These tests are offline: they build synthetic game rows instead of hitting the
NBA Stats API, so they are deterministic and fast.
"""

import pandas as pd

from server.services import playoffs


def _team_row(game_id, date, matchup, abbr, team_id, wl, pts):
    """Build a single NBA game-log-style team row for a game."""
    return {
        "GAME_ID": game_id,
        "GAME_DATE": date,
        "MATCHUP": matchup,
        "TEAM_ID": team_id,
        "TEAM_ABBREVIATION": abbr,
        "TEAM_NAME": abbr,
        "WL": wl,
        "PTS": pts,
    }


def test_determine_winner_trusts_wl_over_pts():
    """Regression for 1984-05-06 Suns/Jazz: PTS says Utah, WL says Phoenix."""
    phx = {"WL": "W", "id": 1}  # 111 pts but flagged the win
    uta = {"WL": "L", "id": 2}  # 113 pts but flagged the loss

    winner = playoffs.determine_winner(phx, uta, home_score=111, away_score=113)
    assert winner is phx


def test_determine_winner_falls_back_to_score_when_wl_missing():
    """When the WL flag is absent, the higher score should win."""
    home = {"WL": None, "id": 1}
    away = {"WL": None, "id": 2}

    assert playoffs.determine_winner(home, away, 100, 98) is home
    assert playoffs.determine_winner(home, away, 98, 100) is away


def test_series_tally_uses_wl_not_pts_when_source_score_contradicts_winner():
    """WL remains the source of truth if a source score contradicts the winner."""
    PHX, UTA = 1610612756, 1610612762
    # (game_id, date, phx_pts, uta_pts, phx_wl, uta_wl, phx_home)
    games = [
        ("0048300041", "1984-04-29", 95, 105, "L", "W", False),
        ("0048300045", "1984-05-02", 102, 97, "W", "L", False),
        ("0048300049", "1984-05-04", 106, 98, "W", "L", True),
        # Synthetic source inconsistency: scores say Utah won, WL says Phoenix won.
        ("0048300051", "1984-05-06", 111, 113, "W", "L", True),
        ("0048300056", "1984-05-08", 106, 118, "L", "W", False),
        ("0048300059", "1984-05-10", 102, 82, "W", "L", True),
    ]

    rows = []
    for gid, date, phx_pts, uta_pts, phx_wl, uta_wl, phx_home in games:
        phx_matchup = "PHX vs. UTA" if phx_home else "PHX @ UTA"
        uta_matchup = "UTA @ PHX" if phx_home else "UTA vs. PHX"
        rows.append(_team_row(gid, date, phx_matchup, "PHX", PHX, phx_wl, phx_pts))
        rows.append(_team_row(gid, date, uta_matchup, "UTA", UTA, uta_wl, uta_pts))

    df = pd.DataFrame(rows)

    normalized = playoffs.normalize_playoff_games(df)
    series = playoffs.derive_playoff_series(normalized)

    assert len(series) == 1
    suns_jazz = series[0]

    assert suns_jazz["wins"][PHX] == 4
    assert suns_jazz["wins"][UTA] == 2
    assert suns_jazz["winnerTeamId"] == PHX


def test_known_historical_scores_normalize_without_defensive_repair(monkeypatch):
    """LeagueGameLog-style completed playoff rows already carry corrected scores."""
    rows = [
        _team_row("0048300047", "1984-05-04", "NYK vs. BOS", "NYK", 1610612752, "W", 100),
        _team_row("0048300047", "1984-05-04", "BOS @ NYK", "BOS", 1610612738, "L", 92),
        _team_row("0048300049", "1984-05-04", "PHX vs. UTH", "PHX", 1610612756, "W", 106),
        _team_row("0048300049", "1984-05-04", "UTH @ PHX", "UTH", 1610612762, "L", 94),
        _team_row("0048300051", "1984-05-06", "PHX vs. UTH", "PHX", 1610612756, "W", 111),
        _team_row("0048300051", "1984-05-06", "UTH @ PHX", "UTH", 1610612762, "L", 110),
        _team_row("0048300052", "1984-05-06", "NYK vs. BOS", "NYK", 1610612752, "W", 118),
        _team_row("0048300052", "1984-05-06", "BOS @ NYK", "BOS", 1610612738, "L", 113),
        _team_row("0048300053", "1984-05-06", "DAL vs. LAL", "DAL", 1610612742, "L", 115),
        _team_row("0048300053", "1984-05-06", "LAL @ DAL", "LAL", 1610612747, "W", 122),
        _team_row("0048500304", "1986-05-18", "MIL vs. BOS", "MIL", 1610612749, "L", 98),
        _team_row("0048500304", "1986-05-18", "BOS @ MIL", "BOS", 1610612738, "W", 111),
        _team_row("0048600054", "1987-05-16", "LAL vs. SEA", "LAL", 1610612747, "W", 92),
        _team_row("0048600054", "1987-05-16", "SEA @ LAL", "SEA", 1610612760, "L", 87),
    ]

    fetch_calls = []
    monkeypatch.setattr(
        playoffs,
        "fetch_corrected_team_scores",
        lambda game_id: fetch_calls.append(game_id),
    )

    normalized = playoffs.normalize_playoff_games(pd.DataFrame(rows))
    corrected = playoffs.correct_game_scores(normalized)

    by_game = {game["gameId"]: game for game in corrected}

    assert by_game["0048300047"]["awayTeam"]["score"] == 92
    assert by_game["0048300047"]["homeTeam"]["score"] == 100
    assert by_game["0048300049"]["awayTeam"]["score"] == 94
    assert by_game["0048300049"]["homeTeam"]["score"] == 106
    assert by_game["0048300051"]["awayTeam"]["score"] == 110
    assert by_game["0048300051"]["homeTeam"]["score"] == 111
    assert by_game["0048300052"]["awayTeam"]["score"] == 113
    assert by_game["0048300052"]["homeTeam"]["score"] == 118
    assert by_game["0048300053"]["awayTeam"]["score"] == 122
    assert by_game["0048300053"]["homeTeam"]["score"] == 115
    assert by_game["0048500304"]["awayTeam"]["score"] == 111
    assert by_game["0048500304"]["homeTeam"]["score"] == 98
    assert by_game["0048600054"]["awayTeam"]["score"] == 87
    assert by_game["0048600054"]["homeTeam"]["score"] == 92
    assert fetch_calls == []
