"""Regressions from the 2026-09-29 external review of cdc6c68."""
import datetime as dt

from server.ask.eval import builders as b
from server.ask.models.common import DateComponents
from server.ask.models.interpreter import FieldInterpretation, InterpreterMetadata, InterpreterOutput
from server.ask.models.request import AskContext
from server.ask.normalize import Normalizer

CONTEXT = AskContext(reference_time=dt.datetime.fromisoformat("2026-03-08T12:00:00-05:00"))
BRUNSON = b.player(1628973, "Jalen Brunson", matched="Jalen")
GREEN = b.player(1630224, "Jalen Green", matched="Jalen")
YESTERDAY = b.date(0, "yesterday", DateComponents(kind="relative", relative="yesterday"), start=dt.date(2026, 3, 7), end=dt.date(2026, 3, 7))


def boxscore(candidates):
    output = InterpreterOutput(outcome="interpreted", fields=[
        FieldInterpretation(field="intent", status="selected", selected=["boxscore_stat"]),
        FieldInterpretation(field="stat_scope", status="selected", selected=["player"]),
        FieldInterpretation(field="stat", status="selected", selected=["points"]),
        FieldInterpretation(field="player", status="selected", selected=[BRUNSON.id]),
        FieldInterpretation(field="date", status="selected", selected=["date:0"]),
    ], metadata=InterpreterMetadata(adapter="jev", provider="x", model="jev-1.13.0", latency_ms=1))
    return Normalizer().normalize(output, candidates, CONTEXT)


def test_selection_from_a_truncated_player_list_is_clarified():
    result = boxscore(b.lookup_result([BRUNSON, GREEN, YESTERDAY], truncated=["player"]))
    assert (result.status, result.clarify_field, result.clarify_reason) == ("needs_clarification", "player", "ambiguous")


def test_selection_from_a_complete_list_still_executes():
    assert boxscore(b.lookup_result([BRUNSON, GREEN, YESTERDAY])).status == "valid"


def lookup_players(question):
    from server.ask.candidates.lookup import CandidateLookupService

    result = CandidateLookupService().lookup(question, CONTEXT)
    return [c.label.split(" (")[0] for c in result.sets["player"].candidates]


def test_sentence_case_does_not_disable_lowercase_names():
    for question in ("How many points did lebron have yesterday?",
                     "how many points did lebron have yesterday?",
                     "How many points did lebron have against the Celtics in the NBA Finals?"):
        assert lookup_players(question) == ["LeBron James"], question


def test_mixed_case_still_requires_capitalized_names():
    # The user capitalizes names ("Tatum"), so the lowercase word "green" is not a name.
    assert "Jalen Green" not in lookup_players("Did Tatum score more than the green team?")
