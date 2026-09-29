import datetime as dt

import pytest

from server.ask.eval import builders as b
from server.ask.interpreters.cascade import PolicyThresholds, ThresholdCascadePolicy
from server.ask.models.common import DateComponents
from server.ask.models.interpreter import (
    FieldInterpretation,
    InterpreterMetadata,
    InterpreterOutput,
)
from server.ask.models.request import AskContext
from server.ask.normalize import Normalizer
from server.ask.protocols import CascadeAttempt, CascadePolicy, CascadeState

CONTEXT = AskContext(reference_time=dt.datetime.fromisoformat("2026-09-29T12:00:00-04:00"))
CLE = b.team(1610612739, "CLE", "Cleveland Cavaliers")
LAST_WEEK = b.date(0, "last week", DateComponents(kind="relative", relative="last_week"),
                   start=dt.date(2026, 9, 21), end=dt.date(2026, 9, 27))
JAN_23 = b.date(1, "January 23", DateComponents(kind="calendar_date", month=1, day=23), unresolved="year_required")
CANDIDATES = b.lookup_result([CLE, LAST_WEEK, JAN_23])

JEV = "jev-1.13.0"
LUNA = "gpt-6-luna"
CASCADE = ThresholdCascadePolicy(JEV, fallback=("openai_responses", LUNA))
JEV_ONLY = ThresholdCascadePolicy(JEV)


def meta(model=JEV):
    adapter = "jev" if model == JEV else "openai_responses"
    return InterpreterMetadata(adapter=adapter, provider="x", model=model, latency_ms=5)


def sel(field, value, confidence=0.95):
    return FieldInterpretation(field=field, status="selected", selected=[value], confidence=confidence)


def attempt(*fields, outcome="interpreted", model=JEV, reason=None, error=None):
    out = InterpreterOutput(outcome=outcome, fields=list(fields), unsupported_reason=reason,
                            error_code=error, metadata=meta(model))
    norm = Normalizer().normalize(out, CANDIDATES, CONTEXT) if outcome == "interpreted" else None
    return CascadeAttempt(output=out, normalization=norm)


def state(*attempts, fallback_enabled=True, budget=1.0, ms=20_000, expanded=()):
    return CascadeState(attempts=list(attempts), candidates=CANDIDATES, expanded_fields=list(expanded),
                        fallback_enabled=fallback_enabled, remaining_budget_usd=budget, remaining_ms=ms)


def test_policies_satisfy_protocol():
    assert isinstance(CASCADE, CascadePolicy)
    with pytest.raises(ValueError):
        ThresholdCascadePolicy(JEV, fallback=("jev", JEV))


def test_confident_complete_request_is_accepted():
    a = attempt(sel("intent", "game_search"), sel("date", "date:0"), sel("teams", CLE.id))
    assert CASCADE.decide(state(a)).action == "accept"


def test_low_confidence_relevant_field_falls_back_once():
    a = attempt(sel("intent", "game_search"), sel("date", "date:0", confidence=0.4))
    decision = CASCADE.decide(state(a))
    assert (decision.action, decision.adapter) == ("fallback", "openai_responses")
    # Without a fallback, a shaky read is clarified rather than executed.
    decision = JEV_ONLY.decide(state(a))
    assert (decision.action, decision.field) == ("clarify", "date")


def test_low_confidence_irrelevant_field_does_not_block():
    a = attempt(sel("intent", "game_search"), sel("date", "date:0"),
                FieldInterpretation(field="player", status="absent", confidence=0.2))
    assert CASCADE.decide(state(a)).action == "accept"


def test_confident_missing_detail_is_clarified_without_fallback():
    a = attempt(sel("intent", "game_search"), sel("date", JAN_23.id))  # year_required
    decision = CASCADE.decide(state(a))
    assert (decision.action, decision.field) == ("clarify", "date")


def test_uncertain_clarification_gets_one_fallback():
    a = attempt(sel("intent", "game_search", confidence=0.4),
                FieldInterpretation(field="date", status="absent", confidence=0.5))
    assert CASCADE.decide(state(a)).action == "fallback"


def test_no_matching_candidate_expands_once_then_clarifies():
    a = attempt(sel("intent", "game_search"), sel("date", "date:0"),
                FieldInterpretation(field="teams", status="no_matching_candidate", confidence=0.9))
    decision = CASCADE.decide(state(a))
    assert (decision.action, decision.field) == ("expand_candidates", "teams")
    decision = CASCADE.decide(state(a, a, expanded=["team"]))
    assert (decision.action, decision.field) == ("clarify", "teams")


def test_unsupported_passes_through():
    a = attempt(outcome="unsupported", reason="career_stats")
    assert CASCADE.decide(state(a)).action == "unsupported"
    per_game = attempt(sel("intent", "boxscore_stat"), sel("aggregation", "per_game"))
    assert CASCADE.decide(state(per_game)).action == "unsupported"


@pytest.mark.parametrize("outcome", ["unreliable", "unavailable"])
def test_unreliable_or_unavailable_primary_falls_back_when_allowed(outcome):
    a = attempt(outcome=outcome, error="timeout" if outcome == "unavailable" else None)
    assert CASCADE.decide(state(a)).action == "fallback"
    assert CASCADE.decide(state(a, fallback_enabled=False)).action == "fail"
    assert CASCADE.decide(state(a, budget=0.0)).action == "fail"
    assert CASCADE.decide(state(a, ms=500)).action == "fail"
    assert JEV_ONLY.decide(state(a)).action == "fail"


def test_fallback_is_used_at_most_once():
    first = attempt(outcome="unreliable")
    second = attempt(outcome="unreliable", model=LUNA)
    assert CASCADE.decide(state(first, second)).action == "fail"


def test_fallback_result_without_confidence_is_accepted_after_python_validation():
    first = attempt(outcome="unreliable")
    luna = attempt(FieldInterpretation(field="intent", status="selected", selected=["game_search"]),
                   FieldInterpretation(field="date", status="selected", selected=["date:0"]), model=LUNA)
    assert CASCADE.decide(state(first, luna)).action == "accept"


def test_both_unreliable_clarifies_when_user_can_resolve():
    first = attempt(sel("intent", "game_search", confidence=0.4),
                    FieldInterpretation(field="date", status="ambiguous", alternatives=["date:0", JAN_23.id],
                                        confidence=0.4))
    luna = attempt(outcome="unavailable", model=LUNA, error="timeout")
    decision = CASCADE.decide(state(first, luna))
    assert (decision.action, decision.field) == ("clarify", "date")


def test_invalid_fallback_output_is_never_executed():
    first = attempt(outcome="unreliable")
    luna = attempt(FieldInterpretation(field="intent", status="selected", selected=["game_search"]),
                   FieldInterpretation(field="date", status="selected", selected=["date:7"]), model=LUNA)
    assert luna.normalization.status == "invalid"
    assert CASCADE.decide(state(first, luna)).action == "fail"


def test_thresholds_are_configurable():
    strict = ThresholdCascadePolicy(JEV, fallback=("openai_responses", LUNA),
                                    thresholds=PolicyThresholds(accept_min=0.99))
    a = attempt(sel("intent", "game_search"), sel("date", "date:0", confidence=0.97))
    assert CASCADE.decide(state(a)).action == "accept"
    assert strict.decide(state(a)).action == "fallback"
