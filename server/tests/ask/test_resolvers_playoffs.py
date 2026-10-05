
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
    clear_player_games,  # noqa: F401
    FakeFinder,
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


def test_named_matchup_returns_the_result(complete_2024):
    output = playoffs.series_result(SEASON, [DAL, BOS])
    result = output.result
    assert (result.round, result.conference) == ("finals", None)
    rows = [(row.team.tricode, row.wins, row.won_series) for row in result.teams]
    assert rows == [("DAL", 1, False), ("BOS", 4, True)]
    assert (result.status, result.games_played, result.summary) == ("complete", 5, "BOS won 4-1")
    assert [item.game.gameId for item in result.games][:2] == [playoff_game_id(4, 0, 1), playoff_game_id(4, 0, 2)]
    assert [link.href for link in output.links] == ["/playoffs/2024/the-finals", "/playoffs?season=2023-24"]
    assert output.sources[0].complete is True


def test_round_only_selection_names_the_participants(complete_2024):
    result = playoffs.series_result(SEASON, round_="finals").result
    # Rows keep the payload's order (game 1 host), never winner first.
    assert [row.team.tricode for row in result.teams] == ["BOS", "DAL"]


def test_one_team_and_round_lists_the_named_team_first(complete_2024):
    output = playoffs.series_result(SEASON, [BOS], "conference_finals")
    assert [row.team.tricode for row in output.result.teams] == ["BOS", "IND"]
    assert output.result.conference == "east"
    assert output.result.summary == "BOS won 4-0"
    assert output.links[0].href == "/playoffs/2024/east-conference-final-1"


def test_conference_and_round_choose_one_series(complete_2024):
    result = playoffs.series_result(SEASON, round_="first_round", conference_="west").result
    assert {row.team.tricode for row in result.teams} == {"DAL", "LAC"}


def test_several_matching_series_ask_for_clarification_with_protected_options(complete_2024):
    with pytest.raises(AmbiguousError) as error:
        playoffs.series_result(SEASON, round_="conference_finals")
    assert error.value.spoiler is True and len(error.value.options) == 2


def test_missing_series_for_a_named_team_is_not_found(complete_2024):
    with pytest.raises(NotFoundError) as error:
        playoffs.series_result(SEASON, [MIA], "finals")
    assert error.value.code == "no_record"


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
    assert (result.status, result.summary) == ("in_progress", "BOS leads 3-1")
    assert [row.won_series for row in result.teams] == [None, None]
    assert output.sources[0].complete is False


def test_past_series_below_known_win_target_has_no_winner():
    series = {"wins": {BOS: 3, DAL: 1}, "targetWins": 4}
    assert playoffs._winner(SEASON, series) is None
    assert playoffs._winner(SEASON, {"wins": {BOS: 4, DAL: 1}, "targetWins": 4}) == BOS
    assert playoffs._winner(SEASON, {"wins": {BOS: 3}, "targetWins": None}) is None


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
    named = playoffs.find_playoff_game(SEASON, 3, [BOS, DAL])
    assert named.game_id == game_id


def test_unplayed_series_game_is_not_found(complete_2024):
    with pytest.raises(NotFoundError) as error:
        playoffs.find_playoff_game(SEASON, 6, [BOS, DAL])
    assert error.value.reason == "series_game_not_played"


def test_series_game_missing_from_its_scoreboard_is_not_found(complete_2024, monkeypatch):
    monkeypatch.setattr(nba_stats_client, "fetch_scoreboard_v3", FakeScoreboards())
    with pytest.raises(NotFoundError) as error:
        playoffs.find_playoff_game(SEASON, 1, [BOS, DAL])
    assert error.value.reason == "game_not_on_scoreboard"


# Numbered games of a round named without teams ------------------------------

SEMIS = "conference_semifinals"
DONCIC = 1629029


def semis_board(monkeypatch, position, home, away, game_number):
    game_id = playoff_game_id(2, position, game_number)
    day = playoff_day(14, game_number)
    board = FakeScoreboards({day.isoformat(): [sb_game(game_id, home, away, series_number=f"Game {game_number}")]})
    monkeypatch.setattr(nba_stats_client, "fetch_scoreboard_v3", board)
    return game_id, day


def finder_for(monkeypatch, game_ids, day):
    rows = [{"GAME_ID": game_id, "PLAYER_ID": DONCIC, "TEAM_ID": DAL, "GAME_DATE": day.isoformat(),
             "PLAYER_NAME": "Luka Doncic"} for game_id in game_ids]
    finder = FakeFinder({(str(DONCIC), day.strftime("%m/%d/%Y")): rows})
    monkeypatch.setattr(nba_stats_client, "fetch_league_game_finder", finder)
    return finder


def test_round_game_only_one_series_reached_is_used(complete_2024, monkeypatch):
    # BOS-CLE ended in five; only DAL-OKC played a Game 6.
    game_id, day = semis_board(monkeypatch, 2, "OKC", "DAL", 6)
    finder = finder_for(monkeypatch, [], day)
    game = playoffs.find_playoff_game(SEASON, 6, round_=SEMIS, player_id=DONCIC)
    assert (game.game_id, game.date, game.round, game.game_number) == (game_id, day, SEMIS, 6)
    assert playoffs.find_playoff_game(SEASON, 6, round_=SEMIS).game_id == game_id
    assert finder.calls == []  # a unique game needs no player lookup


def test_round_game_in_several_series_is_narrowed_by_the_player(complete_2024, monkeypatch, clear_player_games):
    game_id, day = semis_board(monkeypatch, 2, "DAL", "OKC", 5)
    finder = finder_for(monkeypatch, [game_id], day)
    game = playoffs.find_playoff_game(SEASON, 5, round_=SEMIS, player_id=DONCIC)
    assert (game.game_id, set(game.team_ids)) == (game_id, {DAL, tid("OKC")})
    assert len(finder.calls) == 1  # one game-log read, no boxscore per series


@pytest.mark.parametrize("played_in", ["neither", "both", "no_player"])
def test_round_game_still_matching_several_series_is_never_guessed(complete_2024, monkeypatch, clear_player_games, played_in):
    monkeypatch.setattr(nba_stats_client, "fetch_scoreboard_v3", lambda *args, **kwargs: pytest.fail("a game was chosen"))
    both = [playoff_game_id(2, 0, 5), playoff_game_id(2, 2, 5)]
    finder_for(monkeypatch, both if played_in == "both" else [], playoff_day(14, 5))
    with pytest.raises(AmbiguousError) as error:
        playoffs.find_playoff_game(SEASON, 5, round_=SEMIS, player_id=None if played_in == "no_player" else DONCIC)
    assert (error.value.field, error.value.reason, error.value.spoiler) == ("teams", "several_series", True)
    offered = sorted(sorted(team.tricode for team in option["teams"]) for option in error.value.options)
    assert offered == [["BOS", "CLE"], ["DAL", "OKC"]]


def test_round_game_no_series_reached_is_not_found(complete_2024):
    with pytest.raises(NotFoundError) as error:
        playoffs.find_playoff_game(SEASON, 7, round_=SEMIS, player_id=DONCIC)
    assert (error.value.code, error.value.reason) == ("no_record", "series_game_not_played")


def test_round_game_is_not_unique_while_another_series_may_still_reach_it(monkeypatch):
    # BOS leads CLE 3-2: that series may still play a Game 6.
    specs = [(2, 0, "BOS", "CLE", "WLWWL", 14), (2, 2, "DAL", "OKC", "LWWLWW", 14)]
    install_playoffs(monkeypatch, specs, current_season=SEASON)
    with pytest.raises(AmbiguousError) as error:
        playoffs.find_playoff_game(SEASON, 6, round_=SEMIS)
    assert len(error.value.options) == 2


def test_boxscore_request_for_a_round_game_resolves_or_asks_for_teams(complete_2024, monkeypatch):
    from server.ask.models.request import BoxscoreStatRequest
    from server.ask.resolvers import resolve_boxscore_game
    from server.ask.resolvers.errors import ClarificationError

    def leaders(game_number):
        return BoxscoreStatRequest.model_validate({
            "intent": "boxscore_stat", "scope": "leaders", "stat": {"stat": "points"},
            "game": {"season": SEASON, "round": SEMIS, "game_number": game_number}})

    game_id, _ = semis_board(monkeypatch, 2, "OKC", "DAL", 6)
    assert resolve_boxscore_game(leaders(6)).game_id == game_id
    with pytest.raises(ClarificationError) as error:
        resolve_boxscore_game(leaders(5))
    assert (error.value.field, error.value.clarify_reason) == ("teams", "missing")
    with pytest.raises(NotFoundError):
        resolve_boxscore_game(leaders(7))


# Postseason summaries -------------------------------------------------------


def test_league_postseason_reports_champion_and_series(complete_2024):
    output = playoffs.league_postseason(SEASON)
    result = output.result
    assert (result.champion.tricode, result.runner_up.tricode) == ("BOS", "DAL")
    assert len(result.series) == 7
    finals = [row for row in result.series if row.round == "finals"][0]
    assert [(row.team.tricode, row.wins) for row in finals.teams] == [("BOS", 4), ("DAL", 1)]
    assert finals.winner_team_id == BOS and finals.status == "complete"
    assert result.team is None and result.rounds == [] and result.finish is None
    assert [link.href for link in output.links] == ["/playoffs?season=2023-24"]
    assert output.sources[0].complete is True


def test_team_postseason_for_the_champion(complete_2024):
    result = playoffs.team_postseason(SEASON, team_ref("BOS")).result
    assert result.team.name == "Boston Celtics"  # the dated record's name
    assert (result.finish, result.record.wins, result.record.losses, result.series_won) == ("champion", 16, 3, 4)
    rounds = result.rounds
    assert [(row.round, row.opponent.tricode, row.team_wins, row.opponent_wins, row.won) for row in rounds] == [
        ("first_round", "MIA", 4, 1, True),
        ("conference_semifinals", "CLE", 4, 1, True),
        ("conference_finals", "IND", 4, 0, True),
        ("finals", "DAL", 4, 1, True),
    ]
    assert rounds[0].series_link.href == "/playoffs/2024/east-conference-first-round-1"


def test_team_postseason_for_an_eliminated_team(complete_2024):
    result = playoffs.team_postseason(SEASON, team_ref("IND")).result
    assert (result.finish, result.record.wins, result.record.losses) == ("lost_conference_finals", 0, 4)


def test_team_without_playoff_games_did_not_qualify(complete_2024):
    output = playoffs.team_postseason(SEASON, team_ref("NYK"))
    result = output.result
    assert (result.finish, result.rounds) == ("did_not_qualify", [])
    assert result.team.tricode == "NYK"


def test_team_still_playing_is_in_progress(monkeypatch):
    specs = PLAYOFFS_2024[:-1] + [(4, 0, "BOS", "DAL", "WW", 42)]
    install_playoffs(monkeypatch, specs, current_season=SEASON)
    output = playoffs.team_postseason(SEASON, team_ref("DAL"))
    assert output.result.finish == "in_progress"
    assert output.result.rounds[-1].won is None
    assert output.sources[0].complete is False
    league = playoffs.league_postseason(SEASON).result
    assert league.champion is None


def test_requests_dispatch_to_playoff_resolvers(complete_2024):
    series = resolve(PlayoffSeriesRequest(season=SEASON, round="finals"))
    assert series.result.kind == "playoff_series"
    summary = resolve(PostseasonSummaryRequest(season=SEASON, team=team_ref("DAL")))
    assert summary.result.finish == "lost_finals"
    league = resolve(PostseasonSummaryRequest(season=SEASON))
    assert league.result.champion.team_id == BOS
    assert_fits_answer(series, "playoff_series")
    assert_fits_answer(summary, "postseason_summary")
    assert_fits_answer(league, "postseason_summary")


def test_unfinished_league_series_has_participants_without_a_winner(monkeypatch):
    specs = PLAYOFFS_2024[:-1] + [(4, 0, "BOS", "DAL", "WWWL", 42)]
    install_playoffs(monkeypatch, specs, current_season=SEASON)
    output = playoffs.league_postseason(SEASON)
    result = output.result
    final = next(row for row in result.series if row.round == "finals")
    assert final.status == "in_progress" and final.winner_team_id is None
    assert [(row.team.tricode, row.wins) for row in final.teams] == [("BOS", 3), ("DAL", 1)]
    assert result.champion is None and result.runner_up is None
    assert not output.sources[0].complete


def test_link_to_the_asked_series_is_not_a_spoiler(complete_2024):
    # The series page is the answer's own destination, even when the user did
    # not name the opponent (ADR 0006).
    inferred = playoffs.series_result(SEASON, [BOS], "conference_finals")
    assert not any(link.spoiler for link in inferred.links)
