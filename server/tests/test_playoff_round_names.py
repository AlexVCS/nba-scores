"""Season labels, actual source anomalies, and agreement across playoff APIs."""

import json
from collections import Counter
from pathlib import Path

import pandas as pd
import pytest

from server.services import playoffs


FIXTURES = Path(__file__).resolve().parents[2] / "scripts/fixtures/bracket-spacing"


def _fixture_games(season):
    response = json.loads((FIXTURES / f"{season}.json").read_text())
    return list({game["gameId"]: game for series in response["series"] for game in series["games"]}.values())


def _bracket(season, games):
    assigned = playoffs.apply_rounds_to_games(games, season)
    reconciled = playoffs.reconcile_duplicate_matchup_rounds(season, assigned)
    return playoffs.enrich_playoff_bracket_response(season, playoffs.derive_playoff_series(reconciled))


def _early_games(season):
    fixture = Path(__file__).parent / "fixtures/early_playoff_games.json"
    rows = json.loads(fixture.read_text())["seasons"][season]
    games = []
    expected = {}
    for game_id, date, home, away, winner, stage in rows:
        games.append({
            "gameId": game_id, "date": date,
            "homeTeam": {"id": home, "tricode": str(home), "name": str(home)},
            "awayTeam": {"id": away, "tricode": str(away), "name": str(away)},
            "winnerTeamId": winner,
        })
        expected[game_id] = stage
    return games, expected


def _remap_games(games, id_style):
    team_ids = sorted({game[side]["id"] for game in games for side in ("homeTeam", "awayTeam")})
    remap = {team_id: 9000 + index * 13 for index, team_id in enumerate(reversed(team_ids))}
    game_ids = {}
    result = []
    for index, game in enumerate(games):
        game_id = game["gameId"]
        if id_style == "opaque":
            game_id = f"fixture-game-{index}"
        elif id_style == "misleading":
            # Valid-looking NBA IDs falsely encode every game as opening round.
            game_id = f"00499001{index // 7}{index % 7 + 1}"
        game_ids[game["gameId"]] = game_id
        result.append({
            "gameId": game_id, "date": game["date"],
            **{
                side: {
                    "id": remap[game[side]["id"]],
                    "name": f"Team {remap[game[side]['id']]}",
                    "tricode": f"T{remap[game[side]['id']]}",
                }
                for side in ("homeTeam", "awayTeam")
            },
            "winnerTeamId": remap[game["winnerTeamId"]],
        })
    return list(reversed(result)), game_ids


@pytest.mark.parametrize("season", ["1946-47", "1949-50"])
@pytest.mark.parametrize("id_style", ["original", "opaque", "misleading"])
def test_early_stages_follow_results_without_franchise_or_game_id_lookup(season, id_style):
    games, expected = _early_games(season)
    remapped, game_ids = _remap_games(games, id_style)
    bracket = _bracket(season, remapped)
    actual = {
        game["gameId"]: series["round"]
        for series in bracket["series"] for game in series["games"]
    }
    assert actual == {game_ids[game_id]: stage for game_id, stage in expected.items()}
    assert bracket["format"]["finalsRound"] == (4 if season == "1949-50" else 3)


@pytest.mark.parametrize("season", ["1946-47", "1949-50"])
def test_isolated_early_matchup_does_not_guess_a_stage_from_franchise_identity(season):
    games, expected = _early_games(season)
    finals = [game for game in games if expected[game["gameId"]] == max(expected.values())]
    for sample in [finals, _remap_games(finals, "opaque")[0]]:
        bracket = _bracket(season, sample)
        assert bracket["series"][0]["round"] == 0
        assert bracket["series"][0]["roundName"] == "Round not determined"
        assert bracket["format"]["finalsRound"] is None


@pytest.mark.parametrize(
    "season,expected",
    [
        ("1946-47", ["Quarterfinals", "Semifinals", "BAA Finals"]),
        ("1947-48", ["Quarterfinals", "Semifinals", "BAA Finals"]),
        ("1948-49", ["Division Semifinals", "Division Finals", "BAA Finals"]),
        ("1949-50", ["Division Semifinals", "Division Finals", "NBA Semifinals", "NBA Finals"]),
        ("1953-54", ["Division Round Robin", "Division Finals", "NBA Finals"]),
        ("1960-61", ["Division Semifinals", "Division Finals", "NBA Finals"]),
        ("1969-70", ["Division Semifinals", "Division Finals", "NBA Finals"]),
        ("1970-71", ["Conference Semifinals", "Conference Finals", "NBA Finals"]),
        ("1973-74", ["Conference Semifinals", "Conference Finals", "NBA Finals"]),
        ("1974-75", ["First Round", "Conference Semifinals", "Conference Finals", "NBA Finals"]),
        ("2025-26", ["First Round", "Conference Semifinals", "Conference Finals", "NBA Finals"]),
    ],
)
def test_historical_naming_boundaries(season, expected):
    assert list(playoffs.get_round_names(season).values()) == expected


@pytest.mark.parametrize("year", range(1947, 2027))
def test_every_supported_year_has_one_championship_and_no_premature_finals(year):
    season = f"{year - 1}-{year % 100:02d}"
    rounds = playoffs.get_round_names(season)
    championship = max(rounds)
    assert rounds[championship] == ("BAA Finals" if year <= 1949 else "NBA Finals")
    for earlier in rounds:
        if earlier < championship:
            assert playoffs.get_finals_round([{"round": earlier}], season) is None


@pytest.mark.parametrize(
    "season,counts",
    [
        ("1949-50", [6, 3, 1, 1]),
        ("1952-53", [4, 2, 1]),
        ("1953-54", [6, 2, 1]),
        ("1962-63", [2, 2, 1]),
        ("1974-75", [2, 4, 2, 1]),
        ("1977-78", [4, 4, 2, 1]),
        ("1983-84", [8, 4, 2, 1]),
        ("2001-02", [8, 4, 2, 1]),
        ("2002-03", [8, 4, 2, 1]),
        ("2025-26", [8, 4, 2, 1]),
    ],
)
def test_real_source_games_preserve_historical_stages_and_byes(season, counts):
    games = _fixture_games(season)
    bracket = _bracket(season, games)
    expected = dict(zip(playoffs.get_round_names(season).values(), counts))
    assert Counter(series["roundName"] for series in bracket["series"]) == expected
    nested = [game for series in bracket["series"] for game in series["games"]]
    assert Counter(game["gameId"] for game in nested) == Counter(game["gameId"] for game in games)
    labels = {item["round"]: item["label"] for item in bracket["rounds"]}
    for series in bracket["series"]:
        assert series["roundName"] == labels[series["round"]]
        assert all(game["roundName"] == series["roundName"] for game in series["games"])


def test_1954_pool_games_are_separate_from_later_series_between_same_opponents():
    bracket = _bracket("1953-54", _fixture_games("1953-54"))
    pool = [series for series in bracket["series"] if series["round"] == 1]
    division_finals = [series for series in bracket["series"] if series["round"] == 2]
    assert sum(series["gameCount"] for series in pool) == 11
    assert sorted(series["gameCount"] for series in division_finals) == [2, 3]
    assert all(series["targetWins"] is None for series in pool)
    assert all(series["targetWins"] == 2 for series in division_finals)
    for final in division_finals:
        pair = playoffs.get_series_team_id_pair(final)
        assert any(playoffs.get_series_team_id_pair(series) == pair for series in pool)
        assert all(game["date"] >= "1954-03-24" for game in final["games"])


def test_1954_pool_and_repeat_opponents_do_not_depend_on_team_or_game_ids():
    games = _fixture_games("1953-54")
    original = _bracket("1953-54", games)
    remapped, game_ids = _remap_games(games, "opaque")
    bracket = _bracket("1953-54", remapped)
    actual = {
        game["gameId"]: series["round"]
        for series in bracket["series"] for game in series["games"]
    }
    assert actual == {
        game_ids[game["gameId"]]: series["round"]
        for series in original["series"] for game in series["games"]
    }
    assert Counter(series["round"] for series in bracket["series"]) == {1: 6, 2: 2, 3: 1}


@pytest.mark.parametrize("stage", [1, 2, 3, 4])
def test_partial_modern_response_preserves_its_encoded_stage(stage):
    game = {**_fixture_games("2025-26")[0], "gameId": f"0042500{stage}11"}
    bracket = _bracket("2025-26", [game])
    series = bracket["series"][0]
    assert series["round"] == stage
    assert series["roundName"] == playoffs.get_round_name(stage, "2025-26")
    assert series["isFinals"] is (stage == 4)
    assert bracket["format"]["finalsRound"] == (4 if stage == 4 else None)


@pytest.mark.parametrize("isolated_id,expected_stage", [("0042500221", 2), ("unencoded", 0)])
def test_complete_path_does_not_supply_evidence_for_disconnected_partial_series(isolated_id, expected_stage):
    games = []
    for stage in range(1, 5):
        games.append({
            "gameId": f"0042500{stage}01", "date": f"2026-04-{stage:02d}",
            "homeTeam": {"id": 1000, "name": "Winner", "tricode": "WIN", "score": 100},
            "awayTeam": {"id": 2000 + stage, "name": f"Opponent {stage}", "tricode": f"O{stage}", "score": 90},
            "winnerTeamId": 1000,
        })
    games.append({
        "gameId": isolated_id, "date": "2026-04-02",
        "homeTeam": {"id": 3000, "name": "Other winner", "tricode": "OTH", "score": 100},
        "awayTeam": {"id": 3001, "name": "Other opponent", "tricode": "OPP", "score": 90},
        "winnerTeamId": 3000,
    })
    assigned = playoffs.apply_rounds_to_games(list(reversed(games)), "2025-26")
    stages = {game["gameId"]: game["round"] for game in assigned}
    assert stages[isolated_id] == expected_stage
    assert [stages[f"0042500{stage}01"] for stage in range(1, 5)] == [1, 2, 3, 4]


def test_missing_opposite_conference_final_does_not_shift_known_earlier_stages():
    matchups = [
        ("0042500101", "2026-04-01", 1000, 2000),
        ("0042500201", "2026-04-03", 1000, 2001),
        ("0042500301", "2026-04-05", 1000, 2002),
        ("0042500401", "2026-04-07", 1000, 3000),
        ("0042500111", "2026-04-02", 3000, 4000),
        ("0042500211", "2026-04-04", 3000, 4001),
    ]
    games = [
        {
            "gameId": game_id, "date": date,
            "homeTeam": {"id": winner, "name": str(winner), "tricode": str(winner), "score": 100},
            "awayTeam": {"id": loser, "name": str(loser), "tricode": str(loser), "score": 90},
            "winnerTeamId": winner,
        }
        for game_id, date, winner, loser in matchups
    ]
    assigned = playoffs.apply_rounds_to_games(games, "2025-26")
    assert {game["gameId"]: game["round"] for game in assigned} == {
        "0042500101": 1, "0042500201": 2, "0042500301": 3, "0042500401": 4,
        "0042500111": 1, "0042500211": 2,
    }


def test_unencoded_bye_alignment_does_not_promote_distant_ancestor_series():
    games = [{**game, "gameId": f"uncoded-{index}"} for index, game in enumerate(_fixture_games("1974-75"))]
    bracket = _bracket("1974-75", games)
    assert Counter(series["round"] for series in bracket["series"]) == {1: 2, 2: 4, 3: 2, 4: 1}


@pytest.mark.parametrize("season", ["1949-50", "1953-54", "1962-63", "1974-75"])
def test_all_api_views_share_resolved_game_labels(monkeypatch, season):
    rows = []
    for game in _fixture_games(season):
        for side, opponent, separator in [("homeTeam", "awayTeam", "vs."), ("awayTeam", "homeTeam", "@")]:
            team = game[side]
            won = team["id"] == game["winnerTeamId"]
            rows.append({
                "GAME_ID": game["gameId"], "GAME_DATE": game["date"],
                "TEAM_ID": team["id"], "TEAM_NAME": team["name"], "TEAM_ABBREVIATION": team["tricode"],
                "MATCHUP": f"{team['tricode']} {separator} {game[opponent]['tricode']}",
                "WL": "W" if won else "L", "PTS": 100 if won else 90,
            })
    monkeypatch.setattr(playoffs, "fetch_playoff_team_games_df", lambda _: pd.DataFrame(rows))
    standalone = playoffs.get_normalized_playoff_games(season)
    series_only = playoffs.get_playoff_series(season)
    full = playoffs.get_playoff_games_and_series(season)
    expected = {game["gameId"]: (game["round"], game["roundName"]) for game in standalone["games"]}
    for response in [series_only, full]:
        for series in response["series"]:
            assert all(expected[game["gameId"]] == (series["round"], series["roundName"]) for game in series["games"])
    assert full["games"] == standalone["games"]


def test_1986_mistyped_source_codes_cannot_put_a_semifinal_back_in_first_round():
    # Boston/Atlanta has two code-1 games, two code-2 games and one malformed ID.
    # Both participants already won opening series, which resolves that ambiguity.
    fixture = Path(__file__).parent / "fixtures/playoff_games_1986.json"
    bracket = _bracket("1985-86", json.loads(fixture.read_text()))
    assert Counter(series["roundName"] for series in bracket["series"]) == {
        "First Round": 2, "Conference Semifinals": 1,
    }
    assert bracket["format"]["finalsRound"] is None
