import json
from pathlib import Path
from urllib.parse import quote

import pytest

from server.services import game_data
from server.utils.stat_events import SHOT_MEASURES, VIDEO_MEASURES, stat_events

FIXTURES = Path(__file__).resolve().parents[2] / "docs" / "verification" / "stat-event-links-2026-09-29" / "games"
FIXTURE_PATHS = sorted(FIXTURES.glob("*.json"))
OTHER_MEASURES = tuple(m for m in VIDEO_MEASURES if m not in SHOT_MEASURES)
# Characters JavaScript's encodeURI leaves unescaped, besides letters and digits.
ENCODE_URI_SAFE = ";,/?:@&=+$-_.!~*'()#"
NEVER_LINKED = {"MIN", "FG_PCT", "FG3_PCT", "FTM", "FTA", "FT_PCT", "PF", "PTS", "PLUS_MINUS"}


def flags(game_id, video_available_flag, wh_status=1, overtime_periods=0):
    events = stat_events(game_id, wh_status, video_available_flag, overtime_periods)
    return None if events is None else events["measures"]


def both(shot, other):
    return {**{m: shot for m in SHOT_MEASURES if shot}, **{m: other for m in OTHER_MEASURES if other}} or None


# One case per row of the issue's table, at its boundaries.

@pytest.mark.parametrize("game_id", ["0021400001", "0022500868", "0041400401", "0052400101", "0032300001", "0062500001", "0011700001", "0012500001"])
def test_video_era_games_with_video_link_shots_both_ways(game_id):
    assert flags(game_id, 1) == both(3, 1)


@pytest.mark.parametrize("game_id", ["0011400001", "0011500001", "0011600001"])
def test_early_video_era_preseason_with_video_links_video_only(game_id):
    assert flags(game_id, 1) == both(1, 1)


@pytest.mark.parametrize("game_id", ["0021400001", "0022500868", "0041400401", "0011700001", "0012500001"])
def test_video_era_games_without_video_link_shot_charts_only(game_id):
    assert flags(game_id, 0) == both(2, 0)


@pytest.mark.parametrize("game_id", ["0011400001", "0011600001"])
def test_early_video_era_preseason_without_video_has_no_links(game_id):
    assert flags(game_id, 0) is None


@pytest.mark.parametrize("game_id", ["0020100001", "0020500001", "0021300001", "0041300401"])
@pytest.mark.parametrize("video_available_flag", [0, 1])
def test_shot_chart_era_links_shot_charts_only(game_id, video_available_flag):
    assert flags(game_id, video_available_flag) == both(2, 0)


@pytest.mark.parametrize("game_id", ["0010100001", "0011300001"])
@pytest.mark.parametrize("video_available_flag", [0, 1])
def test_preseason_before_video_era_has_no_links(game_id, video_available_flag):
    assert flags(game_id, video_available_flag) is None


@pytest.mark.parametrize("game_id", ["0020000001", "0029600001", "0024600001", "0049900401"])
@pytest.mark.parametrize("video_available_flag", [0, 1])
def test_games_before_shot_charts_have_no_links(game_id, video_available_flag):
    assert flags(game_id, video_available_flag) is None


@pytest.mark.parametrize("wh_status", [0, 2, None, "1", "1.0", True, 1.9, 0.9, "Infinity", float("inf"), float("nan"), {}, [1], {"value": 1}])
def test_games_without_warehouse_status_one_have_no_links(wh_status):
    assert flags("0022500868", 1, wh_status=wh_status) is None


def test_warehouse_status_one_point_zero_is_strictly_one():
    # JavaScript has one number type, so 1.0 === 1.
    assert flags("0022500868", 1, wh_status=1.0) == both(3, 1)


@pytest.mark.parametrize("game_id", ["1022500001", "2022500001", "1522500001", "123", "", None, "00225000a1"])
def test_non_nba_or_malformed_game_ids_have_no_links(game_id):
    assert flags(game_id, 1) is None


@pytest.mark.parametrize("overtime_periods, end_range", [(0, 28800), (1, 31800), (3, 37800), (-1, 28800)])
def test_end_range_covers_overtime_periods(overtime_periods, end_range):
    assert stat_events("0020500001", 1, 0, overtime_periods)["endRange"] == end_range


@pytest.mark.parametrize("game_id, season, season_type", [
    ("0062500001", "2025-26", ""),
    ("0052400101", "2024-25", "PlayIn"),
    ("0032300001", "2023-24", "All Star"),
    ("0012500001", "2025-26", "Pre Season"),
    ("0042300405", "2023-24", "Playoffs"),
    ("0022500868", "2025-26", "Regular Season"),
], ids=["cup_final", "play_in", "all_star", "preseason", "playoffs", "regular"])
def test_season_and_season_type_come_from_the_game_id(game_id, season, season_type):
    events = stat_events(game_id, 1, 1, 0)
    assert (events["season"], events["seasonType"]) == (season, season_type)


@pytest.mark.parametrize("video_available_flag", [1, 1.0, True, "1", " 1 ", "1.0", "1e0"])
def test_video_flag_is_coerced_like_nba_com(video_available_flag):
    assert flags("0022500868", video_available_flag) == both(3, 1)


@pytest.mark.parametrize("video_available_flag", [
    None, 0, False, 1.9, "1.9", 0.9, "", "abc", "1_0", "Infinity", "NaN", float("inf"), float("nan"), {}, [1], {"flag": 1}, b"1",
])
def test_other_video_flags_leave_shot_charts_only(video_available_flag):
    assert flags("0022500868", video_available_flag) == both(2, 0)


# Fixtures recorded from NBA.com box scores

def event_url(game_id, team_id, events, measure, person_id=None):
    # Mirrors NBA.com's builder: sorted keys, encodeURI values, empty CFID/CFPARAMS.
    params = {
        "CFID": "", "CFPARAMS": "", "ContextMeasure": measure, "EndPeriod": 0, "EndRange": events["endRange"],
        "GameID": game_id, "RangeType": 0, "Season": events["season"], "SeasonType": events["seasonType"],
        "StartPeriod": 0, "StartRange": 0, "TeamID": team_id, "flag": events["measures"][measure],
        "sct": "plot", "section": "game",
    }
    if person_id:
        params["PlayerID"] = person_id
    encoded = (f"{key}={quote(str(params[key]), safe=ENCODE_URI_SAFE)}" for key in sorted(params))
    return "https://www.nba.com/stats/events/?" + "&".join(encoded)


def test_every_issue_game_has_a_fixture():
    expected = {"0022500868", "0021400001", "0021300001", "0020500001", "0020000001", "0011600001",
                "0011700001", "0012500001", "0052400101", "0032300001", "0062500001"}
    assert {path.stem for path in FIXTURE_PATHS} == expected


@pytest.mark.parametrize("path", FIXTURE_PATHS, ids=lambda path: path.stem)
def test_fixture_stat_events_match_the_rule(path):
    fixture = json.loads(path.read_text())
    inputs = fixture["summaryInputs"]
    events = stat_events(fixture["gameId"], inputs["whStatus"], inputs["videoAvailableFlag"], inputs["overtimePeriods"])
    assert events == fixture["statEvents"]

    measures = set(events["measures"]) if events else set()
    for kind in ("player", "team"):
        cells = fixture["cells"][kind]
        assert set(cells["linked"]) == measures
        assert not set(cells["unlinked"]) & measures
        assert NEVER_LINKED - {"MIN"} <= set(cells["unlinked"])
    if events is None:
        assert fixture["urls"] == {"player": [], "team": []}
        return

    assert fixture["urls"]["player"] and fixture["urls"]["team"]
    for link in fixture["urls"]["player"]:
        assert link["value"] > 0
        assert event_url(fixture["gameId"], link["teamId"], events, link["measure"], link["personId"]) == link["url"]
    assert {link["measure"] for link in fixture["urls"]["team"]} == measures
    for link in fixture["urls"]["team"]:
        assert event_url(fixture["gameId"], link["teamId"], events, link["measure"]) == link["url"]


def test_contract_urls_match_the_rule():
    contract = json.loads((FIXTURES.parent / "contract.json").read_text())
    inputs = contract["summaryInputs"]
    events = stat_events(contract["gameId"], inputs["whStatus"], inputs["videoAvailableFlag"], inputs["overtimePeriods"])
    assert events == contract["statEvents"]
    for link in contract["urls"].values():
        assert event_url(contract["gameId"], link["teamId"], events, link["measure"], link.get("personId")) == link["url"]


# Summary inputs retained with the boxscore

def test_summary_inputs_use_the_latest_period():
    game = {"whStatus": 1, "videoAvailableFlag": 0, "period": 5}
    assert game_data.v3_stat_event_inputs(game) == game_data.StatEventInputs(1, 0, 1)
    assert game_data.v3_stat_event_inputs({**game, "period": 4}).overtime_periods == 0


def test_summary_inputs_fall_back_to_team_periods_without_a_period():
    periods = [{"period": number} for number in range(1, 7)]
    game = {"whStatus": 1, "videoAvailableFlag": 1, "homeTeam": {"periods": periods}, "awayTeam": {"periods": periods[:4]}}
    assert game_data.v3_stat_event_inputs(game) == game_data.StatEventInputs(1, 1, 2)
    assert game_data.v3_stat_event_inputs({"period": None}) == game_data.StatEventInputs(None, None, 0)


def test_summary_inputs_keep_raw_warehouse_status_and_video_flag():
    game = {"whStatus": "1", "videoAvailableFlag": 1.9, "period": 4.0}
    assert game_data.v3_stat_event_inputs(game) == game_data.StatEventInputs("1", 1.9, 0)


@pytest.mark.parametrize("game", [
    {"period": 5.5},
    {"period": "5"},
    {"period": "Infinity"},
    {"period": float("inf")},
    {"period": True},
    {"period": [5]},
    {"homeTeam": {"periods": [{"period": 1}, {"period": "5"}]}},
    {"homeTeam": {"periods": [{"period": 1}, "5"]}},
    {"homeTeam": {"periods": [{"period": 1}, {}]}},
    {"homeTeam": {"periods": 5}},
    {"homeTeam": "TOR"},
], ids=["fraction", "string", "infinity_string", "infinity", "bool", "list",
        "string_row_period", "non_dict_row", "row_without_period", "non_list_rows", "non_dict_team"])
def test_malformed_period_counts_are_rejected_rather_than_guessed(game):
    with pytest.raises((ValueError, AttributeError)):
        game_data.v3_stat_event_inputs(game)
