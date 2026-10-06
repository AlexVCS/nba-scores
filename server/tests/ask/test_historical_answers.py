"""Answer-accuracy regressions for old seasons (ADR 0009 dry run, part A).

Fixtures under ``fixtures/historical`` are trimmed stats.nba responses: the
scoreboards and boxscores of three old dates, and playoff team game logs.
"""

import json
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from server.ask.models.common import TeamRef
from server.ask.models.request import BoxscoreStatRequest
from server.ask.resolvers import games, playoffs, resolve
from server.ask.resolvers.errors import NotFoundError
from server.ask.resolvers.stats import STATS, minutes_to_seconds, stat_value
from server.services import nba_stats_client
from server.services import playoffs as playoffs_service
from server.tests.ask.test_resolvers_support import (  # noqa: F401
    FakeBoxscores,
    FakeFinder,
    FakeScoreboards,
    assert_fits_answer,
    clear_player_games,
)

FIXTURES = Path(__file__).parent / "fixtures" / "historical"
OLD = json.loads((FIXTURES / "old-boxscores.json").read_text())
PLAYOFF_LOGS = json.loads((FIXTURES / "playoff-team-games.json").read_text())

WILT, MALONE, BIRD = 76375, 77449, 1449
WARRIORS, SIXERS, CELTICS = 1610612744, 1610612755, 1610612738
HAWKS, BULLS, LAKERS, BUCKS, ROCKETS, ROYALS, PISTONS = (
    1610612737, 1610612741, 1610612747, 1610612749, 1610612745, 1610612758, 1610612765)


def _summary_unavailable(game_id, **kwargs):
    raise nba_stats_client.UpstreamUnavailableError("BoxScoreSummaryV3", "Timeout", 10)


def _schedule_unavailable(season, *args, **kwargs):
    raise nba_stats_client.UpstreamUnavailableError("ScheduleLeagueV2", "Timeout", 10)


@pytest.fixture
def old_games(monkeypatch, clear_player_games):
    boards = FakeScoreboards(OLD["scoreboards"])
    boxes = FakeBoxscores(OLD["boxscores"])
    # stats.nba has no player game logs before 1983-84: the finder is empty for
    # Chamberlain and Malone. It does hold Bird's 1988 playoff game.
    finder = FakeFinder({(str(BIRD), "05/22/1988"): [{
        "PLAYER_ID": BIRD, "PLAYER_NAME": "Larry Bird", "TEAM_ID": CELTICS, "GAME_ID": "0048700060",
        "GAME_DATE": "1988-05-22"}]})
    monkeypatch.setattr(nba_stats_client, "fetch_scoreboard_v3", boards)
    monkeypatch.setattr(nba_stats_client, "fetch_boxscore_traditional", boxes)
    monkeypatch.setattr(nba_stats_client, "fetch_boxscore_summary_v3", _summary_unavailable)
    monkeypatch.setattr(nba_stats_client, "fetch_league_game_finder", finder)
    monkeypatch.setattr(nba_stats_client, "fetch_schedule_league_v2", _schedule_unavailable)
    return boxes


def player_request(player_id, name, day, stat):
    return BoxscoreStatRequest.model_validate({
        "intent": "boxscore_stat", "scope": "player", "stat": {"stat": stat, "aggregation": "total"},
        "game": {"date": day}, "player": {"player_id": player_id, "name": name}})


def player_value(player_id, name, day, stat):
    output = resolve(player_request(player_id, name, day, stat))
    assert_fits_answer(output, "boxscore_stat")
    return output.result


# Old boxscores ---------------------------------------------------------------


def test_player_without_a_game_log_is_found_in_the_dates_boxscore(old_games):
    # unseen-three-boxscore_stat-05: the 100-point game. Was player_did_not_play.
    result = player_value(WILT, "Wilt Chamberlain", "1962-03-02", "rebounds")
    line = result.player_line
    assert (line.status, line.player.player_id, line.team.team_id) == ("played", WILT, WARRIORS)
    assert [(v.stat, v.value) for v in line.values] == [("rebounds", 25)]
    assert result.game.date == date(1962, 3, 2)


def test_pre_1983_playoff_game_is_found_in_the_boxscore(old_games):
    # unseen-three-boxscore_stat-17: 1983 Finals Game 4. Was player_did_not_play.
    result = player_value(MALONE, "Moses Malone", "1983-05-31", "defensive_rebounds")
    line = result.player_line
    assert (line.player.player_id, line.team.team_id) == (MALONE, SIXERS)
    assert [(v.stat, v.value) for v in line.values] == [("defensive_rebounds", 15)]


def test_pre_1983_dates_do_not_ask_for_a_game_log(old_games, monkeypatch):
    def finder_unavailable(*args, **kwargs):
        raise nba_stats_client.UpstreamUnavailableError("LeagueGameFinder", "Timeout", 10)

    monkeypatch.setattr(nba_stats_client, "fetch_league_game_finder", finder_unavailable)
    game, team = games.find_player_game(WILT, date(1962, 3, 2))
    assert (game.date, team.team_id) == (date(1962, 3, 2), WARRIORS)


def test_whole_minutes_are_read(old_games):
    # unseen-three-boxscore_stat-14: stats.nba reports "47" before 1996-97. Was no_record.
    result = player_value(BIRD, "Larry Bird", "1988-05-22", "minutes")
    (value,) = result.player_line.values
    assert (value.value, value.display) == (47.0, "47:00")
    assert result.player_line.team.team_id == CELTICS


@pytest.mark.parametrize("text,seconds", [("47", 2820), ("0", 0), ("47:00", 2820), ("PT34M12.00S", 2052), ("", None), ("DNP", None)])
def test_minutes_formats(text, seconds):
    assert minutes_to_seconds(text) == seconds


def test_player_absent_from_old_boxscores_is_no_record_not_did_not_play(old_games):
    # No game log exists for the era, so absence cannot be asserted.
    with pytest.raises(NotFoundError) as error:
        resolve(player_request(MALONE, "Moses Malone", "1962-03-02", "points"))
    assert (error.value.code, error.value.reason) == ("no_record", "no_player_game_log_before_1983")


def test_old_date_without_games_is_no_record(old_games):
    with pytest.raises(NotFoundError) as error:
        games.find_player_game(WILT, date(1962, 3, 3))
    assert error.value.code == "no_record"


@pytest.mark.parametrize("stat", ["defensive_rebounds", "offensive_rebounds", "steals", "blocks", "turnovers",
                                  "three_pointers", "plus_minus"])
def test_statistic_not_kept_in_1962_is_not_recorded_rather_than_zero(old_games, stat):
    # The source fills these with 0 for every player in the game.
    with pytest.raises(NotFoundError) as error:
        resolve(player_request(WILT, "Wilt Chamberlain", "1962-03-02", stat))
    assert (error.value.code, error.value.reason) == ("no_record", "stat_not_recorded")


def test_old_stat_line_marks_unrecorded_values_missing(old_games):
    values = {v.stat: v.value for v in player_value(WILT, "Wilt Chamberlain", "1962-03-02", "stat_line").player_line.values}
    assert (values["points"], values["rebounds"], values["minutes"], values["field_goals"]) == (100, 25, 48.0, 36)
    assert [values[key] for key in ("steals", "blocks", "turnovers", "three_pointers", "plus_minus")] == [None] * 5


def test_minutes_zero_for_everyone_were_not_recorded(old_games):
    # Detroit at Cincinnati the same night: every player's minutes are "0".
    with pytest.raises(NotFoundError) as error:
        resolve(player_request(76191, "Arlen Bockhorn", "1962-03-02", "minutes"))
    assert (error.value.code, error.value.reason) == ("no_record", "stat_not_recorded")
    assert player_value(76191, "Arlen Bockhorn", "1962-03-02", "rebounds").player_line.values[0].value == 3


def test_recorded_1983_values_and_missing_plus_minus(old_games):
    values = {v.stat: v.value for v in player_value(MALONE, "Moses Malone", "1983-05-31", "stat_line").player_line.values}
    assert (values["rebounds"], values["points"]) == (23, 24)
    assert values["plus_minus"] is None and values["steals"] is not None


def test_leaders_and_team_totals_refuse_unrecorded_statistics(old_games):
    base = {"intent": "boxscore_stat", "game": {"date": "1962-03-02", "teams": [{"team_id": WARRIORS, "tricode": "PHW", "name": "Philadelphia Warriors"}]}}
    for scope in ("leaders", "team"):
        request = BoxscoreStatRequest.model_validate({**base, "scope": scope, "stat": {"stat": "blocks", "aggregation": "total"}})
        with pytest.raises(NotFoundError) as error:
            resolve(request)
        assert (error.value.code, error.value.reason) == ("no_record", "stat_not_recorded")
    request = BoxscoreStatRequest.model_validate({**base, "scope": "leaders", "stat": {"stat": "points", "aggregation": "total"}})
    assert resolve(request).result.leaders[0].player.player_id == WILT


def test_percentage_zero_beside_real_makes_is_computed():
    bird = next(p for p in OLD["boxscores"]["0048700060"]["homeTeam"]["players"] if p["personId"] == BIRD)
    assert bird["statistics"]["threePointersPercentage"] == 0.0  # source error: he was 1-for-3
    value = stat_value(bird["statistics"], STATS["three_point_percentage"])
    assert (value.value, value.made, value.attempted) == (0.333, 1, 3)


def test_modern_empty_game_log_still_means_did_not_play(monkeypatch, clear_player_games):
    monkeypatch.setattr(nba_stats_client, "fetch_scoreboard_v3", FakeScoreboards({}))
    monkeypatch.setattr(nba_stats_client, "fetch_league_game_finder", FakeFinder())
    with pytest.raises(NotFoundError) as error:
        games.find_player_game(BIRD, date(1988, 5, 21))
    assert error.value.code == "player_did_not_play"


# Division-era playoff sides ----------------------------------------------------


@pytest.fixture
def playoff_logs(monkeypatch):
    def frame(season, today=None):
        return pd.DataFrame(PLAYOFF_LOGS["seasons"][season], columns=PLAYOFF_LOGS["columns"])

    monkeypatch.setattr(playoffs_service, "fetch_playoff_team_games_df", frame)
    monkeypatch.setattr(playoffs_service, "fetch_corrected_team_scores", lambda game_id: None)
    monkeypatch.setattr(playoffs_service, "get_current_season", lambda today=None: "2026-27")


def team(team_id, tricode):
    return TeamRef(team_id=team_id, tricode=tricode, name=tricode)


def team_rounds(season, team_id, tricode):
    output = playoffs.team_postseason(season, team(team_id, tricode))
    assert_fits_answer(output, "postseason_summary")
    return [(row.round, row.conference, row.opponent.team_id, row.series_link.href) for row in output.result.rounds]


def test_philadelphia_warriors_1956_played_in_the_eastern_division(playoff_logs):
    # unseen-three-postseason_summary-03: was labeled west, where Golden State plays today.
    rounds = team_rounds("1955-56", WARRIORS, "PHW")
    assert [row[:3] for row in rounds] == [("conference_finals", "east", SIXERS), ("finals", None, PISTONS)]
    assert rounds[0][3] == "/playoffs/1956/east-division-final-1"


def test_san_diego_rockets_1969_played_in_the_western_division(playoff_logs):
    # unseen-three-postseason_summary-04: was labeled east, from Atlanta's present conference.
    assert [row[:3] for row in team_rounds("1968-69", ROCKETS, "SDR")] == [("conference_semifinals", "west", HAWKS)]


def test_cincinnati_royals_1964_played_in_the_eastern_division(playoff_logs):
    # unseen-three-postseason_summary-15: was labeled west, where Sacramento plays today.
    assert [row[:3] for row in team_rounds("1963-64", ROYALS, "CIN")] == [
        ("conference_semifinals", "east", SIXERS), ("conference_finals", "east", CELTICS)]


def test_league_summary_1970_labels_every_division_round(playoff_logs):
    # unseen-three-postseason_summary-06: Atlanta-Chicago and Los Angeles-Atlanta were labeled east.
    output = playoffs.league_postseason("1969-70")
    assert_fits_answer(output, "postseason_summary")
    labels = {frozenset(p.team.team_id for p in row.teams): (row.round, row.conference) for row in output.result.series}
    assert labels[frozenset({HAWKS, BULLS})] == ("conference_semifinals", "west")
    assert labels[frozenset({LAKERS, HAWKS})] == ("conference_finals", "west")
    assert labels[frozenset({BUCKS, SIXERS})] == ("conference_semifinals", "east")
    assert sorted(str(row.conference) for row in output.result.series) == ["None", "east", "east", "east", "west", "west", "west"]


def test_playoff_series_tool_uses_the_dated_side(playoff_logs):
    output = playoffs.series_result("1969-70", [HAWKS, LAKERS])
    assert (output.result.round, output.result.conference) == ("conference_finals", "west")
    assert output.links[0].href == "/playoffs/1970/west-division-final-1"
    # Selecting by side finds the series that was actually played on it.
    chosen = playoffs.series_result("1969-70", round_="conference_finals", conference_="west").result
    assert {row.team.team_id for row in chosen.teams} == {HAWKS, LAKERS}
    east = playoffs.series_result("1969-70", round_="conference_finals", conference_="east").result
    assert {row.team.team_id for row in east.teams} == {1610612752, BUCKS}


def test_conference_era_realignment_is_dated_too(playoff_logs):
    # Milwaukee and Chicago were Western Conference teams from 1970-71 to 1979-80.
    result = playoffs.series_result("1973-74", [BUCKS, BULLS]).result
    assert (result.round, result.conference) == ("conference_finals", "west")


def test_side_is_omitted_when_teams_were_on_neither(playoff_logs):
    # 1949-50 had a Central Division: its rounds are neither east nor west.
    central = playoffs.series_result("1949-50", [LAKERS, PISTONS]).result
    assert central.conference is None
    # Anderson and Tri-Cities met in the Western Division (the Hawks are in the East today).
    west = playoffs.series_result("1949-50", [1610610023, HAWKS]).result
    assert west.conference == "west"


def test_conference_is_none_when_team_sides_disagree_or_are_unknown():
    def series(*ids, group="east-conference", day="2024-05-01"):
        return {"bracketGroupId": group, "isFinals": False, "teams": [{"id": i} for i in ids], "games": [{"date": day}]}

    assert playoffs.conference(series(CELTICS, 1610612748)) == "east"
    assert playoffs.conference(series(CELTICS, LAKERS)) is None
    assert playoffs.conference(series(CELTICS, 1)) is None
    assert playoffs.conference(series(CELTICS, 1610612748, group="league")) is None


@pytest.mark.parametrize("team_id,year,side", [
    (WARRIORS, 1956, "East"), (WARRIORS, 1964, "West"),
    (ROYALS, 1962, "West"), (ROYALS, 1964, "East"), (ROYALS, 1975, "West"),
    (HAWKS, 1970, "West"), (HAWKS, 1971, "East"),
    (BULLS, 1975, "West"), (BULLS, 1981, "East"),
    (ROCKETS, 1969, "West"), (ROCKETS, 1975, "East"), (ROCKETS, 1981, "West"),
    (PISTONS, 1962, "West"), (PISTONS, 1968, "East"), (PISTONS, 1974, "West"), (PISTONS, 1989, "East"),
    (BUCKS, 1970, "East"), (BUCKS, 1974, "West"), (BUCKS, 2021, "East"),
    (1610612764, 1965, "West"), (1610612764, 1971, "East"),
    (1610612740, 2004, "East"), (1610612740, 2008, "West"),
    (LAKERS, 1950, "Central"), (LAKERS, 1951, "West"), (CELTICS, 1957, "East"), (CELTICS, None, "East"),
    (WARRIORS, None, "West"), (1, 1960, None),
])
def test_team_side_by_playoff_year(team_id, year, side):
    assert playoffs_service.get_team_side(team_id, year) == side
