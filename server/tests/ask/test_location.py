import datetime as dt

import pytest

from server.ask.candidates.lookup import CandidateLookupService
from server.ask.models.interpreter import FieldInterpretation, InterpreterMetadata, InterpreterOutput
from server.ask.models.request import AskContext
from server.ask.normalize import Normalizer
from server.ask.resolvers import games
from server.ask.resolvers.errors import NotFoundError
from server.tests.ask.test_resolvers_games import DAY, boards, rng  # noqa: F401
from server.tests.ask.test_resolvers_support import tid

CONTEXT = AskContext(reference_time=dt.datetime.fromisoformat("2026-03-08T12:00:00-05:00"))
LOOKUP = CandidateLookupService()


def sets(question):
    result = LOOKUP.lookup(question, CONTEXT)
    return result, [c.id for c in result.sets["location"].candidates], [c.id for c in result.sets["team"].candidates]


@pytest.mark.parametrize("question, location, teams", [
    ("What NBA games are on tonight in New York?", ["location:new_york"], []),
    ("games in LA this week", ["location:los_angeles"], []),
    ("Knicks games at Boston in March", ["location:boston"], ["team:1610612752"]),
    ("Boston games last week", [], ["team:1610612738"]),
    ("how did Tatum do in Boston's game last night", [], ["team:1610612738"]),
])
def test_a_city_after_in_or_at_is_a_venue_not_a_team(question, location, teams):
    _, got_location, got_teams = sets(question)
    assert (got_location, got_teams) == (location, teams)


def test_new_york_means_knicks_and_nets_home_games():
    result, _, _ = sets("games tonight in New York")
    location = result.by_id("location:new_york").value.location
    assert (location.city, sorted(t.tricode for t in location.teams)) == ("New York", ["BKN", "NYK"])


def test_normalizer_carries_the_location_into_game_search():
    result, _, _ = sets("What NBA games are on tonight in New York?")
    date_id = result.sets["date"].candidates[0].id
    output = InterpreterOutput(outcome="interpreted", fields=[
        FieldInterpretation(field="intent", status="selected", selected=["game_search"]),
        FieldInterpretation(field="date", status="selected", selected=[date_id]),
        FieldInterpretation(field="location", status="selected", selected=["location:new_york"]),
    ], metadata=InterpreterMetadata(adapter="jev", provider="x", model="jev-1.13.0", latency_ms=1))
    request = Normalizer().normalize(output, result, CONTEXT).request
    assert request.teams == [] and request.location.city == "New York"


def test_venue_filter_keeps_only_home_games(boards):  # noqa: F811
    # NYK hosts CLE on the 15th; on the 16th NYK plays at MIA.
    result = games.search_games(rng(DAY, DAY + dt.timedelta(days=1)), home_team_ids=[tid("NYK"), 1610612751]).result
    assert [g.game.gameId for day in result.days for g in day.games] == ["0022300602"]
    with pytest.raises(NotFoundError) as missing:
        games.search_games(rng(DAY + dt.timedelta(days=1)), home_team_ids=[tid("NYK")])
    assert missing.value.reason == "no_games_at_location"
