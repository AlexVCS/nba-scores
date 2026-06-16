"""Tests for playoff winner determination and series tallying.

These tests are offline: they build synthetic game rows instead of hitting the
NBA Stats API, so they are deterministic and fast.
"""

import pandas as pd

from server.services import playoffs


def _team_row(game_id, date, matchup, abbr, team_id, wl, pts):
    """Build a single LeagueGameFinder-style team row for a game."""
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


def test_suns_jazz_1984_series_is_not_a_tie():
    """The real 1984 West Semis were Phoenix 4-2 Utah.

    Game 0048300051 (1984-05-06) has corrupt PTS in the source data (Utah 113 /
    Phoenix 111) while the WL flags correctly show a Phoenix win. The series tally
    must rely on WL so it does not render as a 3-3 tie.
    """
    PHX, UTA = 1610612756, 1610612762
    # (game_id, date, phx_pts, uta_pts, phx_wl, uta_wl, phx_home)
    games = [
        ("0048300041", "1984-04-29", 95, 105, "L", "W", False),
        ("0048300045", "1984-05-02", 102, 97, "W", "L", False),
        ("0048300049", "1984-05-04", 106, 98, "W", "L", True),
        # Corrupt PTS row: scores say Utah won, WL (correctly) says Phoenix won.
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
