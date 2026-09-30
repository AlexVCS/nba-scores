import datetime as dt
import json
from zoneinfo import ZoneInfo

import pytest

from server.ask.candidates import CandidateLookupService, alias_version
from server.ask.candidates.aliases import ALIAS_PATH, _parse
from server.ask.candidates.evaluation import DEV_SET, candidate_key, evaluate
from server.ask.models.candidates import CANDIDATE_FIELDS, CandidateLookupResult
from server.ask.models.request import AskContext
from server.ask.protocols import CandidateLookup

NY = ZoneInfo("America/New_York")
REF = dt.datetime(2026, 3, 18, 20, 0, tzinfo=NY)
OFFSEASON = dt.datetime(2026, 9, 29, 12, 0, tzinfo=NY)


@pytest.fixture(scope="module")
def service():
    return CandidateLookupService()


def lookup(service, question, **context):
    return service.lookup(question, AskContext(reference_time=context.pop("reference_time", REF), **context))


def keys(result, field):
    return [candidate_key(c) for c in result.sets[field].candidates]


def test_implements_the_contract_protocol(service):
    assert isinstance(service, CandidateLookup)
    assert service.alias_version == alias_version()


def test_result_round_trips_through_the_contract_model(service):
    result = lookup(service, "How many points did Tatum score in game 4 of the 2024 Finals?")
    assert set(result.sets) == set(CANDIDATE_FIELDS)
    again = CandidateLookupResult.model_validate_json(result.model_dump_json())
    assert again == result
    assert result.by_id("player:1628369") is not None
    assert keys(result, "season") == ["2023-24"]
    assert keys(result, "round") == ["finals"]
    assert keys(result, "game_number") == [4]
    [tatum] = [c for c in result.sets["player"].candidates if c.id == "player:1628369"]
    assert tatum.matched_text == "Tatum" and tatum.span == (20, 25)


def test_off_topic_question_mentions_nothing(service):
    result = lookup(service, "Tell me a joke")
    assert all(s.status == "not_mentioned" for s in result.sets.values())


def test_no_candidates_is_explicit(service):
    result = lookup(service, "Who won game 9 of the play-in?")
    assert result.sets["game_number"].status == "no_candidates"
    assert result.sets["game_number"].unmatched_text == ["game 9"]
    assert result.sets["round"].status == "no_candidates"


@pytest.mark.parametrize("question, reference_time, expected", [
    ("Who won the 2016 Finals?", REF, ["2015-16"]),
    ("Lakers 2016 record", REF, ["2015-16", "2016-17"]),  # no playoff language: both seasons
    ("Summarize the 2023-24 season", REF, ["2023-24"]),
    ("the '98 Finals", REF, ["1997-98"]),
    ("Clippers in the playoffs last season", REF, ["2024-25"]),
    ("Summarize last year's playoffs", OFFSEASON, ["2024-25"]),
    ("Who won the Knicks-Pistons series this year?", OFFSEASON, ["2025-26"]),
    ("How are the Knicks doing this season?", OFFSEASON, ["2025-26", "2026-27"]),
])
def test_seasons(service, question, reference_time, expected):
    assert keys(lookup(service, question, reference_time=reference_time), "season") == expected


def test_final_score_is_not_playoff_language(service):
    result = lookup(service, "What was the final score of the Hornets game in 2002?")
    assert keys(result, "season") == ["2001-02", "2002-03"]


def test_page_playoff_pointer_uses_the_page_season(service):
    result = lookup(service, "Who won these playoffs?", reference_time=REF,
                    route="playoffs", playoff_season="2015-16")
    [candidate] = result.sets["season"].candidates
    assert candidate.value.season == "2015-16"
    assert candidate.source == "app_context"
    explicit = lookup(service, "Who won these playoffs in 2016?", reference_time=REF,
                      route="playoffs", playoff_season="2015-16")
    assert keys(explicit, "season") == ["2015-16"]


def test_invalid_season_is_not_repaired(service):
    result = lookup(service, "Summarize the 2023-25 season")
    assert result.sets["season"].status == "no_candidates"


@pytest.mark.parametrize("question, expected", [
    ("Who won the 2023 Western Conference Finals?", ["conference_finals.west"]),
    ("Celtics Heat 2012 East finals", ["conference_finals.east"]),
    ("Knicks Pacers second round 2025", ["conference_semifinals"]),
    ("Hornets first round series in 2008", ["first_round"]),
    ("Hornets first-round series in 2008", ["first_round"]),
    ("Knicks second-round series", ["conference_semifinals"]),
    ("Lakers third-round series", ["conference_finals"]),
    ("2014 WCF game 6", ["conference_finals.west"]),
])
def test_rounds(service, question, expected):
    assert keys(lookup(service, question), "round") == expected


def test_app_context_season_only_when_the_question_points_at_it(service):
    result = lookup(service, "What happened in this series?", reference_time=OFFSEASON,
                    route="series", playoff_season="2024-25")
    [candidate] = result.sets["season"].candidates
    assert candidate.source == "app_context" and candidate.value.season == "2024-25"
    result = lookup(service, "Tell me a joke", route="series", playoff_season="2024-25")
    assert result.sets["season"].status == "not_mentioned"


def test_app_context_date(service):
    result = lookup(service, "Who scored the most that night?", view_date=dt.date(2026, 2, 1))
    [candidate] = result.sets["date"].candidates
    assert candidate.source == "app_context"
    assert candidate.value.resolved.start == dt.date(2026, 2, 1)
    assert lookup(service, "Who scored the most that night?").sets["date"].status == "no_candidates"


def test_bounds_hold_for_a_crowded_question(service):
    question = "Jalen Anthony Jordan Green Davis Johnson Williams Smith and Brown games " \
               "on Monday Tuesday Wednesday Thursday Friday Saturday Sunday"
    result = lookup(service, question)
    total = sum(len(s.candidates) for s in result.sets.values())
    assert total <= 48
    assert all(len(s.candidates) <= 12 for s in result.sets.values())
    assert result.sets["player"].truncated


def test_long_question_is_cut_to_the_contract_limit(service):
    result = lookup(service, "Knicks " + "x" * 400 + " Celtics")
    assert [c.value.team.team_id for c in result.sets["team"].candidates] == [1610612752]


def test_alias_file_rejects_malformed_entries():
    data = json.loads(ALIAS_PATH.read_bytes())
    data["players"]["Bad"] = ["not an id"]
    with pytest.raises(ValueError):
        _parse(json.dumps(data).encode())


def test_alias_mapping_has_no_statistical_definitions():
    data = json.loads(ALIAS_PATH.read_bytes())
    assert set(data) == {"_comment", "teams", "cities", "players"}


def test_dev_set_is_labeled_as_development():
    data = json.loads(DEV_SET.read_text())
    assert "DEVELOPMENT SET" in data["_comment"]
    assert len(data["questions"]) >= 60
    intents = {q["intent"] for q in data["questions"]}
    assert intents == {"game_search", "boxscore_stat", "playoff_series", "postseason_summary", "unsupported"}


def test_dev_set_regression():
    """Guards the measured development numbers; not a release gate."""
    report = evaluate(repeats=1)
    assert report.recall() >= 0.97, report.misses
    assert report.abstain_correct == report.abstain_total, report.misses
    assert report.ambiguous_correct == report.ambiguous_total, report.misses
    assert report.forbidden_leaks == 0, report.misses


@pytest.mark.parametrize("question", [
    "Any Suns games on the day I have open?",
    "List the games for the date I'm looking at",
    "What games were played on the date on my screen?",
    "Show games from the displayed date",
    "Scores for the day that is currently selected",
])
def test_app_context_date_from_on_screen_wording(service, question):
    result = lookup(service, question, route="scores", view_date=dt.date(2023, 1, 9))
    [candidate] = result.sets["date"].candidates
    assert candidate.source == "app_context"
    assert candidate.value.resolved.start == dt.date(2023, 1, 9)


def test_on_screen_wording_without_a_page_date_offers_nothing(service):
    result = lookup(service, "Any Suns games on the day I have open?")
    assert result.sets["date"].status == "no_candidates"
    assert lookup(service, "What date is it today?").sets["date"].candidates[0].source != "app_context"


@pytest.mark.parametrize(("question", "number"), [
    ("Kawhi's steals in the fourth game of the 2019 Finals", 4),
    ("Show Nash's assists from the 2nd game of the 2006 West semifinals", 2),
    ("What did Pierce score in the seventh Finals game of 2010?", 7),
])
def test_ordinal_game_numbers_in_playoff_questions(service, question, number):
    result = lookup(service, question)
    [candidate] = result.sets["game_number"].candidates
    assert candidate.value.game_number == number


def test_ordinal_games_outside_playoff_wording_are_not_series_games(service):
    result = lookup(service, "Knicks first game of the 2019 season")
    assert result.sets["game_number"].status == "not_mentioned"


def test_ordinal_beyond_seven_is_reported_not_offered(service):
    result = lookup(service, "the ninth game of the 1999 Finals")
    assert result.sets["game_number"].status == "no_candidates"


@pytest.mark.parametrize(("question", "round_name"), [
    ("Open Utah's opening playoff round in 2021", "first_round"),
    ("Pull up the Knicks' second postseason round from 2023", "conference_semifinals"),
    ("Which series was round one for Phoenix in 2022?", "first_round"),
    ("Show round 2 for the Sixers in 2021", "conference_semifinals"),
])
def test_round_wording_with_playoff_modifiers(service, question, round_name):
    [candidate] = lookup(service, question).sets["round"].candidates
    assert candidate.value.round == round_name


def test_out_of_era_team_word_stays_open_to_player_names(service):
    result = lookup(service, "Show Magic's rebounds from May 14, 1985")
    assert keys(result, "player") and result.sets["player"].candidates[0].value.player.player_id == 77142
    assert result.sets["team"].status == "no_candidates"  # the dropped team name is still reported


def test_in_era_or_team_worded_names_stay_teams(service):
    in_era = lookup(service, "Show Magic's rebounds from May 14, 2010")
    assert in_era.sets["player"].status == "not_mentioned"
    assert in_era.sets["team"].candidates[0].value.team.tricode == "ORL"
    worded = lookup(service, "How did the Magic do in the 1984 playoffs?")
    assert worded.sets["player"].status == "not_mentioned"
    multiword = lookup(service, "Seattle SuperSonics games on Jan 3, 2020")
    assert multiword.sets["player"].status == "not_mentioned"


def test_dismissed_page_date_is_not_offered(service):
    result = lookup(service, "Ignore the date on my screen and list yesterday's games",
                    route="scores", view_date=dt.date(2023, 1, 9))
    assert [c.source for c in result.sets["date"].candidates] == ["date_parser"]
