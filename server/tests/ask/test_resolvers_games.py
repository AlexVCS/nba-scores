from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from server.ask.models.common import DateRange
from server.ask.models.request import BoxscoreStatRequest
from server.ask.models.response import AskResponse
from server.ask.resolvers import games
from server.ask.resolvers.spoiler_policy import outcome_may_reveal_result
from server.services.nba_schedule import SeasonSchedule, SOURCE_SCHEDULE
from server.ask.resolvers.errors import AmbiguousError, ClarificationError, NotFoundError, UnavailableError
from server.services import nba_stats_client
from server.tests.ask.test_resolvers_support import FakeFinder, FakeScoreboards, clear_player_games, sb_game, tid  # noqa: F401

DAY = date(2024, 1, 15)


def rng(start, end=None):
    return DateRange(start=start, end=end or start)


@pytest.fixture
def boards(monkeypatch):
    fake = FakeScoreboards({
        "2024-01-15": [
            sb_game("0022300601", "BOS", "MIA", home_score=120, away_score=118, period=5, status_text="Final/OT"),
            sb_game("0022300602", "NYK", "CLE"),
        ],
        "2024-01-16": [sb_game("0022300611", "MIA", "NYK", status=1)],
        "2024-01-17": [sb_game("0022300621", "DAL", "BOS", status=2)],
    })
    monkeypatch.setattr(nba_stats_client, "fetch_scoreboard_v3", fake)
    return fake


def test_single_day_search_returns_contract_games_with_links(boards):
    output = games.search_games(rng(DAY))
    result = output.result
    assert result.kind == "games" and result.total_games == 2
    (day,) = result.days
    overtime = day.games[0]
    assert overtime.game.gameId == "0022300601"
    assert overtime.game.gameStatusText == "Final/OT"
    assert overtime.game.boxscoreAvailable is True
    assert [link.href for link in overtime.links] == ["/games/0022300601/boxscore?date=2024-01-15"]
    assert [link.href for link in output.links] == ["/?date=2024-01-15"]
    assert output.sources[0].complete is True
    # The embedded game stays camelCase inside the snake_case payload.
    dumped = result.model_dump(mode="json")
    assert dumped["days"][0]["games"][0]["game"]["homeTeam"]["teamTricode"] == "BOS"


def test_scheduled_game_has_no_boxscore_link(boards):
    result = games.search_games(rng(date(2024, 1, 16))).result
    item = result.days[0].games[0]
    assert item.links == [] and item.game.boxscoreAvailable is False


def test_range_lists_only_days_with_games_and_reports_incomplete_when_live(boards):
    output = games.search_games(rng(date(2024, 1, 14), date(2024, 1, 20)))
    assert [day.date for day in output.result.days] == [date(2024, 1, 15), date(2024, 1, 16), date(2024, 1, 17)]
    assert len(boards.calls) == 7
    assert output.sources[0].complete is False


def test_team_filters_one_team_or_head_to_head(boards):
    one = games.search_games(rng(date(2024, 1, 15), date(2024, 1, 17)), [tid("BOS")]).result
    assert [item.game.gameId for day in one.days for item in day.games] == ["0022300601", "0022300621"]
    assert [team.tricode for team in one.teams] == ["BOS"]
    two = games.search_games(rng(date(2024, 1, 15), date(2024, 1, 17)), [tid("NYK"), tid("MIA")]).result
    assert [item.game.gameId for day in two.days for item in day.games] == ["0022300611"]
    with pytest.raises(ValueError):
        games.search_games(rng(DAY), [tid("BOS"), tid("MIA"), tid("NYK")])


def test_seven_day_maximum_is_enforced():
    with pytest.raises(ValidationError):
        rng(DAY, DAY + timedelta(days=7))
    # Direct callers that bypass DateRange validation are still refused.
    oversized = DateRange.model_construct(start=DAY, end=DAY + timedelta(days=7))
    with pytest.raises(ClarificationError) as error:
        games.search_games(oversized)
    assert error.value.clarify_reason == "range_too_long"


def test_no_matching_games_is_not_found(boards):
    with pytest.raises(NotFoundError) as error:
        games.search_games(rng(date(2024, 1, 18)))
    assert error.value.code == "no_games"


def test_dates_before_the_first_game_are_a_historical_gap(boards):
    with pytest.raises(NotFoundError) as error:
        games.search_games(rng(date(1946, 10, 1)))
    assert (error.value.code, error.value.reason) == ("no_record", "before_records")
    assert boards.calls == []


def test_one_failing_day_makes_the_search_unavailable_not_partial(monkeypatch):
    fake = FakeScoreboards({"2024-01-15": [sb_game("0022300601", "BOS", "MIA")]}, failing={"2024-01-16"})
    monkeypatch.setattr(nba_stats_client, "fetch_scoreboard_v3", fake)
    with pytest.raises(UnavailableError) as error:
        games.search_games(rng(date(2024, 1, 15), date(2024, 1, 16)))
    assert error.value.reason == "upstream_unavailable" and error.value.retryable


def test_searches_reuse_the_shared_scoreboard_cache(boards):
    games.search_games(rng(DAY))
    games.find_game_on_date(DAY, [tid("BOS")])
    assert boards.calls == ["2024-01-15"]


def test_find_game_on_date_requires_a_unique_game(boards):
    assert games.find_game_on_date(DAY, [tid("MIA")]).game_id == "0022300601"
    with pytest.raises(AmbiguousError) as error:
        games.find_game_on_date(DAY)
    assert [option["game_id"] for option in error.value.options] == ["0022300601", "0022300602"]
    with pytest.raises(NotFoundError):
        games.find_game_on_date(DAY, [tid("DAL")])


def test_game_context_reports_final_score_and_overtime(boards):
    context = games.game_context(games.get_game("0022300601", DAY))
    assert context.season == "2023-24" and context.season_type == "regular_season"
    assert (context.final_score.home, context.final_score.away, context.final_score.periods) == (120, 118, 5)
    live = games.game_context(games.get_game("0022300621", date(2024, 1, 17)))
    assert live.final_score is None


def test_playoff_game_context_reads_round_and_number_from_numbered_games(monkeypatch):
    fake = FakeScoreboards({"2024-06-12": [sb_game("0042300403", "DAL", "BOS", series_number="Game 3")]})
    monkeypatch.setattr(nba_stats_client, "fetch_scoreboard_v3", fake)
    context = games.game_context(games.get_game("0042300403", date(2024, 6, 12)))
    assert (context.season_type, context.round, context.game_number) == ("playoffs", "finals", 3)


def test_game_id_without_date_uses_summary_date(boards, monkeypatch):
    monkeypatch.setattr(games.data, "game_date", lambda game_id: DAY)
    assert games.get_game("0022300602").home.tricode == "NYK"
    with pytest.raises(NotFoundError) as error:
        games.get_game("0022300699", DAY)
    assert error.value.reason == "game_not_on_scoreboard"


# Player game by exact date --------------------------------------------------

PLAYER = 1628369


def finder_row(game_id, team, day="2024-01-15", player_id=PLAYER):
    return {"PLAYER_ID": player_id, "PLAYER_NAME": "Jayson Tatum", "TEAM_ID": tid(team), "GAME_ID": game_id, "GAME_DATE": day}


def test_player_game_is_found_by_id_and_exact_date_then_verified(boards, monkeypatch, clear_player_games):
    finder = FakeFinder({(str(PLAYER), "01/15/2024"): [finder_row("0022300601", "BOS")]})
    monkeypatch.setattr(nba_stats_client, "fetch_league_game_finder", finder)
    game, team = games.find_player_game(PLAYER, DAY)
    assert game.game_id == "0022300601" and team.tricode == "BOS"
    call = finder.calls[0]
    assert call["player_or_team_abbreviation"] == "P"
    assert call["date_from_nullable"] == call["date_to_nullable"] == "01/15/2024"
    assert boards.calls == ["2024-01-15"]
    games.find_player_game(PLAYER, DAY)
    assert len(finder.calls) == 1  # cached


def test_player_team_comes_from_the_dated_record_not_a_roster(boards, monkeypatch, clear_player_games):
    # A traded player's row names the team he played for that night.
    finder = FakeFinder({(str(PLAYER), "01/15/2024"): [finder_row("0022300601", "MIA")]})
    monkeypatch.setattr(nba_stats_client, "fetch_league_game_finder", finder)
    assert games.find_player_game(PLAYER, DAY)[1].tricode == "MIA"


def test_player_without_a_game_that_day_did_not_play(boards, monkeypatch, clear_player_games):
    monkeypatch.setattr(nba_stats_client, "fetch_league_game_finder", FakeFinder())
    with pytest.raises(NotFoundError) as error:
        games.find_player_game(PLAYER, DAY)
    assert error.value.code == "player_did_not_play"


@pytest.mark.parametrize("days_after", [0, 1])
def test_recent_empty_player_log_does_not_claim_did_not_play(boards, monkeypatch, clear_player_games, days_after):
    monkeypatch.setattr(games, "nba_today", lambda: DAY + timedelta(days=days_after))
    monkeypatch.setattr(nba_stats_client, "fetch_league_game_finder", FakeFinder())
    with pytest.raises(NotFoundError) as error:
        games.find_player_game(PLAYER, DAY)
    assert (error.value.code, error.value.reason) == ("no_record", "recent_player_record_unverified")
    assert boards.calls == [DAY.isoformat()]


def test_player_rows_that_disagree_with_the_scoreboard_are_not_trusted(boards, monkeypatch, clear_player_games):
    rows = {(str(PLAYER), "01/15/2024"): [finder_row("0022300609", "BOS")]}
    monkeypatch.setattr(nba_stats_client, "fetch_league_game_finder", FakeFinder(rows))
    with pytest.raises(NotFoundError) as error:
        games.find_player_game(PLAYER, DAY)
    assert error.value.reason == "game_not_on_scoreboard"
    games.data._player_game_cache.clear()
    rows = {(str(PLAYER), "01/15/2024"): [finder_row("0022300601", "DAL")]}
    monkeypatch.setattr(nba_stats_client, "fetch_league_game_finder", FakeFinder(rows))
    with pytest.raises(NotFoundError) as error:
        games.find_player_game(PLAYER, DAY)
    assert error.value.reason == "player_team_not_in_game"


def test_player_rows_for_other_dates_or_players_are_ignored(boards, monkeypatch, clear_player_games):
    rows = {(str(PLAYER), "01/15/2024"): [finder_row("0022300601", "BOS", day="2024-01-14"), finder_row("0022300601", "BOS", player_id=1)]}
    monkeypatch.setattr(nba_stats_client, "fetch_league_game_finder", FakeFinder(rows))
    with pytest.raises(NotFoundError):
        games.find_player_game(PLAYER, DAY)


@pytest.mark.parametrize("error", [
    nba_stats_client.UpstreamUnavailableError("LeagueGameFinder", "Timeout", 10),
    nba_stats_client.UpstreamBadResponseError("LeagueGameFinder", "KeyError", 10),
])
def test_player_lookup_failures_are_unavailable(boards, monkeypatch, clear_player_games, error):
    monkeypatch.setattr(nba_stats_client, "fetch_league_game_finder", FakeFinder(error=error))
    with pytest.raises(UnavailableError):
        games.find_player_game(PLAYER, DAY)


def test_malformed_player_rows_are_unavailable(boards, monkeypatch, clear_player_games):
    rows = {(str(PLAYER), "01/15/2024"): [{"PLAYER_ID": PLAYER, "GAME_ID": 12, "TEAM_ID": 1, "GAME_DATE": "2024-01-15"}]}
    monkeypatch.setattr(nba_stats_client, "fetch_league_game_finder", FakeFinder(rows))
    with pytest.raises(UnavailableError) as error:
        games.find_player_game(PLAYER, DAY)
    assert error.value.reason == "upstream_bad_response"


def test_games_result_fits_an_answer_response(boards):
    output = games.search_games(rng(DAY))
    response = AskResponse(
        request_id="r1",
        outcome="answer",
        question="games on January 15, 2024",
        interpretation={"intent": "game_search", "reference_time": "2024-01-16T12:00:00-05:00"},
        result=output.result,
        links=list(output.links),
        sources=list(output.sources),
        interpreter={"model_called": False},
    )
    assert AskResponse.model_validate_json(response.model_dump_json()) == response


def test_playoff_context_names_both_teams(monkeypatch):
    fake = FakeScoreboards({"2024-06-12": [sb_game("0042300403", "DAL", "BOS", series_number="Game 3")]})
    monkeypatch.setattr(nba_stats_client, "fetch_scoreboard_v3", fake)
    context = games.game_context(games.get_game("0042300403", date(2024, 6, 12)))
    assert {context.away.tricode, context.home.tricode} == {"DAL", "BOS"}


def test_ambiguous_game_uses_shared_teams_clarification_field(boards):
    with pytest.raises(AmbiguousError) as error:
        games.find_game_on_date(DAY)
    assert error.value.field == "teams"


def test_conditional_and_filtered_playoff_games_are_answered_in_full(monkeypatch):
    # Asking is consent (ADR 0006): a possible Game 5 and a team-filtered Finals
    # game are part of the answer, with their links, and are not flagged.
    day = date(2024, 6, 15)
    monkeypatch.setattr(nba_stats_client, "fetch_scoreboard_v3", FakeScoreboards({day.isoformat(): [
        sb_game("0042300405", "BOS", "DAL", series_number="Game 5"),
    ]}))
    output = games.search_games(rng(day))
    item = output.result.days[0].games[0]
    assert output.result.total_games == 1 and item.game.seriesGameNumber == "Game 5"
    assert not any(link.spoiler for link in (*item.links, *output.links))

    monkeypatch.setattr(nba_stats_client, "fetch_scoreboard_v3", FakeScoreboards({"2024-06-06": [
        sb_game("0042300401", "BOS", "DAL", series_number="Game 1"),
    ]}))
    filtered = games.search_games(rng(date(2024, 6, 6)), [tid("BOS")])
    assert filtered.result.total_games == 1
    assert not any(link.spoiler for link in filtered.links)


def _date_stat(day, scope="leaders"):
    return BoxscoreStatRequest.model_validate({"scope": scope, "stat": {"stat": "points"}, "game": {"date": day.isoformat()}})


def test_postseason_dates_may_reveal_results_before_lookup(monkeypatch):
    looked_up = []

    def schedule(season, **kwargs):
        looked_up.append(season)
        return SeasonSchedule(season, SOURCE_SCHEDULE, frozenset({"2020-10-09"}), {
            "0041900405": {"gameId": "0041900405", "gameDateEst": "2020-10-09", "seriesGameNumber": "Game 5"},
        })
    monkeypatch.setattr("server.ask.resolvers.spoiler_policy.nba_schedule.get_season_schedule", schedule)
    assert outcome_may_reveal_result(_date_stat(date(2020, 10, 9)))
    assert looked_up == ["2019-20"]  # the bubble Finals ran into October 2020


def test_regular_season_dates_do_not_reveal_results(monkeypatch):
    day = date(2024, 1, 15)
    schedule = SeasonSchedule("2023-24", SOURCE_SCHEDULE, frozenset({day.isoformat()}), {
        "0022300601": {"gameId": "0022300601", "gameDateEst": day.isoformat()},
    })
    monkeypatch.setattr("server.ask.resolvers.spoiler_policy.nba_schedule.get_season_schedule", lambda *args, **kwargs: schedule)
    assert not outcome_may_reveal_result(_date_stat(day))


def test_play_in_dates_and_missing_schedules_may_reveal_results(monkeypatch):
    day = date(2024, 4, 17)
    schedule = SeasonSchedule("2023-24", SOURCE_SCHEDULE, frozenset({day.isoformat()}), {
        "0052300101": {"gameId": "0052300101", "gameDateEst": day.isoformat()},
    })
    monkeypatch.setattr("server.ask.resolvers.spoiler_policy.nba_schedule.get_season_schedule", lambda *args, **kwargs: schedule)
    assert outcome_may_reveal_result(_date_stat(day))

    def unavailable(*args, **kwargs):
        raise RuntimeError("schedule down")
    monkeypatch.setattr("server.ask.resolvers.spoiler_policy.nba_schedule.get_season_schedule", unavailable)
    assert outcome_may_reveal_result(_date_stat(date(2024, 1, 15)))
