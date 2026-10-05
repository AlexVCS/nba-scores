import datetime as dt
from zoneinfo import ZoneInfo

import pytest

from server.ask.candidates import CandidateLookupService
from server.ask.candidates.aliases import get_alias_mapping
from server.ask.candidates.players import get_player_index
from server.ask.models.request import AskContext

REF = dt.datetime(2026, 3, 18, 20, 0, tzinfo=ZoneInfo("America/New_York"))
CONTEXT = AskContext(reference_time=REF)


@pytest.fixture(scope="module")
def service():
    return CandidateLookupService()


def players(service, question):
    return service.lookup(question, CONTEXT).sets["player"]


def ids(player_set):
    return [c.value.player.player_id for c in player_set.candidates]


def test_every_player_alias_points_at_the_catalog():
    index = get_player_index()
    for alias, player_ids in get_alias_mapping().players.items():
        assert all(pid in index.players for pid in player_ids), alias


@pytest.mark.parametrize("question, expected", [
    ("What was Jalen Brunson's stat line yesterday?", 1628973),
    ("How many assists did King James have on March 5, 2026?", 2544),
    ("SGA's points vs the Spurs", 1628983),
    ("What did Nikola Jokic score in game 1?", 203999),  # catalog spells it Jokić
    ("Jimmy Butler points", 202710),  # catalog: Jimmy Butler III
    ("how many assists did lebron have yesterday", 2544),  # no capitals anywhere
    ("How many points did Ant score on Christmas Day 2025?", 1630162),
])
def test_resolves_names_and_aliases(service, question, expected):
    assert ids(players(service, question))[0] == expected


def test_alias_adds_a_candidate_without_hiding_catalog_matches(service):
    player_set = players(service, "How many points did Kobe score?")
    assert ids(player_set)[0] == 977
    assert player_set.candidates[0].source == "alias"
    assert len(player_set.candidates) > 1  # Kobe Brown, Kobe Bufkin, ... remain


def test_acronym_aliases_need_capitals(service):
    assert 201142 in ids(players(service, "KD points last night"))
    assert 201142 not in ids(players(service, "kd points last night"))


def test_first_name_alone_stays_ambiguous_and_bounded(service):
    player_set = players(service, "How many rebounds did Jalen have last night?")
    assert len(player_set.candidates) == 8  # per-phrase bound
    assert player_set.truncated
    assert all(c.value.player.name.startswith("Jalen") for c in player_set.candidates)


def test_same_name_players_are_all_offered(service):
    assert set(ids(players(service, "Patrick Ewing points"))) == {121, 201607}
    assert set(ids(players(service, "Tatum points"))) >= {1628369, 78294}


def test_unknown_full_name_is_not_split_into_other_players(service):
    player_set = players(service, "How many points did Dwight Schrute score last night?")
    assert player_set.status == "no_candidates"
    assert player_set.unmatched_text == ["Dwight Schrute"]
    assert 2730 not in ids(player_set)  # Dwight Howard is not evidence of anything


def test_expand_widens_one_field_within_the_limit(service):
    question = "How many points did Dwight Schrute score last night?"
    previous = players(service, question)
    wider = service.expand(question, CONTEXT, "player", previous)
    assert wider.status == "candidates"
    assert 2730 in ids(wider)
    assert len(wider.candidates) <= 12


def test_expand_returns_previous_when_nothing_new(service):
    question = "Games on February 14"
    previous = service.lookup(question, CONTEXT).sets["date"]
    assert service.expand(question, CONTEXT, "date", previous) is previous


def test_close_misspelling_is_a_fuzzy_candidate(service):
    player_set = players(service, "How many points did Zion Williamsen score yesterday?")
    assert ids(player_set) == [1629627]
    assert player_set.candidates[0].match_score < 1


def test_fuzzy_surname_limit_does_not_hide_other_close_candidates(service):
    player_set = players(service, "How many points did Akins score?")
    names = {candidate.value.player.name for candidate in player_set.candidates}
    assert {"Jim Eakins", "Chucky Atkins", "Keith Askins", "Rawle Alkins", "Henry Akin"}.issubset(names)
    assert not player_set.truncated


def test_candidates_carry_career_span_but_no_current_team(service):
    [jordan] = players(service, "Michael Jordan points in game 6").candidates
    assert jordan.value.first_season == "1984-85"
    assert jordan.value.last_season == "2002-03"
    assert jordan.value.team_ids == []  # never inferred from rosters
