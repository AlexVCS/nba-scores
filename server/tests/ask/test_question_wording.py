"""Everyday words in a question that used to be read as a player, a team or a round."""
import datetime as dt

from server.ask.candidates.lookup import CandidateLookupService
from server.ask.models.interpreter import FieldInterpretation, InterpreterMetadata, InterpreterOutput
from server.ask.models.request import AskContext
from server.ask.normalize import Normalizer
from server.ask.season_scope import normalize_question

CONTEXT = AskContext(reference_time=dt.datetime.fromisoformat("2026-09-30T12:00:00-04:00"))


def lookup(question):
    return CandidateLookupService().lookup(question, CONTEXT)


def named(candidates, field):
    return [c for c in candidates.sets[field].candidates if c.source != "app_context"]


def normalized(question, intent, **fields):
    """Normalize as if the interpreter chose ``intent`` and each lone candidate."""
    candidates = lookup(question)
    for field in ("season", "player", "teams"):
        found = named(candidates, "team" if field == "teams" else field)
        if found and field not in fields:
            fields[field] = found[0].id
    output = InterpreterOutput(
        outcome="interpreted", metadata=InterpreterMetadata(adapter="jev", provider="test", model="test", latency_ms=0),
        fields=[FieldInterpretation(field=k, status="selected", selected=[v], confidence=1)
                for k, v in {"intent": intent, **fields}.items()])
    return normalize_question(Normalizer(), output, candidates, CONTEXT, question)


def test_a_regular_season_mark_is_not_a_player_named_mark():
    question = "What was Milwaukee's regular-season mark in 1970-71?"
    assert named(lookup(question), "player") == []
    n = normalized(question, "team_records")
    assert n.status == "valid" and n.request.team.tricode == "MIL" and n.request.season == "1970-71"
    assert {c.value.player.name for c in named(lookup("How many points did Mark score in 2023-24?"), "player")} >= {"Mark Williams"}
    assert [c.value.player.name for c in named(lookup("mark jackson assists 1996-97"), "player")] == ["Mark Jackson"]


def test_rank_is_not_a_player():
    question = "Kobe's all-time rank in points"
    assert all(c.matched_text == "Kobe's" for c in named(lookup(question), "player"))
    kobe = next(c.id for c in named(lookup(question), "player") if c.value.player.player_id == 977)
    n = normalized(question, "career_stats", player=kobe, stat="points")
    assert n.status == "valid" and n.request.view == "player_rank" and n.request.stat.aggregation == "total"


def test_a_scoring_title_is_not_the_finals():
    question = "Who won the scoring title in 2013-14?"
    assert named(lookup(question), "round") == []
    n = normalized(question, "season_leaders", stat="points")
    assert n.status == "valid" and n.request.stat.aggregation == "per_game" and n.request.season == "2013-14"
    assert named(lookup("Who won the division title in 2013-14?"), "round") == []
    assert [c.value.round for c in named(lookup("Who won the title in 2014?"), "round")] == ["finals"]


def test_a_misspelled_team_name_is_offered_as_that_team():
    teams = named(lookup("Warriros games on March 7, 2016"), "team")
    assert [(c.value.team.tricode, c.matched_text) for c in teams] == [("GSW", "Warriros")]
    assert [c.value.team.tricode for c in named(lookup("Did the Celtcis win on March 7, 2016?"), "team")] == ["BOS"]
    # Short names are not matched loosely, and a real player name is never a team typo.
    assert named(lookup("Heath games on March 7, 2016"), "team") == []
    assert named(lookup("Bullock points on March 7, 2016"), "team") == []


def test_best_record_with_no_team_is_the_standings():
    n = normalized("Which team had the best record in 2015-16?", "team_records")
    assert n.status == "valid" and n.request.team is None and n.request.standings_scope == "league"
    n = normalized("Who had the worst record in 2011-12?", "team_records")
    assert n.status == "valid" and n.request.team is None
    # A named team's best record is franchise history, which the standings cannot answer.
    assert normalized("What was the Lakers' best record in 2015-16?", "team_records").status == "unsupported"
    assert normalized("Which team had the best home record in 2015-16?", "team_records").status == "unsupported"
