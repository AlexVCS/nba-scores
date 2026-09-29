import datetime as dt

import pytest

from server.ask.candidates.locations import location_value
from server.ask.candidates.lookup import CandidateLookupService
from server.ask.models.interpreter import FieldInterpretation, InterpreterMetadata, InterpreterOutput
from server.ask.models.request import AskContext
from server.ask.normalize import Normalizer
from server.ask.resolvers import games
from server.ask.resolvers.errors import NotFoundError
from server.tests.ask.test_resolvers_games import DAY, boards, rng  # noqa: F401

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
    assert (location.city, sorted(h.team.tricode for h in location.homes)) == ("New York", ["BKN", "NYK"])
    # The Nets count only from their 2012 move to Brooklyn.
    nets = 1610612751
    assert location.hosts(nets, dt.date(2013, 1, 1)) and not location.hosts(nets, dt.date(2005, 1, 1))


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
    new_york = location_value("new_york").location
    result = games.search_games(rng(DAY, DAY + dt.timedelta(days=1)), location=new_york).result
    assert [g.game.gameId for day in result.days for g in day.games] == ["0022300602"]
    with pytest.raises(NotFoundError) as missing:
        games.search_games(rng(DAY + dt.timedelta(days=1)), location=new_york)
    assert missing.value.reason == "no_games_at_location"


def test_no_team_based_there_on_those_dates():
    # The Nets played in New Jersey in 2005; nothing is fetched.
    with pytest.raises(NotFoundError) as missing:
        games.search_games(rng(dt.date(2005, 1, 1)), location=location_value("brooklyn").location)
    assert missing.value.reason == "no_team_at_location"


def test_former_cities_map_to_the_franchise_then():
    seattle = location_value("seattle").location
    thunder = 1610612760
    assert seattle.hosts(thunder, dt.date(2005, 1, 1)) and not seattle.hosts(thunder, dt.date(2009, 1, 1))


@pytest.mark.parametrize("question", [
    "I want the Nets schedule for January 2, 2002, when they were in New Jersey.",
    "Sonics games on January 5, 2005, back when they were still based in Seattle",
    "the Grizzlies schedule for March 1, 2000 while the Grizzlies were in Vancouver",
])
def test_where_a_team_was_based_is_not_a_venue(question):
    # Franchise history, not "games played there": no home-only filter for any tier to pick.
    result, location, _ = sets(question)
    assert location == [] and result.sets["location"].status == "not_mentioned"


def test_nets_schedule_when_they_were_in_new_jersey_has_no_venue_filter():
    result, _, teams = sets("I want the Nets schedule for January 2, 2002, when they were in New Jersey.")
    assert teams == ["team:1610612751"]
    output = InterpreterOutput(outcome="interpreted", fields=[
        FieldInterpretation(field="intent", status="selected", selected=["game_search"]),
        FieldInterpretation(field="date", status="selected", selected=[result.sets["date"].candidates[0].id]),
        FieldInterpretation(field="teams", status="selected", selected=teams),
    ], metadata=InterpreterMetadata(adapter="jev", provider="x", model="jev-1.13.0", latency_ms=1))
    request = Normalizer().normalize(output, result, CONTEXT).request
    assert request.location is None and [t.tricode for t in request.teams] == ["NJN"]


@pytest.mark.parametrize("question, location", [
    ("Nets games in New Jersey on January 2, 2002", ["location:new_jersey"]),
    ("Did the Bucks have a game in Boston on December 6, 2024?", ["location:boston"]),
    ("Were there games in Seattle on January 5, 2005?", ["location:seattle"]),
])
def test_explicit_venue_wording_keeps_the_filter(question, location):
    assert sets(question)[1] == location
