import json
from pathlib import Path

import pytest

from server.ask.eval.runner import (
    Configuration,
    LabeledCase,
    drive,
    embedded_candidates,
    percentile,
    report,
    run,
)
from server.ask.interpreters.cascade import ThresholdCascadePolicy
from server.ask.interpreters.pricing import SpendGuard
from server.ask.models.interpreter import (
    FieldInterpretation,
    InterpreterMetadata,
    InterpreterOutput,
    InterpreterUsage,
)

FIXTURE = Path(__file__).parent / "fixtures" / "eval" / "smoke_hand_built.json"
CASES = [LabeledCase.from_json(c) for c in json.loads(FIXTURE.read_text())["cases"]]
BY_ID = {c.id: c for c in CASES}


def sel(field, *values, confidence=None):
    return FieldInterpretation(field=field, status="selected", selected=list(values), confidence=confidence)


class FakeAdapter:
    """Scripted adapter: question -> list of fields | ("unsupported", reason) | outcome str."""

    provider = "fake"

    def __init__(self, name, model, script, cost=0.001):
        self.name = name
        self.model = model
        self.script = script
        self.cost = cost
        self.calls = 0

    def estimate_cost(self, request):
        return self.cost

    def interpret(self, request):
        self.calls += 1
        meta = InterpreterMetadata(adapter=self.name, provider="fake", model=self.model,
                                   resolved_model=f"{self.model}-resolved", latency_ms=10,
                                   usage=InterpreterUsage(provider_calls=1, cost_usd=self.cost))
        entry = self.script.get(request.question, "unreliable")
        if isinstance(entry, tuple):
            return InterpreterOutput(outcome="unsupported", unsupported_reason=entry[1], metadata=meta)
        if isinstance(entry, str):
            return InterpreterOutput(outcome=entry, metadata=meta,
                                     error_code="timeout" if entry == "unavailable" else None)
        return InterpreterOutput(outcome="interpreted", fields=entry, metadata=meta)


GOOD = {
    "Cavs games last week": [sel("intent", "game_search", confidence=0.95), sel("date", "date:0", confidence=0.9),
                             sel("teams", "team:1610612739", confidence=0.9)],
    "Who won the 2023 NBA Finals?": [sel("intent", "playoff_series", confidence=0.9),
                                     sel("season", "season:2022-23", confidence=0.9),
                                     sel("round", "round:finals", confidence=0.9)],
    "What are LeBron's career points?": ("unsupported", "career_stats"),
}
# Jev-like primary: confident on two, unsure on the Finals question, and guesses a year.
PRIMARY = {
    **GOOD,
    "Who won the 2023 NBA Finals?": [sel("intent", "playoff_series", confidence=0.9),
                                     sel("season", "season:2022-23", confidence=0.5),
                                     sel("round", "round:finals", confidence=0.9)],
    "Lakers vs Celtics on January 23": [sel("intent", "game_search", confidence=0.9),
                                        sel("date", "date:0", confidence=0.9)],
}


def configs(primary, fallback):
    jev_alone = Configuration("jev", primary, ThresholdCascadePolicy("jev-1.13.0"))
    cascade = Configuration("jev->luna", primary, ThresholdCascadePolicy(
        "jev-1.13.0", fallback=("openai_responses", "gpt-6-luna")), fallback=fallback)
    return [jev_alone, cascade]


def test_fixture_cases_are_labeled_and_hand_built():
    doc = json.loads(FIXTURE.read_text())
    assert "NOT valid for the interpreter comparison" in doc["description"]
    assert {c.action for c in CASES} == {"accept", "clarify", "unsupported"}
    assert all(c.candidates.alias_version == "hand-built" for c in CASES)


def test_drive_accepts_and_scores_exact_request():
    primary = FakeAdapter("jev", "jev-1.13.0", GOOD)
    case = BY_ID["smoke-games-last-week"]
    outcome = drive(configs(primary, None)[0], case.question, case.context, case.candidates, guard=SpendGuard(1))
    assert outcome.decision.action == "accept"
    assert outcome.request.dates.start.isoformat() == "2026-09-21"


def test_run_reports_accuracy_guesses_fallback_and_shared_primary_calls():
    primary = FakeAdapter("jev", "jev-1.13.0", PRIMARY)
    luna = FakeAdapter("openai_responses", "gpt-6-luna", GOOD, cost=0.01)
    chosen = [BY_ID[i] for i in ("smoke-games-last-week", "smoke-series-finals", "smoke-career",
                                  "smoke-year-required")]
    cfgs = configs(primary, luna)
    guard = SpendGuard(3.0)
    result = run(chosen, embedded_candidates, cfgs, guard)
    doc = report(chosen, result, cfgs, guard, {"purpose": "test"})

    # The primary was called once per case, shared by both configurations.
    assert primary.calls == len(chosen)
    assert luna.calls == 1  # only the low-confidence Finals read fell back

    alone, cascade = doc["configs"]["jev"], doc["configs"]["jev->luna"]
    assert alone["correct"] == 3 and cascade["correct"] == 4
    assert cascade["fallback_effect_vs_primary_alone"] == {"fixed": ["smoke-series-finals"], "worsened": []}
    assert cascade["fallback_rate"] == 0.25
    # January 23 without a year: the normalizer turns the date pick into year_required.
    assert all(s["action"] == "clarify" for s in doc["cases"]["jev"] if s["case_id"] == "smoke-year-required")
    assert cascade["cost_per_successful_answer_usd"] == pytest.approx((4 * 0.001 + 0.01) / 4)
    assert doc["spend"]["spent_usd"] == pytest.approx(4 * 0.001 + 0.01)
    assert "gpt-6-luna-resolved" in cascade["resolved_models"]


def test_schema_valid_guess_counts_as_failure():
    guessing = {"How many assists did Jalen have last night?": [
        sel("intent", "boxscore_stat", confidence=0.9), sel("stat_scope", "player", confidence=0.9),
        sel("stat", "assists", confidence=0.9), sel("player", "player:1628973", confidence=0.9),
        sel("date", "date:0", confidence=0.9)]}
    primary = FakeAdapter("jev", "jev-1.13.0", guessing)
    case = BY_ID["smoke-which-jalen"]
    cfg = configs(primary, None)[0]
    result = run([case], embedded_candidates, [cfg], SpendGuard(1))
    score = result.scores["jev"][0]
    assert score.action == "accept" and not score.correct and score.guess
    assert score.failure == "schema_valid_guess"


def test_spend_cap_stops_the_run_before_overspending():
    primary = FakeAdapter("jev", "jev-1.13.0", GOOD, cost=0.4)
    cfg = configs(primary, None)[0]
    guard = SpendGuard(1.0)
    result = run(CASES, embedded_candidates, [cfg], guard)
    assert result.stopped_reason == "spend cap reached"
    assert primary.calls == 2 and guard.spent_usd <= 1.0
    assert len(result.not_run["jev"]) == len(CASES) - 2


def test_unavailable_primary_uses_fallback_only_when_enabled():
    primary = FakeAdapter("jev", "jev-1.13.0", {"Cavs games last week": "unavailable"})
    luna = FakeAdapter("openai_responses", "gpt-6-luna", GOOD)
    case = BY_ID["smoke-games-last-week"]
    cascade = configs(primary, luna)[1]
    assert drive(cascade, case.question, case.context, case.candidates, guard=SpendGuard(1)).decision.action == "accept"
    cascade.fallback_enabled = False
    assert drive(cascade, case.question, case.context, case.candidates, guard=SpendGuard(1)).decision.action == "fail"


def test_expansion_without_lookup_becomes_clarification():
    script = {"Did the Sonics play last night?": [
        sel("intent", "game_search", confidence=0.9), sel("date", "date:0", confidence=0.9),
        FieldInterpretation(field="teams", status="no_matching_candidate", confidence=0.9)]}
    case = BY_ID["smoke-missing-team"]
    outcome = drive(configs(FakeAdapter("jev", "jev-1.13.0", script), None)[0], case.question, case.context,
                    case.candidates, guard=SpendGuard(1))
    assert (outcome.decision.action, outcome.decision.field) == ("clarify", "teams")


def test_percentile_nearest_rank():
    assert percentile([], 95) is None
    assert percentile([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 95) == 10
    assert percentile([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 50) == 5
