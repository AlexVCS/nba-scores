import datetime as dt
import threading
import time
from pathlib import Path

import pytest

from server.ask.cache import AskCache
from server.ask.config import AskConfig
from server.ask.eval import builders as b
from server.ask.limits import AskLimits, AskTimeout
from server.ask.models.common import DateComponents
from server.ask.models.interpreter import FieldInterpretation, InterpreterMetadata, InterpreterOutput, InterpreterUsage
from server.ask.models.response import AskQuery, AskResponse
from server.ask.pipeline import AskPipeline
from server.ask.resolution import PendingResolution, ResolutionStore
from server.ask.resolvers.output import ResolverOutput


NOW = dt.datetime(2026, 9, 29, 12, tzinfo=dt.timezone(dt.timedelta(hours=-4)))


class Lookup:
    alias_version = "test"

    def __init__(self, candidates):
        self.candidates = candidates

    def lookup(self, question, context):
        return self.candidates


class Adapter:
    name = "openai_responses"
    model = "gpt-6-luna"

    def __init__(self):
        self.calls = 0

    def estimate_cost(self, request):
        return 0.001

    def interpret(self, request):
        self.calls += 1
        return InterpreterOutput(outcome="unsupported", unsupported_reason="other",
                                 metadata=InterpreterMetadata(adapter=self.name, provider="openai",
                                                              model=self.model, latency_ms=1,
                                                              usage=InterpreterUsage(provider_calls=1,
                                                                                     cost_usd=0.0001)))


class Budget:
    def __init__(self):
        self.settlements = []

    def remaining_usd(self):
        return 1.0

    def reserve(self, model, amount):
        return object()

    def settle(self, reservation, amount):
        self.settlements.append(amount)


def pipeline(tmp_path, lookup, adapter, budget=None, deadline_seconds=20):
    return AskPipeline(AskConfig(enabled=True, state_dir=tmp_path, api_key="fake",
                                 deadline_seconds=deadline_seconds),
                       lookup=lookup, adapter=adapter, budget=budget or Budget(), cache=AskCache(),
                       resolutions=ResolutionStore(tmp_path / "resolutions.sqlite3"), clock=lambda: NOW)


def test_parse_cache_ignores_lookup_latency_but_keeps_candidate_content(tmp_path):
    candidates = b.lookup_result([])
    adapter = Adapter()
    coordinator = pipeline(tmp_path, Lookup(candidates), adapter)
    context = coordinator._context(AskQuery(question="Who won yesterday?"))
    deadline = time.monotonic() + 5

    _, first_hit = coordinator._interpret("Who won yesterday?", context, candidates, deadline)
    _, second_hit = coordinator._interpret("Who won yesterday?", context,
                                           candidates.model_copy(update={"latency_ms": 897}), deadline)
    assert first_hit is False and second_hit is True
    assert adapter.calls == 1

    changed = candidates.model_copy(update={"alias_version": "different"})
    _, changed_hit = coordinator._interpret("Who won yesterday?", context, changed, deadline)
    assert changed_hit is False and adapter.calls == 2
    with_player = b.lookup_result([b.player(10, "Jalen A", matched="Jalen")])
    _, content_hit = coordinator._interpret("Who won yesterday?", context, with_player, deadline)
    assert content_hit is False and adapter.calls == 3


def test_first_exact_answer_populates_empty_answer_cache(tmp_path, monkeypatch):
    fixture = Path("src/services/ask/fixtures/responses/answer-games-last-week.json")
    known = AskResponse.model_validate_json(fixture.read_text())
    coordinator = pipeline(tmp_path, Lookup(b.lookup_result([])), Adapter())
    calls = []

    def resolve(request):
        calls.append(request)
        return ResolverOutput(known.result, tuple(known.links), tuple(known.sources))

    monkeypatch.setattr("server.ask.pipeline.resolve", resolve)
    query = AskQuery(question="Games on 2026-09-29?")
    first = coordinator.answer(query)
    second = coordinator.answer(query)
    assert first.outcome == second.outcome == "answer"
    assert first.interpreter.cache_hit is False
    assert second.interpreter.cache_hit is True
    assert len(calls) == 1


def test_first_token_answer_populates_empty_answer_cache(tmp_path, monkeypatch):
    fixture = Path("src/services/ask/fixtures/responses/answer-games-last-week.json")
    known = AskResponse.model_validate_json(fixture.read_text())
    day = b.date(0, "today", DateComponents(kind="relative", relative="today"),
                 start=dt.date(2026, 9, 29))
    candidates = b.lookup_result([day])
    coordinator = pipeline(tmp_path, Lookup(candidates), Adapter())
    question = "Any games today?"
    context = coordinator._context(AskQuery(question=question))
    output = InterpreterOutput(outcome="interpreted", fields=[
        FieldInterpretation(field="intent", status="selected", selected=["game_search"]),
        FieldInterpretation(field="date", status="selected", selected=[day.id]),
    ], metadata=InterpreterMetadata(adapter="openai_responses", provider="openai",
                                    model="gpt-6-luna", latency_ms=1,
                                    usage=InterpreterUsage(provider_calls=1, cost_usd=0.0001)))
    token = coordinator.resolutions.issue(question, PendingResolution(output, candidates, context))
    calls = []

    def resolve(request):
        calls.append(request)
        return ResolverOutput(known.result, tuple(known.links), tuple(known.sources))

    monkeypatch.setattr("server.ask.pipeline.resolve", resolve)
    query = AskQuery(question=question, resolution=token)
    first = coordinator.answer(query)
    second = coordinator.answer(query)
    assert first.outcome == second.outcome == "answer"
    assert first.interpreter.cache_hit is False
    assert second.interpreter.cache_hit is True
    assert len(calls) == 1


def test_lookup_consumes_deadline_without_starting_paid_call(tmp_path):
    entered, release, done = threading.Event(), threading.Event(), threading.Event()

    class BlockingLookup(Lookup):
        def lookup(self, question, context):
            entered.set()
            release.wait(1)
            return self.candidates

    adapter, budget = Adapter(), Budget()
    coordinator = pipeline(tmp_path, BlockingLookup(b.lookup_result([])), adapter, budget,
                           deadline_seconds=0.02)
    limits = AskLimits(max_in_flight=1)
    responses = []

    def work():
        try:
            responses.append(coordinator.answer(AskQuery(question="Who won yesterday?")))
        finally:
            done.set()

    try:
        with pytest.raises(AskTimeout):
            limits.run_bounded(work, timeout_seconds=0.02)
        assert entered.is_set()
    finally:
        release.set()
    assert done.wait(1)
    assert responses[0].outcome == "unavailable"
    assert adapter.calls == 0 and budget.settlements == []


def test_expired_reservation_is_settled_unspent(tmp_path):
    class SlowBudget(Budget):
        def reserve(self, model, amount):
            time.sleep(0.03)
            return super().reserve(model, amount)

    adapter, budget = Adapter(), SlowBudget()
    coordinator = pipeline(tmp_path, Lookup(b.lookup_result([])), adapter, budget,
                           deadline_seconds=0.02)
    response = coordinator.answer(AskQuery(question="Who won yesterday?"))
    assert response.outcome == "unavailable"
    assert adapter.calls == 0 and budget.settlements == [0.0]


@pytest.mark.parametrize("case", ["player", "year"])
def test_long_clarification_does_not_issue_truncated_question(tmp_path, case):
    if case == "player":
        first = b.player(10, "Jalen A", matched="Jalen")
        second = b.player(11, "Jalen B", matched="Jalen")
        candidates = b.lookup_result([first, second])
        fields = [
            FieldInterpretation(field="intent", status="selected", selected=["boxscore_stat"]),
            FieldInterpretation(field="stat_scope", status="selected", selected=["player"]),
            FieldInterpretation(field="player", status="ambiguous",
                                alternatives=[first.id, second.id]),
        ]
        base = "How did Jalen do? "
    else:
        day = b.date(0, "March 3", DateComponents(kind="calendar_date", month=3, day=3),
                     unresolved="year_required", matched="March 3")
        candidates = b.lookup_result([day])
        fields = [
            FieldInterpretation(field="intent", status="selected", selected=["game_search"]),
            FieldInterpretation(field="date", status="selected", selected=[day.id]),
        ]
        base = "Games on March 3? "
    question = base + "x" * (300 - len(base))
    output = InterpreterOutput(outcome="interpreted", fields=fields,
                               metadata=InterpreterMetadata(adapter="openai_responses", provider="openai",
                                                            model="gpt-6-luna", latency_ms=1,
                                                            usage=InterpreterUsage(provider_calls=1,
                                                                                   cost_usd=0.0001)))

    class ScriptedAdapter(Adapter):
        def interpret(self, request):
            self.calls += 1
            return output

    coordinator = pipeline(tmp_path, Lookup(candidates), ScriptedAdapter())
    coordinator.resolutions.issue = lambda *args: pytest.fail("truncated question received a token")
    response = coordinator.answer(AskQuery(question=question))
    assert response.outcome == "needs_clarification"
    assert response.clarification.options == []
    assert "Shorten your question" in response.clarification.hint


@pytest.mark.parametrize("total_seconds, max_interpreter_ms", [(20, 15000), (4, 3000)])
def test_interpretation_leaves_time_for_nba_resolution(tmp_path, total_seconds, max_interpreter_ms):
    deadlines = []

    class CapturingAdapter(Adapter):
        def interpret(self, request):
            deadlines.append(request.deadline_ms)
            return super().interpret(request)

    coordinator = pipeline(tmp_path, Lookup(b.lookup_result([])), CapturingAdapter(),
                           deadline_seconds=total_seconds)
    response = coordinator.answer(AskQuery(question="Explain basketball history"))
    assert response.outcome == "unsupported"
    assert len(deadlines) == 1
    assert 0 < deadlines[0] <= max_interpreter_ms
    assert coordinator.config.deadline_seconds == total_seconds


def test_invalid_normalization_is_not_replayed_from_parse_cache(tmp_path):
    class RecoveringAdapter(Adapter):
        def interpret(self, request):
            output = super().interpret(request)
            if self.calls == 1:
                return output.model_copy(update={"outcome": "interpreted", "unsupported_reason": None,
                    "fields": [
                        FieldInterpretation(field="intent", status="selected", selected=["boxscore_stat"]),
                        FieldInterpretation(field="aggregation", status="ambiguous", alternatives=["total", "per_game"]),
                    ]})
            return output

    adapter = RecoveringAdapter()
    coordinator = pipeline(tmp_path, Lookup(b.lookup_result([])), adapter)
    query = AskQuery(question="Explain basketball history")
    assert coordinator.answer(query).outcome == "unavailable"
    assert coordinator.answer(query).outcome == "unsupported"
    assert adapter.calls == 2
    assert coordinator.answer(query).interpreter.cache_hit is True
    assert adapter.calls == 2
