import datetime as dt
from zoneinfo import ZoneInfo

import pytest

from server.ask.candidates import CandidateLookupService
from server.ask.candidates.teams import load_records
from server.ask.models.request import AskContext

REF = dt.datetime(2026, 3, 18, 20, 0, tzinfo=ZoneInfo("America/New_York"))
THUNDER, HORNETS, PELICANS = 1610612760, 1610612766, 1610612740


@pytest.fixture(scope="module")
def service():
    return CandidateLookupService()


def teams(service, question):
    return service.lookup(question, AskContext(reference_time=REF)).sets["team"]


def team_ids(team_set):
    return [c.value.team.team_id for c in team_set.candidates]


def test_franchise_records_cover_every_current_team_once():
    from nba_api.stats.static import teams as static_teams  # bundled data, no network

    records = load_records()
    current = {r.team_id: r for r in records if r.last_season is None}
    expected = {t["id"]: t for t in static_teams.get_teams()}
    assert set(current) == set(expected)
    for team_id, record in current.items():
        assert record.full_name == expected[team_id]["full_name"]
        assert record.abbreviation == expected[team_id]["abbreviation"]


def test_franchise_name_windows_do_not_overlap():
    by_team = {}
    for record in load_records():
        by_team.setdefault(record.team_id, []).append(record)
    for records in by_team.values():
        records.sort(key=lambda r: r.first_season)
        for earlier, later in zip(records, records[1:], strict=False):
            assert earlier.last_season is not None and earlier.last_season < later.first_season


def test_historical_name_resolves_in_its_era(service):
    team_set = teams(service, "Sonics vs Bulls 1996 Finals")
    assert team_ids(team_set) == [THUNDER, 1610612741]
    sonics = team_set.candidates[0]
    assert sonics.value.team.name == "Seattle SuperSonics"
    assert sonics.value.team.tricode == "SEA"
    assert sonics.value.valid_to == dt.date(2008, 6, 30)


def test_historical_name_outside_its_era_is_not_mapped_to_the_current_team(service):
    team_set = teams(service, "Seattle SuperSonics first round 2015")
    assert team_set.status == "no_candidates"
    assert team_set.unmatched_text == ["Seattle SuperSonics"]
    assert THUNDER not in team_ids(team_set)


def test_relative_dates_date_the_team_name_too(service):
    assert teams(service, "Sonics games last week").status == "no_candidates"
    assert team_ids(teams(service, "Hornets vs Magic tonight")) == [HORNETS, 1610612753]


@pytest.mark.parametrize("question, expected", [
    ("How did the Hornets do in the 2000 playoffs?", HORNETS),
    ("Who won the Hornets first round series in 2008?", PELICANS),
    ("How did the Bullets do in the 1978 Finals?", 1610612764),
    ("How far did the Minneapolis Lakers go in the 1954 playoffs?", 1610612747),
    ("How did the Royals do in the 1951 postseason?", 1610612758),
    ("Who did the New Jersey Nets play in the 2003 Finals?", 1610612751),
])
def test_shared_or_historical_names_follow_dated_records(service, question, expected):
    assert team_ids(teams(service, question)) == [expected]


def test_undated_shared_nickname_offers_every_franchise(service):
    team_set = teams(service, "Hornets history")
    assert set(team_ids(team_set)) == {HORNETS, PELICANS}
    assert team_set.candidates[0].value.team.team_id == HORNETS  # the current name ranks first


def test_aliases_cities_and_tricodes(service):
    assert team_ids(teams(service, "Cavs games")) == [1610612739]
    assert teams(service, "Cavs games").candidates[0].source == "alias"
    assert set(team_ids(teams(service, "LA games last night"))) == {1610612747, 1610612746}
    assert team_ids(teams(service, "BOS vs NYK")) == [1610612738, 1610612752]
    # Tricodes and capitalized aliases need capitals: "was" and "min" are ordinary words.
    assert teams(service, "what was the score in min 3").status == "not_mentioned"


def test_unknown_team_name_abstains(service):
    team_set = teams(service, "How many points did the Seattle Pilots score yesterday?")
    assert team_set.status == "no_candidates"
    assert team_set.candidates == []
