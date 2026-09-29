from dataclasses import replace
from datetime import date

import pytest

from server.ask.models.request import BoxscoreStatRequest
from server.ask.resolvers import boxscore, games, resolve, resolve_boxscore_game
from server.ask.resolvers.errors import ClarificationError, NotFoundError, UnavailableError, UnsupportedError
from server.ask.resolvers.spoiler_policy import HIDDEN_GAME_GATE
from server.services import nba_stats_client
from server.tests.ask.test_resolvers_support import (  # noqa: F401
    FakeBoxscores,
    FakeFinder,
    assert_fits_answer,
    FakeScoreboards,
    boxscore as make_boxscore,
    clear_player_games,
    player,
    sb_game,
    tid,
)

DAY = date(2024, 1, 15)
GAME = "0022300601"
TATUM, BROWN, WHITE, BUTLER, ADEBAYO, HOLIDAY = 1628369, 1627759, 1628401, 202710, 1628389, 201950

BOS_PLAYERS = [
    player(TATUM, "Jayson", "Tatum", "38:12", points=30, reboundsTotal=10, assists=5, fieldGoalsMade=11,
           fieldGoalsAttempted=22, fieldGoalsPercentage=0.5, plusMinusPoints=6),
    player(BROWN, "Jaylen", "Brown", "35:00", points=30, reboundsTotal=4, assists=7, fieldGoalsMade=12,
           fieldGoalsAttempted=20, fieldGoalsPercentage=0.6, plusMinusPoints=-2),
    player(HOLIDAY, "Jrue", "Holiday", "", comment="DNP - Coach's Decision"),
    player(WHITE, "Derrick", "White", "", comment="Injury/Illness", status="INACTIVE"),
]
MIA_PLAYERS = [
    player(BUTLER, "Jimmy", "Butler", "40:00", points=25, reboundsTotal=6, assists=9, fieldGoalsMade=9,
           fieldGoalsAttempted=18, fieldGoalsPercentage=0.5, plusMinusPoints=-6),
    player(ADEBAYO, "Bam", "Adebayo", "36:30", points=18, reboundsTotal=12, assists=9, fieldGoalsMade=8,
           fieldGoalsAttempted=14, fieldGoalsPercentage=0.571, plusMinusPoints=0),
]
TEAM_STATS = {"points": 120, "reboundsTotal": 44, "assists": 25, "fieldGoalsMade": 45, "fieldGoalsAttempted": 90,
              "fieldGoalsPercentage": 0.5, "threePointersMade": 15, "threePointersAttempted": 40,
              "freeThrowsMade": 15, "freeThrowsAttempted": 20, "steals": 7, "blocks": 5, "turnovers": 11,
              "foulsPersonal": 18, "reboundsOffensive": 9}


@pytest.fixture
def game_data(monkeypatch):
    boards = FakeScoreboards({"2024-01-15": [
        sb_game(GAME, "BOS", "MIA", home_score=120, away_score=118, period=5, status_text="Final/OT"),
        sb_game("0022300602", "NYK", "CLE", status=1),
    ]})
    boxes = FakeBoxscores({GAME: make_boxscore(GAME, "BOS", "MIA", BOS_PLAYERS, MIA_PLAYERS, TEAM_STATS, {"points": 118})})
    monkeypatch.setattr(nba_stats_client, "fetch_scoreboard_v3", boards)
    monkeypatch.setattr(nba_stats_client, "fetch_boxscore_traditional", boxes)
    # Lifetime metadata is optional; its failure never fails the boxscore.
    monkeypatch.setattr(nba_stats_client, "fetch_boxscore_summary_v3", FakeBoxscores(failing={GAME}))
    return boards, boxes


def final_game():
    return games.get_game(GAME, DAY)


def test_player_stat_returns_guarded_values_and_the_game_team(game_data):
    result = boxscore.player_stat(final_game(), TATUM, "points")
    line = result.player_line
    assert (line.player.name, line.team.tricode, line.status) == ("Jayson Tatum", "BOS", "played")
    (value,) = line.values
    assert value.spoiler is True and (value.value.value, value.value.display) == (30, "30")
    assert result.game.final_score.spoiler is True and result.aggregation == "total"


def test_player_stat_line_formats_shooting_minutes_and_plus_minus(game_data):
    line = boxscore.player_stat(final_game(), TATUM, "stat_line").player_line
    values = {item.value.stat: item.value for item in line.values}
    assert values["minutes"].display == "38:12"
    assert (values["field_goals"].display, values["field_goals"].made, values["field_goals"].attempted) == ("11-22", 11, 22)
    assert values["plus_minus"].display == "+6"
    assert values["steals"].value is None and values["steals"].display == "—"
    assert all(item.spoiler for item in line.values)


def test_percentage_display(game_data):
    (value,) = boxscore.player_stat(final_game(), BROWN, "field_goal_percentage").player_line.values
    assert (value.value.display, value.value.made, value.value.attempted) == ("60.0%", 12, 20)


def test_listed_players_who_did_not_play_have_a_status_and_no_values(game_data):
    dnp = boxscore.player_stat(final_game(), HOLIDAY, "points").player_line
    assert (dnp.status, dnp.values) == ("did_not_play", [])
    inactive = boxscore.player_stat(final_game(), WHITE, "points").player_line
    assert inactive.status == "inactive"


def test_player_missing_from_the_boxscore_did_not_play(game_data):
    with pytest.raises(NotFoundError) as error:
        boxscore.player_stat(final_game(), 1, "points")
    assert error.value.code == "player_did_not_play"


def test_unrecorded_statistic_is_not_found(game_data):
    with pytest.raises(NotFoundError) as error:
        boxscore.player_stat(final_game(), TATUM, "blocks")
    assert (error.value.code, error.value.reason) == ("no_record", "stat_not_recorded")


def test_per_game_aggregation_is_unsupported_not_answered_as_a_total(game_data):
    with pytest.raises(UnsupportedError) as error:
        boxscore.player_stat(final_game(), TATUM, "points", aggregation="per_game")
    assert error.value.unsupported_reason == "multi_game_average"


def test_team_totals_for_one_team_or_both(game_data):
    one = boxscore.team_stat(final_game(), "rebounds", [tid("BOS")])
    assert [(line.team.tricode, line.values[0].value.value) for line in one.team_lines] == [("BOS", 44)]
    both = boxscore.team_stat(final_game(), "points")
    assert [(line.team.tricode, line.values[0].value.display) for line in both.team_lines] == [("BOS", "120"), ("MIA", "118")]
    with pytest.raises(NotFoundError):
        boxscore.team_stat(final_game(), "points", [tid("NYK")])


def test_leaders_rank_each_teams_leaders_together_and_share_ties(game_data):
    result = boxscore.stat_leaders(final_game(), "points")
    rows = [(row.rank, row.player.name, row.team.tricode, row.value.value) for row in result.leaders.value]
    assert rows == [(1, "Jayson Tatum", "BOS", 30), (1, "Jaylen Brown", "BOS", 30), (3, "Jimmy Butler", "MIA", 25)]
    assert result.leaders.spoiler
    mia = boxscore.stat_leaders(final_game(), "assists", tid("MIA"))
    assert [row.player.name for row in mia.leaders.value] == ["Jimmy Butler", "Bam Adebayo"]


def test_minutes_leader_uses_parsed_minutes(game_data):
    result = boxscore.stat_leaders(final_game(), "minutes")
    assert [row.player.name for row in result.leaders.value] == ["Jimmy Butler", "Jayson Tatum"]


def test_leaders_refuse_partial_or_unrankable_statistics(game_data):
    with pytest.raises(NotFoundError):
        boxscore.stat_leaders(final_game(), "steals")
    with pytest.raises(UnsupportedError):
        boxscore.stat_leaders(final_game(), "field_goal_percentage")
    with pytest.raises(UnsupportedError):
        boxscore.stat_leaders(final_game(), "stat_line")


def test_scheduled_games_have_no_boxscore_and_are_never_fetched(game_data):
    _, boxes = game_data
    with pytest.raises(NotFoundError) as error:
        boxscore.player_stat(games.get_game("0022300602", DAY), TATUM, "points")
    assert error.value.reason == "game_not_started"
    assert boxes.calls == []


def test_boxscore_failures_are_unavailable_and_empty_data_is_not_found(monkeypatch, game_data):
    boards, _ = game_data
    monkeypatch.setattr(nba_stats_client, "fetch_boxscore_traditional", FakeBoxscores(failing={GAME}))
    with pytest.raises(UnavailableError):
        boxscore.player_stat(final_game(), TATUM, "points")
    monkeypatch.setattr(nba_stats_client, "fetch_boxscore_traditional", FakeBoxscores({}))
    with pytest.raises(NotFoundError) as error:
        boxscore.player_stat(final_game(), TATUM, "points")
    assert (error.value.code, error.value.reason) == ("no_record", "boxscore_not_recorded")


def test_boxscore_requests_share_the_cached_boxscore(game_data):
    _, boxes = game_data
    game = final_game()
    boxscore.player_stat(game, TATUM, "points")
    boxscore.stat_leaders(game, "rebounds")
    assert boxes.calls == [GAME]


# Request dispatch -----------------------------------------------------------


def request(**kwargs):
    return BoxscoreStatRequest.model_validate({"stat": {"stat": "points"}, **kwargs})


def team(tricode):
    return {"team_id": tid(tricode), "tricode": tricode, "name": tricode}


def test_player_and_date_resolve_through_the_players_game_log(game_data, monkeypatch, clear_player_games):
    finder = FakeFinder({(str(TATUM), "01/15/2024"): [
        {"PLAYER_ID": TATUM, "PLAYER_NAME": "Jayson Tatum", "TEAM_ID": tid("BOS"), "GAME_ID": GAME, "GAME_DATE": "2024-01-15"},
    ]})
    monkeypatch.setattr(nba_stats_client, "fetch_league_game_finder", finder)
    output = resolve(request(scope="player", player={"player_id": TATUM, "name": "Jayson Tatum"}, game={"date": "2024-01-15"}))
    assert output.result.player_line.values[0].value.value == 30
    assert [link.href for link in output.links] == ["/games/0022300601/boxscore?date=2024-01-15", "/?date=2024-01-15"]
    assert output.sources[0].complete is True


def test_player_with_team_and_date_uses_the_scoreboard_game(game_data, monkeypatch):
    monkeypatch.setattr(nba_stats_client, "fetch_league_game_finder", FakeFinder(error=AssertionError("not used")))
    output = resolve(request(scope="player", player={"player_id": BUTLER, "name": "Jimmy Butler"},
                             game={"date": "2024-01-15", "teams": [team("MIA")]}))
    assert output.result.player_line.team.tricode == "MIA"


def test_team_scope_uses_request_team_or_selector_teams(game_data):
    output = resolve(request(scope="team", team=team("BOS"), game={"date": "2024-01-15"}))
    assert [line.team.tricode for line in output.result.team_lines] == ["BOS"]
    output = resolve(request(scope="team", game={"date": "2024-01-15", "teams": [team("BOS"), team("MIA")]}))
    assert len(output.result.team_lines) == 2


def test_leaders_by_game_id(game_data):
    output = resolve(request(scope="leaders", game={"game_id": GAME, "date": "2024-01-15"}))
    assert output.result.leaders.value[0].rank == 1
    assert_fits_answer(output, "boxscore_stat")


def test_gated_leaders_without_teams_clarify_before_game_lookup(monkeypatch):
    monkeypatch.setattr("server.ask.resolvers.request_spoiler_gate", lambda _request: HIDDEN_GAME_GATE)
    monkeypatch.setattr(games, "find_game_on_date", lambda *args: pytest.fail("game lookup disclosed schedule"))
    monkeypatch.setattr("server.ask.resolvers.playoffs.find_playoff_game",
                        lambda *args: pytest.fail("series lookup disclosed participants"))
    for selector in ({"date": "2024-05-15"},
                     {"season": "2023-24", "round": "conference_semifinals", "game_number": 5}):
        with pytest.raises(ClarificationError) as error:
            resolve(request(scope="leaders", game=selector))
        assert (error.value.field, error.value.clarify_reason) == ("teams", "missing")


@pytest.mark.parametrize("games_on_date", [1, 2])
def test_finals_date_without_game_number_clarifies_independent_of_results(monkeypatch, games_on_date):
    monkeypatch.setattr("server.ask.resolvers.request_spoiler_gate", lambda _request: HIDDEN_GAME_GATE)
    calls = []
    def lookup(*args):
        calls.append(games_on_date)
        if games_on_date == 2:
            raise AssertionError("multiple game result reached")
        return None
    monkeypatch.setattr(games, "find_game_on_date", lookup)
    with pytest.raises(ClarificationError) as error:
        resolve(request(scope="leaders", game={"date": "2024-05-15", "round": "finals"}))
    assert (error.value.field, error.value.clarify_reason) == ("teams", "missing")
    assert calls == []


def test_known_finals_and_named_team_do_not_get_preemptive_clarification(game_data, monkeypatch):
    monkeypatch.setattr("server.ask.resolvers.request_spoiler_gate", lambda _request: HIDDEN_GAME_GATE)
    monkeypatch.setattr("server.ask.resolvers.playoffs.find_playoff_game", lambda *args: final_game())
    finals = resolve(request(scope="leaders", game={"season": "2023-24", "round": "finals", "game_number": 1}))
    assert finals.result.leaders.value
    named = resolve(request(scope="leaders", game={"date": "2024-01-15", "teams": [team("BOS")]}))
    assert named.result.leaders.value


def test_named_team_not_in_the_game_is_not_found(game_data):
    with pytest.raises(NotFoundError):
        resolve(request(scope="team", team=team("NYK"), game={"game_id": GAME, "date": "2024-01-15"}))


def test_numbered_game_selection_includes_scope_team(game_data, monkeypatch):
    calls = []
    def find(season, number, teams, round_, conference):
        calls.append((season, number, teams, round_, conference))
        return final_game()
    monkeypatch.setattr("server.ask.resolvers.playoffs.find_playoff_game", find)
    resolve_boxscore_game(request(scope="team", team=team("BOS"), game={
        "season": "2023-24", "game_number": 1, "round": "conference_finals",
    }))
    assert calls == [("2023-24", 1, [tid("BOS")], "conference_finals", None)]


def test_date_and_playoff_game_must_identify_the_same_game(game_data, monkeypatch):
    playoff_game = replace(final_game(), round="finals", game_number=1)
    monkeypatch.setattr("server.ask.resolvers.playoffs.find_playoff_game", lambda *args: playoff_game)
    base = {"season": "2023-24", "round": "finals", "game_number": 1}
    matched = request(scope="leaders", game={**base, "date": "2024-01-15"})
    assert resolve_boxscore_game(matched).game_id == GAME

    conflict = request(scope="leaders", game={**base, "date": "2024-01-16"})
    with pytest.raises(NotFoundError) as error:
        resolve_boxscore_game(conflict)
    assert error.value.reason == "date_not_matching_game"


def test_dated_game_rejects_conflicting_selected_season_or_game_number(game_data):
    for detail, value, reason in [
        ("season", "2022-23", "season_not_matching_game"),
        ("game_number", 2, "game_number_unverifiable"),
    ]:
        chosen = request(scope="leaders", game={"date": "2024-01-15", "teams": [team("BOS")], detail: value})
        with pytest.raises((NotFoundError, ClarificationError)) as error:
            resolve_boxscore_game(chosen)
        assert error.value.reason == reason
