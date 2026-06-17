"""Regression tests for duplicate-matchup playoff series reconciliation."""

from collections import Counter

import pandas as pd

from server.services import playoffs


BOS = 1610612738
LAL = 1610612747
NYK = 1610612752
PHL = 1610612755
ROC = 1610612758


def _team_row(game_id, date, matchup, abbr, team_id, wl, pts):
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


def _add_game(rows, game_id, date, away, home, winner_abbr):
    away_abbr, away_id, away_pts = away
    home_abbr, home_id, home_pts = home

    rows.append(
        _team_row(
            game_id,
            date,
            f"{home_abbr} vs. {away_abbr}",
            home_abbr,
            home_id,
            "W" if winner_abbr == home_abbr else "L",
            home_pts,
        )
    )
    rows.append(
        _team_row(
            game_id,
            date,
            f"{away_abbr} @ {home_abbr}",
            away_abbr,
            away_id,
            "W" if winner_abbr == away_abbr else "L",
            away_pts,
        )
    )


def _series_for_rows(season, rows):
    normalized = playoffs.normalize_playoff_games(pd.DataFrame(rows))
    with_rounds = playoffs.apply_rounds_to_games(normalized)
    reconciled = playoffs.reconcile_duplicate_matchup_rounds(season, with_rounds)
    series = playoffs.derive_playoff_series(reconciled)
    bracket = playoffs.enrich_playoff_bracket_response(season, series)
    return bracket["series"]


def _series_for_pair(series, *team_ids):
    pair = set(team_ids)
    return [
        item
        for item in series
        if {team["id"] for team in item["teams"]} == pair
    ]


def _assert_no_duplicate_pairs(series):
    pairs = Counter(
        tuple(sorted(team["id"] for team in item["teams"]))
        for item in series
    )
    assert all(count == 1 for count in pairs.values())


def _assert_no_completed_finals_tie(series):
    for item in series:
        if not item.get("isFinals"):
            continue

        wins = list(item["wins"].values())
        assert len(wins) != 2 or wins[0] != wins[1]


def _assert_series_reaches_target(series):
    for item in series:
        target_wins = item.get("targetWins")
        if target_wins is None:
            continue

        assert max(item["wins"].values()) == target_wins


def _1951_finals_rows():
    rows = []
    games = [
        ("0045000301", "1951-04-07", ("NYK", NYK, 65), ("ROC", ROC, 92), "ROC"),
        ("0045000412", "1951-04-08", ("NYK", NYK, 84), ("ROC", ROC, 99), "ROC"),
        ("0045000413", "1951-04-11", ("ROC", ROC, 78), ("NYK", NYK, 71), "ROC"),
        ("0045000414", "1951-04-13", ("ROC", ROC, 73), ("NYK", NYK, 79), "NYK"),
        ("0045000415", "1951-04-15", ("NYK", NYK, 92), ("ROC", ROC, 89), "NYK"),
        ("0045000416", "1951-04-18", ("ROC", ROC, 73), ("NYK", NYK, 80), "NYK"),
        ("0045000417", "1951-04-21", ("NYK", NYK, 75), ("ROC", ROC, 79), "ROC"),
    ]

    for game in games:
        _add_game(rows, *game)

    return rows


def _1965_finals_rows():
    rows = []
    games = [
        ("0046400301", "1965-04-18", ("LAL", LAL, 110), ("BOS", BOS, 142), "BOS"),
        ("0046400412", "1965-04-19", ("LAL", LAL, 123), ("BOS", BOS, 129), "BOS"),
        ("0046400413", "1965-04-21", ("BOS", BOS, 105), ("LAL", LAL, 126), "LAL"),
        ("0046400414", "1965-04-23", ("BOS", BOS, 112), ("LAL", LAL, 99), "BOS"),
        ("0046400415", "1965-04-25", ("LAL", LAL, 96), ("BOS", BOS, 129), "BOS"),
    ]

    for game in games:
        _add_game(rows, *game)

    return rows


def _1967_eastern_finals_rows():
    rows = []
    games = [
        ("0046600321", "1967-03-31", ("BOS", BOS, 113), ("PHL", PHL, 127), "PHL"),
        ("0046600322", "1967-04-02", ("PHL", PHL, 107), ("BOS", BOS, 102), "PHL"),
        ("0046600323", "1967-04-05", ("BOS", BOS, 104), ("PHL", PHL, 115), "PHL"),
        ("0046600204", "1967-04-09", ("PHL", PHL, 117), ("BOS", BOS, 121), "BOS"),
        ("0046600325", "1967-04-11", ("BOS", BOS, 116), ("PHL", PHL, 140), "PHL"),
    ]

    for game in games:
        _add_game(rows, *game)

    return rows


def test_1951_duplicate_matchup_orphan_merges_into_finals():
    series = _series_for_rows("1950-51", _1951_finals_rows())
    finals = _series_for_pair(series, ROC, NYK)

    assert len(finals) == 1
    assert finals[0]["round"] == 4
    assert finals[0]["gameCount"] == 7
    assert finals[0]["wins"][ROC] == 4
    assert finals[0]["wins"][NYK] == 3
    assert finals[0]["winnerTeamId"] == ROC
    assert "1951-04-07" in [game["date"] for game in finals[0]["games"]]


def test_1965_duplicate_matchup_orphan_merges_into_finals():
    series = _series_for_rows("1964-65", _1965_finals_rows())
    finals = _series_for_pair(series, BOS, LAL)

    assert len(finals) == 1
    assert finals[0]["round"] == 4
    assert finals[0]["gameCount"] == 5
    assert finals[0]["wins"][BOS] == 4
    assert finals[0]["wins"][LAL] == 1
    assert finals[0]["winnerTeamId"] == BOS
    assert "1965-04-18" in [game["date"] for game in finals[0]["games"]]


def test_1967_duplicate_matchup_orphan_merges_into_division_finals():
    series = _series_for_rows("1966-67", _1967_eastern_finals_rows())
    eastern_finals = _series_for_pair(series, PHL, BOS)

    assert len(eastern_finals) == 1
    assert eastern_finals[0]["round"] == 3
    assert eastern_finals[0]["gameCount"] == 5
    assert eastern_finals[0]["wins"][PHL] == 4
    assert eastern_finals[0]["wins"][BOS] == 1
    assert eastern_finals[0]["winnerTeamId"] == PHL
    assert "1967-04-09" in [game["date"] for game in eastern_finals[0]["games"]]


def test_corrected_historical_series_invariants():
    cases = [
        ("1950-51", _1951_finals_rows()),
        ("1964-65", _1965_finals_rows()),
        ("1966-67", _1967_eastern_finals_rows()),
    ]

    for season, rows in cases:
        series = _series_for_rows(season, rows)

        _assert_no_duplicate_pairs(series)
        _assert_no_completed_finals_tie(series)
        _assert_series_reaches_target(series)


def test_reconciliation_does_not_merge_duplicate_pair_when_orphan_is_not_one_game():
    rows = []
    games = [
        ("0046400301", "1965-04-18", ("LAL", LAL, 110), ("BOS", BOS, 142), "BOS"),
        ("0046400302", "1965-04-19", ("BOS", BOS, 100), ("LAL", LAL, 105), "LAL"),
        ("0046400413", "1965-04-21", ("BOS", BOS, 105), ("LAL", LAL, 126), "LAL"),
        ("0046400414", "1965-04-23", ("BOS", BOS, 112), ("LAL", LAL, 99), "BOS"),
        ("0046400415", "1965-04-25", ("LAL", LAL, 96), ("BOS", BOS, 129), "BOS"),
    ]
    for game in games:
        _add_game(rows, *game)

    series = _series_for_rows("1964-65", rows)
    lakers_celtics = _series_for_pair(series, BOS, LAL)

    assert len(lakers_celtics) == 2


def test_reconciliation_does_not_merge_when_combined_wins_do_not_reach_target():
    rows = []
    games = [
        ("0046400301", "1965-04-18", ("LAL", LAL, 110), ("BOS", BOS, 142), "BOS"),
        ("0046400412", "1965-04-19", ("LAL", LAL, 123), ("BOS", BOS, 129), "BOS"),
        ("0046400413", "1965-04-21", ("BOS", BOS, 105), ("LAL", LAL, 126), "LAL"),
        ("0046400414", "1965-04-23", ("BOS", BOS, 112), ("LAL", LAL, 99), "BOS"),
    ]
    for game in games:
        _add_game(rows, *game)

    series = _series_for_rows("1964-65", rows)
    lakers_celtics = _series_for_pair(series, BOS, LAL)

    assert len(lakers_celtics) == 2


def test_reconciliation_does_not_merge_when_combined_games_exceed_max():
    rows = []
    games = [
        ("0046400301", "1965-04-18", ("LAL", LAL, 110), ("BOS", BOS, 142), "BOS"),
        ("0046400412", "1965-04-19", ("LAL", LAL, 123), ("BOS", BOS, 129), "BOS"),
        ("0046400413", "1965-04-21", ("BOS", BOS, 105), ("LAL", LAL, 126), "LAL"),
        ("0046400414", "1965-04-23", ("BOS", BOS, 112), ("LAL", LAL, 99), "BOS"),
        ("0046400415", "1965-04-25", ("LAL", LAL, 96), ("BOS", BOS, 129), "BOS"),
        ("0046400416", "1965-04-27", ("BOS", BOS, 95), ("LAL", LAL, 101), "LAL"),
        ("0046400417", "1965-04-29", ("LAL", LAL, 98), ("BOS", BOS, 104), "BOS"),
        ("0046400418", "1965-05-01", ("BOS", BOS, 99), ("LAL", LAL, 103), "LAL"),
    ]
    for game in games:
        _add_game(rows, *game)

    series = _series_for_rows("1964-65", rows)
    lakers_celtics = _series_for_pair(series, BOS, LAL)

    assert len(lakers_celtics) == 2


def test_reconciliation_does_not_merge_legitimate_rematch_without_valid_completion():
    rows = []
    games = [
        ("0046600204", "1967-04-09", ("PHL", PHL, 117), ("BOS", BOS, 121), "BOS"),
        ("0046600321", "1967-04-20", ("BOS", BOS, 113), ("PHL", PHL, 127), "PHL"),
        ("0046600322", "1967-04-22", ("PHL", PHL, 107), ("BOS", BOS, 102), "PHL"),
        ("0046600323", "1967-04-25", ("BOS", BOS, 104), ("PHL", PHL, 115), "PHL"),
        ("0046600325", "1967-05-10", ("BOS", BOS, 116), ("PHL", PHL, 140), "PHL"),
    ]
    for game in games:
        _add_game(rows, *game)

    series = _series_for_rows("1966-67", rows)
    celtics_sixers = _series_for_pair(series, BOS, PHL)

    assert len(celtics_sixers) == 2
