import datetime as dt
from pathlib import Path

from server.ask.cache import AskCache
from server.ask.budget import BudgetExhausted
from server.ask.config import AskConfig
from server.ask.eval import builders as b
from server.ask.models.common import DateComponents
from server.ask.models.interpreter import FieldInterpretation, InterpreterMetadata, InterpreterOutput, InterpreterUsage
from server.ask.models.response import AskQuery, AskResponse
from server.ask.pipeline import AskPipeline
from server.ask.resolution import ResolutionStore
from server.ask.resolvers.errors import NotFoundError
from server.ask.resolvers.output import ResolverOutput


NOW = dt.datetime(2026, 9, 29, 12, tzinfo=dt.timezone(dt.timedelta(hours=-4)))


def selected(field, value):
    return FieldInterpretation(field=field, status="selected", selected=[value])


class Lookup:
    alias_version = "test"

    def __init__(self, candidates):
        self.candidates = candidates
        self.calls = 0

    def lookup(self, question, context):
        self.calls += 1
        return self.candidates

    def expand(self, question, context, field, previous):
        return previous


class Adapter:
    name = "openai_responses"
    model = "gpt-6-luna"

    def __init__(self, output):
        self.output = output
        self.calls = 0

    def estimate_cost(self, request):
        return 0.001

    def interpret(self, request):
        self.calls += 1
        return self.output


def output(*fields, outcome="interpreted", reason=None):
    return InterpreterOutput(outcome=outcome, fields=list(fields), unsupported_reason=reason,
                             metadata=InterpreterMetadata(adapter="openai_responses", provider="openai",
                                                          model="gpt-6-luna", latency_ms=1,
                                                          usage=InterpreterUsage(provider_calls=1, cost_usd=0.0001)))


def pipeline(tmp_path, candidates, interpreted):
    config = AskConfig(enabled=True, state_dir=tmp_path, api_key="fake")
    lookup, adapter = Lookup(candidates), Adapter(interpreted)
    return AskPipeline(config, lookup=lookup, adapter=adapter, cache=AskCache(),
                       resolutions=ResolutionStore(tmp_path / "resolutions.sqlite3"), clock=lambda: NOW), lookup, adapter


def test_exact_date_is_zero_model(tmp_path, monkeypatch):
    coordinator, lookup, adapter = pipeline(tmp_path, b.lookup_result([]), output())
    captured = []

    def no_games(request):
        captured.append(request)
        raise NotFoundError("no_games", "no_matching_games")

    monkeypatch.setattr("server.ask.pipeline.resolve", no_games)
    response = coordinator.answer(AskQuery(question="Games on 2026-09-29?"))
    assert response.outcome == "not_found"
    assert response.interpreter.model_called is False
    assert len(captured) == 1 and captured[0].dates.start == dt.date(2026, 9, 29)
    assert lookup.calls == adapter.calls == 0


def test_answer_and_not_found_preserve_identical_resolver_gate(tmp_path, monkeypatch):
    fixture = Path("src/services/ask/fixtures/responses/answer-conditional-game-hidden.json")
    conditional = AskResponse.model_validate_json(fixture.read_text())
    known = AskResponse.model_validate_json(Path(
        "src/services/ask/fixtures/responses/answer-games-last-week.json").read_text())
    gate = conditional.spoiler_gate
    assert gate is not None
    coordinator, _, _ = pipeline(tmp_path, b.lookup_result([]), output())
    query = AskQuery(question="Games on 2024-06-17?")
    monkeypatch.setattr("server.ask.pipeline.resolve", lambda request: ResolverOutput(
        known.result, tuple(known.links), tuple(known.sources), gate))
    answer = coordinator.answer(query)
    def missing(request):
        error = NotFoundError("no_games", "no_matching_games")
        error.spoiler_gate = gate
        raise error
    monkeypatch.setattr("server.ask.pipeline.resolve", missing)
    absent, _, _ = pipeline(tmp_path / "other", b.lookup_result([]), output())
    not_found = absent.answer(query)
    assert answer.outcome == "answer" and not_found.outcome == "not_found"
    assert answer.spoiler_gate == not_found.spoiler_gate == gate


def test_parse_cache_saves_model_call_and_uses_ny_day(tmp_path, monkeypatch):
    date = b.date(0, "today", DateComponents(kind="relative", relative="today"),
                  start=dt.date(2026, 9, 29))
    coordinator, lookup, adapter = pipeline(tmp_path, b.lookup_result([date]),
                                            output(selected("intent", "game_search"), selected("date", date.id)))
    def no_games(request):
        raise NotFoundError("no_games", "no_matching_games")
    monkeypatch.setattr("server.ask.pipeline.resolve", no_games)
    first = coordinator.answer(AskQuery(question="Any games today?"))
    second = coordinator.answer(AskQuery(question="Any games today?"))
    assert first.outcome == second.outcome == "not_found"
    assert first.interpreter.model_called is True
    assert second.interpreter.model_called is False and second.interpreter.cache_hit is True
    assert adapter.calls == 1 and lookup.calls == 2


def test_partial_token_chain_never_calls_model_again(tmp_path, monkeypatch):
    jalen_a = b.player(10, "Jalen A", matched="Jalen")
    jalen_b = b.player(11, "Jalen B", matched="Jalen")
    date = b.date(0, "March 3", DateComponents(kind="calendar_date", month=3, day=3),
                  unresolved="year_required", matched="March 3")
    interpreted = output(selected("intent", "boxscore_stat"), selected("stat_scope", "player"),
                         selected("date", date.id),
                         FieldInterpretation(field="player", status="ambiguous",
                                             alternatives=[jalen_a.id, jalen_b.id]))
    coordinator, _, adapter = pipeline(tmp_path, b.lookup_result([jalen_a, jalen_b, date]), interpreted)
    first = coordinator.answer(AskQuery(question="How did Jalen do on March 3?"))
    assert first.outcome == "needs_clarification" and first.clarification.field == "player"
    chosen = first.clarification.options[0]
    second = coordinator.answer(AskQuery(question=chosen.question, resolution=chosen.resolution))
    assert second.outcome == "needs_clarification" and second.clarification.field == "date"
    year = second.clarification.options[0]
    def no_game(request):
        assert request.player.player_id == 10
        assert request.game.date.year == 2026
        raise NotFoundError("player_did_not_play", "no_game")
    monkeypatch.setattr("server.ask.pipeline.resolve", no_game)
    third = coordinator.answer(AskQuery(question=year.question, resolution=year.resolution))
    assert third.outcome == "not_found"
    assert adapter.calls == 1


def test_token_bound_to_rewritten_question_and_context(tmp_path):
    date = b.date(0, "March 3", DateComponents(kind="calendar_date", month=3, day=3),
                  unresolved="year_required", matched="March 3")
    coordinator, _, adapter = pipeline(tmp_path, b.lookup_result([date]),
                                       output(selected("intent", "game_search"), selected("date", date.id)))
    first = coordinator.answer(AskQuery(question="Games on March 3?"))
    chosen = first.clarification.options[0]
    assert coordinator.resolutions.read(chosen.resolution, "Different question", coordinator._context(
        AskQuery(question="Different question"))) is None
    assert coordinator.resolutions.read(chosen.resolution, chosen.question, coordinator._context(
        AskQuery(question=chosen.question, context={"route": "playoffs"}))) is None
    assert adapter.calls == 1


def test_disabled_coordinator_makes_no_model_call(tmp_path):
    coordinator, lookup, adapter = pipeline(tmp_path, b.lookup_result([]), output())
    coordinator.config = AskConfig(enabled=False, state_dir=tmp_path)
    response = coordinator.answer(AskQuery(question="Who won?"))
    assert response.outcome == "unavailable" and response.notice.code == "service_unavailable"
    assert lookup.calls == adapter.calls == 0


def test_boxscore_context_leader_shortcut_is_zero_model(tmp_path, monkeypatch):
    coordinator, lookup, adapter = pipeline(tmp_path, b.lookup_result([]), output())
    captured = []
    def no_game(request):
        captured.append(request)
        raise NotFoundError("no_record", "game_not_recorded")
    monkeypatch.setattr("server.ask.pipeline.resolve", no_game)
    query = AskQuery(question="Who led in rebounds?",
                     context={"route": "boxscore", "game_id": "0022500012"})
    response = coordinator.answer(query)
    assert response.outcome == "not_found"
    assert captured[0].scope == "leaders" and captured[0].stat.stat == "rebounds"
    assert captured[0].game.game_id == "0022500012"
    assert lookup.calls == adapter.calls == 0


def test_budget_exhaustion_prevents_provider_call(tmp_path):
    date = b.date(0, "today", DateComponents(kind="relative", relative="today"),
                  start=dt.date(2026, 9, 29))
    coordinator, _, adapter = pipeline(tmp_path, b.lookup_result([date]),
                                       output(selected("intent", "game_search"), selected("date", date.id)))
    class EmptyBudget:
        def remaining_usd(self):
            return 0

        def reserve(self, model, amount):
            raise BudgetExhausted("daily limit")
    coordinator.budget = EmptyBudget()
    response = coordinator.answer(AskQuery(question="Any games today?"))
    assert response.outcome == "budget_exhausted"
    assert response.interpreter.model_called is False and adapter.calls == 0
