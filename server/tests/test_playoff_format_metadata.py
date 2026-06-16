import pytest

from server.services import playoffs


def _series(series_key, round_num, teams, winner, games=None):
    winner_team_abbreviation = teams[0][1] if winner == teams[0][0] else teams[1][1]
    games = games or [
        {
            "gameId": f"{series_key}-1",
            "date": f"2000-04-{round_num:02d}",
            "round": round_num,
            "roundName": playoffs.get_round_name(round_num),
            "homeTeam": {"id": teams[0][0], "tricode": teams[0][1], "name": teams[0][1], "score": 100},
            "awayTeam": {"id": teams[1][0], "tricode": teams[1][1], "name": teams[1][1], "score": 90},
            "winnerTeamId": winner,
            "winnerTeamAbbreviation": winner_team_abbreviation,
        }
    ]
    return {
        "seriesKey": series_key,
        "round": round_num,
        "roundName": playoffs.get_round_name(round_num),
        "teams": [
            {"id": teams[0][0], "tricode": teams[0][1], "name": teams[0][1]},
            {"id": teams[1][0], "tricode": teams[1][1], "name": teams[1][1]},
        ],
        "wins": {winner: 1},
        "winnerTeamId": winner,
        "winnerTeamTricode": teams[0][1],
        "gameCount": len(games),
        "games": games,
    }


def test_1954_round_robin_format_marks_dynamic_finals_round():
    mnl = 1610612747
    syr = 1610612755
    bracket = playoffs.enrich_playoff_bracket_response(
        "1953-54",
        [
            _series("R1-a", 1, [(1610612738, "BOS"), (1610612752, "NYK")], 1610612738),
            _series("R1-b", 1, [(mnl, "MNL"), (1610612758, "ROC")], mnl),
            _series("R2-final", 2, [(mnl, "MNL"), (syr, "SYR")], mnl),
        ],
    )

    assert bracket["format"]["era"] == "six-team-round-robin"
    assert bracket["format"]["bracketType"] == "round-robin-plus-finals"
    assert bracket["format"]["finalsRound"] == 2
    assert bracket["series"][-1]["isFinals"] is True
    assert bracket["series"][-1]["roundName"] == "NBA Finals"


def test_1951_to_1953_formats_have_dedicated_metadata():
    for year in (1951, 1952, 1953):
        playoff_format = playoffs.get_playoff_format(f"{year - 1}-{str(year)[-2:]}")

        assert playoff_format["era"] == f"{year}-two-division-eight-team"
        assert playoff_format["bracketType"] == "multi-division"
        assert playoff_format["supportsExactBracket"] is True
        assert playoff_format["notes"]


@pytest.mark.parametrize("season", [None, "", "2023", "2023-", "-24", "2023-2024", "abcd-ef"])
def test_playoff_end_year_rejects_invalid_season_format(season):
    with pytest.raises(ValueError, match="Expected YYYY-YY|Season must be a string"):
        playoffs.get_playoff_end_year(season)


def test_1951_to_1953_series_targets_match_era_format():
    for year in (1951, 1952, 1953):
        assert playoffs.get_target_wins(year, 1, False) == 2
        assert playoffs.get_target_wins(year, 2, False) == 3
        assert playoffs.get_target_wins(year, 3, True) == 4


def test_1984_first_round_uses_best_of_five_target_wins():
    bracket = playoffs.enrich_playoff_bracket_response(
        "1983-84",
        [
            _series(
                "R1-bos-was",
                1,
                [(1610612738, "BOS"), (1610612764, "WAS")],
                1610612738,
            ),
            _series(
                "R4-bos-lal",
                4,
                [(1610612738, "BOS"), (1610612747, "LAL")],
                1610612738,
            ),
        ],
    )

    first_round = next(series for series in bracket["series"] if series["round"] == 1)
    finals = next(series for series in bracket["series"] if series["isFinals"])

    assert bracket["format"]["era"] == "sixteen-team-best-of-five-first-round"
    assert first_round["targetWins"] == 3
    assert finals["targetWins"] == 4


def test_metadata_includes_groups_rounds_and_advancement_edges():
    bos = 1610612738
    nyk = 1610612752
    lal = 1610612747
    first = _series("R1-bos-nyk", 1, [(bos, "BOS"), (nyk, "NYK")], bos)
    final = _series("R2-bos-lal", 2, [(bos, "BOS"), (lal, "LAL")], bos)

    bracket = playoffs.enrich_playoff_bracket_response("1950-51", [first, final])

    assert bracket["format"]["era"] == "1951-two-division-eight-team"
    assert bracket["groups"]
    assert bracket["rounds"] == [
        {"round": 1, "label": "First Round", "sortOrder": 1, "defaultRevealed": True},
        {"round": 2, "label": "NBA Finals", "sortOrder": 2, "defaultRevealed": False},
    ]
    assert bracket["edges"] == [
        {
            "sourceSeriesKey": "R1-bos-nyk",
            "targetSeriesKey": "R2-bos-lal",
            "winnerTeamId": bos,
        }
    ]
