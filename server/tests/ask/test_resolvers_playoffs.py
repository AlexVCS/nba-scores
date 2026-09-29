
import pytest
from fastapi import HTTPException

from server.ask import links
from server.ask.models.request import PlayoffSeriesRequest, PostseasonSummaryRequest
from server.ask.models.common import TeamRef
from server.ask.resolvers import playoffs, resolve
from server.ask.resolvers.errors import AmbiguousError, NotFoundError, UnavailableError
from server.services import nba_stats_client
from server.services import playoffs as playoffs_service
from server.tests.ask.test_resolvers_support import (
    PLAYOFFS_2024,
    assert_fits_answer,
    FakeScoreboards,
    install_playoffs,
    playoff_day,
    playoff_game_id,
    sb_game,
    tid,
)

SEASON = "2023-24"
BOS, DAL, MIA, IND, NYK = tid("BOS"), tid("DAL"), tid("MIA"), tid("IND"), tid("NYK")


@pytest.fixture
def complete_2024(monkeypatch):
    return install_playoffs(monkeypatch)


def team_ref(tricode):
    return TeamRef(team_id=tid(tricode), tricode=tricode, name=tricode)


# Series results -------------------------------------------------------------


def test_named_matchup_echoes_teams_and_guards_the_result(complete_2024):
    output = playoffs.series_result(SEASON, [DAL, BOS])
    result = output.result
    assert (result.round, result.conference) == ("finals", None)
    rows = [(row.team.value.tricode, row.team.spoiler, row.wins.value, row.won_series.value) for row in result.teams]
    assert rows == [("DAL", False, 1, False), ("BOS", False, 4, True)]
    assert all(row.wins.spoiler and row.won_series.spoiler for row in result.teams)
    assert (result.status.value, result.games_played.value, result.summary.value) == ("complete", 5, "BOS won 4-1")
    assert result.status.spoiler and result.games_played.spoiler and result.summary.spoiler and result.games.spoiler
    assert [item.game.gameId for item in result.games.value][:2] == [playoff_game_id(4, 0, 1), playoff_game_id(4, 0, 2)]
    assert [link.href for link in output.links] == ["/playoffs/2024/the-finals", "/playoffs?season=2023-24"]
    assert output.sources[0].complete is True


def test_round_only_selection_guards_inferred_participants(complete_2024):
    result = playoffs.series_result(SEASON, round_="finals").result
    assert all(row.team.spoiler for row in result.teams)
    # Rows keep the payload's order (game 1 host), never winner first.
    assert [row.team.value.tricode for row in result.teams] == ["BOS", "DAL"]


def test_one_team_and_round_guards_only_the_opponent(complete_2024):
    output = playoffs.series_result(SEASON, [BOS], "conference_finals")
    rows = [(row.team.value.tricode, row.team.spoiler) for row in output.result.teams]
    assert rows == [("BOS", False), ("IND", True)]
    assert output.result.conference == "east"
    assert output.result.summary.value == "BOS won 4-0"
    assert output.links[0].href == "/playoffs/2024/east-conference-final-1"


def test_conference_and_round_choose_one_series(complete_2024):
    result = playoffs.series_result(SEASON, round_="first_round", conference_="west").result
    assert {row.team.value.tricode for row in result.teams} == {"DAL", "LAC"}


def test_several_matching_series_ask_for_clarification_with_protected_options(complete_2024):
    with pytest.raises(AmbiguousError) as error:
        playoffs.series_result(SEASON, round_="conference_finals")
    assert error.value.spoiler is True and len(error.value.options) == 2


def test_missing_series_for_a_named_team_is_a_protected_not_found(complete_2024):
    with pytest.raises(NotFoundError) as error:
        playoffs.series_result(SEASON, [MIA], "finals")
    assert (error.value.code, error.value.spoiler) == ("no_record", True)


def test_series_slugs_match_the_frontend_convention(complete_2024):
    payload = playoffs_service.get_playoff_games_and_series(SEASON)
    slugs = {series["seriesKey"]: links.series_slug(series) for series in payload["series"]}
    assert slugs[f"R1-{BOS}-{MIA}"] == "east-conference-first-round-1"
    assert slugs[f"R2-{DAL}-{tid('OKC')}"] == "west-conference-semifinal-1"
    assert slugs[f"R4-{BOS}-{DAL}"] == "the-finals"


def test_undecided_current_series_is_in_progress(monkeypatch):
    specs = PLAYOFFS_2024[:-1] + [(4, 0, "BOS", "DAL", "WWWL", 42)]
    install_playoffs(monkeypatch, specs, current_season=SEASON)
    output = playoffs.series_result(SEASON, round_="finals")
    result = output.result
    assert (result.status.value, result.summary.value) == ("in_progress", "BOS leads 3-1")
    assert [row.won_series.value for row in result.teams] == [None, None]
    assert output.sources[0].complete is False


def test_invalid_and_pre_history_seasons(complete_2024):
    with pytest.raises(NotFoundError) as error:
        playoffs.series_result("1945-46", round_="finals")
    assert error.value.reason == "before_records"


def test_season_without_playoff_games_is_not_found(monkeypatch):
    install_playoffs(monkeypatch, specs=[])
    with pytest.raises(NotFoundError) as error:
        playoffs.series_result("2026-27", round_="finals")
    assert error.value.reason == "no_postseason_records"


@pytest.mark.parametrize("failure", [
    HTTPException(status_code=503, detail="NBA Stats API unavailable: Timeout"),
    nba_stats_client.UpstreamBadResponseError("LeagueGameLog", "KeyError", 5),
])
def test_playoff_source_failures_are_unavailable(monkeypatch, failure):
    def fail(season, today=None):
        raise failure

    monkeypatch.setattr(playoffs_service, "fetch_playoff_team_games_df", fail)
    with pytest.raises(UnavailableError):
        playoffs.series_result(SEASON, round_="finals")


def test_historical_rounds_map_by_distance_from_the_finals():
    assert playoffs.contract_round("1969-70", {"round": 3}) == "conference_finals"  # Division Finals
    assert playoffs.contract_round("1969-70", {"round": 2}) == "conference_semifinals"
    assert playoffs.contract_round("1946-47", {"round": 2}) == "conference_finals"  # BAA Semifinals
    assert playoffs.contract_round("2023-24", {"round": 0}) is None


# Numbered playoff games -----------------------------------------------------


def finals_board(monkeypatch, game_number):
    game_id = playoff_game_id(4, 0, game_number)
    day = playoff_day(42, game_number)
    board = FakeScoreboards({day.isoformat(): [sb_game(game_id, "DAL", "BOS", series_number=f"Game {game_number}")]})
    monkeypatch.setattr(nba_stats_client, "fetch_scoreboard_v3", board)
    return game_id, day


def test_numbered_series_game_is_verified_on_its_scoreboard(complete_2024, monkeypatch):
    game_id, day = finals_board(monkeypatch, 3)
    game = playoffs.find_playoff_game(SEASON, 3, round_="finals")
    assert (game.game_id, game.date, game.round, game.game_number) == (game_id, day, "finals", 3)
    assert game.participants_inferred is True
    named = playoffs.find_playoff_game(SEASON, 3, [BOS, DAL])
    assert named.participants_inferred is False


def test_unplayed_series_game_is_a_protected_not_found(complete_2024):
    with pytest.raises(NotFoundError) as error:
        playoffs.find_playoff_game(SEASON, 6, [BOS, DAL])
    assert (error.value.reason, error.value.spoiler) == ("series_game_not_played", True)


def test_series_game_missing_from_its_scoreboard_is_not_found(complete_2024, monkeypatch):
    monkeypatch.setattr(nba_stats_client, "fetch_scoreboard_v3", FakeScoreboards())
    with pytest.raises(NotFoundError) as error:
        playoffs.find_playoff_game(SEASON, 1, [BOS, DAL])
    assert error.value.reason == "game_not_on_scoreboard"


# Postseason summaries -------------------------------------------------------


def test_league_postseason_guards_champion_and_series(complete_2024):
    output = playoffs.league_postseason(SEASON)
    result = output.result
    assert (result.champion.value.tricode, result.runner_up.value.tricode) == ("BOS", "DAL")
    assert result.champion.spoiler and result.runner_up.spoiler and result.series.spoiler
    assert len(result.series.value) == 7
    finals = [row for row in result.series.value if row.round == "finals"][0]
    assert [(row.team.tricode, row.wins) for row in finals.teams] == [("BOS", 4), ("DAL", 1)]
    assert finals.winner_team_id == BOS and finals.status == "complete"
    assert result.team is None and result.rounds.value == [] and result.finish.value is None
    assert [link.href for link in output.links] == ["/playoffs?season=2023-24"]
    assert output.sources[0].complete is True


def test_team_postseason_for_the_champion(complete_2024):
    result = playoffs.team_postseason(SEASON, team_ref("BOS")).result
    assert result.team.name == "Boston Celtics"  # the dated record's name
    assert (result.finish.value, result.record.value.wins, result.record.value.losses, result.series_won.value) == ("champion", 16, 3, 4)
    rounds = result.rounds.value
    assert [(row.round, row.opponent.tricode, row.team_wins, row.opponent_wins, row.won) for row in rounds] == [
        ("first_round", "MIA", 4, 1, True),
        ("conference_semifinals", "CLE", 4, 1, True),
        ("conference_finals", "IND", 4, 0, True),
        ("finals", "DAL", 4, 1, True),
    ]
    assert rounds[0].series_link.href == "/playoffs/2024/east-conference-first-round-1"
    assert result.finish.spoiler and result.record.spoiler and result.series_won.spoiler and result.rounds.spoiler


def test_team_postseason_for_an_eliminated_team(complete_2024):
    result = playoffs.team_postseason(SEASON, team_ref("IND")).result
    assert (result.finish.value, result.record.value.wins, result.record.value.losses) == ("lost_conference_finals", 0, 4)


def test_team_without_playoff_games_did_not_qualify(complete_2024):
    output = playoffs.team_postseason(SEASON, team_ref("NYK"))
    result = output.result
    assert (result.finish.value, result.finish.spoiler, result.rounds.value, result.rounds.spoiler) == ("did_not_qualify", True, [], True)
    assert result.team.tricode == "NYK"


def test_team_still_playing_is_in_progress(monkeypatch):
    specs = PLAYOFFS_2024[:-1] + [(4, 0, "BOS", "DAL", "WW", 42)]
    install_playoffs(monkeypatch, specs, current_season=SEASON)
    output = playoffs.team_postseason(SEASON, team_ref("DAL"))
    assert output.result.finish.value == "in_progress"
    assert output.result.rounds.value[-1].won is None
    assert output.sources[0].complete is False
    league = playoffs.league_postseason(SEASON).result
    assert league.champion.value is None


def test_requests_dispatch_to_playoff_resolvers(complete_2024):
    series = resolve(PlayoffSeriesRequest(season=SEASON, round="finals"))
    assert series.result.kind == "playoff_series"
    summary = resolve(PostseasonSummaryRequest(season=SEASON, team=team_ref("DAL")))
    assert summary.result.finish.value == "lost_finals"
    league = resolve(PostseasonSummaryRequest(season=SEASON))
    assert league.result.champion.value.team_id == BOS
    assert_fits_answer(series, "playoff_series")
    assert_fits_answer(summary, "postseason_summary")
    assert_fits_answer(league, "postseason_summary")


def test_unfinished_league_series_has_participants_without_a_winner(monkeypatch):
    specs = PLAYOFFS_2024[:-1] + [(4, 0, "BOS", "DAL", "WWWL", 42)]
    install_playoffs(monkeypatch, specs, current_season=SEASON)
    output = playoffs.league_postseason(SEASON)
    result = output.result
    final = next(row for row in result.series.value if row.round == "finals")
    assert final.status == "in_progress" and final.winner_team_id is None
    assert [(row.team.tricode, row.wins) for row in final.teams] == [("BOS", 3), ("DAL", 1)]
    assert result.champion.value is None and result.champion.spoiler
    assert result.runner_up.value is None and result.runner_up.spoiler
    assert not output.sources[0].complete


def test_inferred_series_destination_is_protected(complete_2024):
    inferred = playoffs.series_result(SEASON, [BOS], "conference_finals")
    assert inferred.links[0].spoiler
    named = playoffs.series_result(SEASON, [BOS, DAL])
    assert not named.links[0].spoiler
