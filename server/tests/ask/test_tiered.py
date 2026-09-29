import datetime as dt

import pytest

from server.ask.config import AskConfig
from server.ask.eval import builders as b
from server.ask.interpreters.cascade import ThresholdCascadePolicy
from server.ask.interpreters.tiered import CASCADE_POLICY_THRESHOLDS, Tier, TieredAdapter
from server.ask.models.common import DateComponents
from server.ask.models.interpreter import (
    FieldInterpretation,
    InterpreterInput,
    InterpreterMetadata,
    InterpreterOutput,
    InterpreterUsage,
)
from server.ask.models.request import AskContext
from server.ask.normalize import Normalizer
from server.ask.pipeline import build_cascade
from server.ask.protocols import CascadeAttempt, CascadeState, InterpreterAdapter

CONTEXT = AskContext(reference_time=dt.datetime.fromisoformat("2026-09-29T12:00:00-04:00"))
CLE = b.team(1610612739, "CLE", "Cleveland Cavaliers")
BOS = b.team(1610612738, "BOS", "Boston Celtics")
LAST_WEEK = b.date(0, "last week", DateComponents(kind="relative", relative="last_week"),
                   start=dt.date(2026, 9, 21), end=dt.date(2026, 9, 27))
CANDIDATES = b.lookup_result([CLE, BOS, LAST_WEEK])
REQUEST = InterpreterInput(question="cavs games last week", context=CONTEXT, candidates=CANDIDATES,
                           deadline_ms=20_000, max_cost_usd=1.0)
POLICY = ThresholdCascadePolicy("cascade", thresholds=CASCADE_POLICY_THRESHOLDS)


def sel(field, *values, confidence=0.95):
    return FieldInterpretation(field=field, status="selected", selected=list(values), confidence=confidence)


def absent(field, confidence=0.95):
    return FieldInterpretation(field=field, status="absent", confidence=confidence)


class Fake:
    def __init__(self, name, *fields, outcome="interpreted", reason=None, cost=0.0, error=None):
        self.name = "openai_responses" if name == "luna" else name
        self.model = f"{name}-model"
        self.fields = list(fields)
        self.outcome = outcome
        self.reason = reason
        self.cost = cost
        self.error = error
        self.calls = 0

    def estimate_cost(self, request):
        return 0.001

    def interpret(self, request):
        self.calls += 1
        if self.outcome == "unavailable":
            return InterpreterOutput(outcome="unavailable", error_code=self.error or "timeout",
                                     metadata=InterpreterMetadata(adapter=self.name, provider="x", model=self.model,
                                                                  latency_ms=1,
                                                                  usage=InterpreterUsage(provider_calls=1, cost_usd=self.cost)))
        return InterpreterOutput(
            outcome=self.outcome, fields=[] if self.outcome == "unsupported" else self.fields,
            unsupported_reason=self.reason,
            metadata=InterpreterMetadata(adapter=self.name, provider="x", model=self.model, latency_ms=1,
                                         usage=InterpreterUsage(provider_calls=1, cost_usd=self.cost)),
        )


def cascade(*adapters, thresholds=(0.9, 0.9)):
    tiers = []
    for index, adapter in enumerate(adapters):
        name = "luna" if adapter.name == "openai_responses" else adapter.name
        final = name == "luna"
        tiers.append(Tier(name, adapter, None if final else thresholds[index]))
    return TieredAdapter(tiers)


def decide(output):
    norm = Normalizer().normalize(output, CANDIDATES, CONTEXT) if output.outcome == "interpreted" else None
    state = CascadeState(attempts=[CascadeAttempt(output=output, normalization=norm)], candidates=CANDIDATES,
                         fallback_enabled=False, remaining_budget_usd=1, remaining_ms=20_000)
    return POLICY.decide(state)


def test_tiered_adapter_satisfies_protocol():
    assert isinstance(cascade(Fake("jev")), InterpreterAdapter)
    with pytest.raises(ValueError):
        TieredAdapter([Tier("luna", Fake("luna"), None), Tier("jev", Fake("jev"), 0.9)])


def test_confident_first_tier_stops_the_cascade():
    jev = Fake("jev", sel("intent", "game_search"), sel("date", "date:0"), sel("teams", CLE.id), absent("location"),
               cost=0.0001)
    luna = Fake("luna")
    out = cascade(jev, luna).interpret(REQUEST)
    assert luna.calls == 0
    assert out.metadata.field_tiers == {"intent": "jev", "date": "jev", "teams": "jev", "location": "jev"}
    assert (out.metadata.model, out.metadata.resolved_model) == ("jev-model+luna-model", "jev-model")
    assert out.metadata.usage.cost_usd == pytest.approx(0.0001)
    assert decide(out).action == "accept"


def test_uncertain_field_escalates_and_keeps_confident_reads():
    laya = Fake("laya", sel("intent", "game_search"), sel("date", "date:0"), sel("teams", CLE.id, confidence=0.5))
    jev = Fake("jev", sel("intent", "game_search", confidence=0.6), sel("teams", CLE.id))
    out = cascade(laya, jev).interpret(REQUEST)
    assert out.metadata.field_tiers == {"intent": "laya", "date": "laya", "teams": "jev"}
    assert out.metadata.usage.provider_calls == 2
    assert decide(out).action == "accept"


def test_final_tier_fills_what_system_one_tiers_could_not():
    jev = Fake("jev", sel("intent", "game_search"), sel("date", "date:0"), sel("teams", CLE.id, confidence=0.3))
    luna = Fake("luna", sel("intent", "game_search", confidence=None), sel("teams", CLE.id, confidence=None))
    out = cascade(jev, luna).interpret(REQUEST)
    assert out.metadata.field_tiers["teams"] == "luna"
    assert out.metadata.resolved_model == "jev-model+luna-model"
    assert decide(out).action == "accept"


def test_luna_disagreeing_with_an_accepted_read_is_vetoed():
    jev = Fake("jev", sel("intent", "game_search"), sel("teams", CLE.id), sel("date", "date:0", confidence=0.3))
    luna = Fake("luna", sel("intent", "game_search", confidence=None), sel("teams", BOS.id, confidence=None),
                sel("date", "date:0", confidence=None))
    out = cascade(jev, luna).interpret(REQUEST)
    teams = out.get_field("teams")
    assert (teams.status, sorted(teams.alternatives)) == ("ambiguous", sorted([CLE.id, BOS.id]))
    assert out.metadata.field_tiers["teams"] == "veto"
    decision = decide(out)
    assert (decision.action, decision.field) == ("clarify", "teams")


def test_luna_dropping_a_leaning_selection_is_clarified_not_executed():
    # Jev leans CLE (0.6, below accept_min) and Luna reads no team: running an
    # unfiltered search would be a guess.
    jev = Fake("jev", sel("intent", "game_search"), sel("date", "date:0"), sel("teams", CLE.id, confidence=0.6))
    luna = Fake("luna", sel("intent", "game_search", confidence=None), absent("teams", confidence=None))
    out = cascade(jev, luna).interpret(REQUEST)
    assert out.metadata.field_tiers["teams"] == "veto"
    decision = decide(out)
    assert (decision.action, decision.field) == ("clarify", "teams")


def test_weak_laya_lean_does_not_veto_confident_jev():
    laya = Fake("laya", sel("intent", "game_search"), sel("date", "date:0"), sel("teams", BOS.id, confidence=0.6))
    jev = Fake("jev", sel("intent", "game_search"), sel("teams", CLE.id))
    out = cascade(laya, jev).interpret(REQUEST)
    assert out.get_field("teams").selected == [CLE.id]
    assert decide(out).action == "accept"


def test_without_luna_an_undecided_field_is_clarified():
    jev = Fake("jev", sel("intent", "game_search"), sel("date", "date:0"), sel("teams", CLE.id, confidence=0.4))
    out = cascade(jev).interpret(REQUEST)
    assert "teams" not in out.metadata.field_tiers
    decision = decide(out)
    assert (decision.action, decision.field) == ("clarify", "teams")


def test_unavailable_tier_is_skipped():
    laya = Fake("laya", outcome="unavailable", error="connection_error")
    jev = Fake("jev", sel("intent", "game_search"), sel("date", "date:0"), absent("teams"))
    out = cascade(laya, jev).interpret(REQUEST)
    assert out.metadata.field_tiers == {"intent": "jev", "date": "jev", "teams": "jev"}
    assert decide(out).action == "accept"


def test_all_tiers_unavailable():
    out = cascade(Fake("jev", outcome="unavailable"), Fake("luna", outcome="unavailable")).interpret(REQUEST)
    assert (out.outcome, out.error_code) == ("unavailable", "all_tiers_unavailable")
    assert out.metadata.usage.provider_calls == 2


def test_unsupported_ends_the_cascade():
    jev = Fake("jev", outcome="unsupported", reason="prediction")
    luna = Fake("luna")
    out = cascade(jev, luna).interpret(REQUEST)
    assert (out.outcome, out.unsupported_reason, luna.calls) == ("unsupported", "prediction", 0)
    assert out.metadata.field_tiers == {"intent": "jev"}


def test_unknown_tier_cost_is_reported_as_unknown():
    jev = Fake("jev", sel("intent", "game_search"), sel("date", "date:0", confidence=0.2), cost=None)
    luna = Fake("luna", sel("date", "date:0", confidence=None), absent("teams", confidence=None), cost=0.0002)
    out = cascade(jev, luna).interpret(REQUEST)
    assert out.metadata.usage.cost_usd is None


def test_cache_label_tracks_thresholds():
    jev = Fake("jev")
    assert cascade(jev, thresholds=(0.9,)).label != cascade(jev, thresholds=(0.8,)).label


def test_build_cascade_orders_configured_tiers():
    config = AskConfig(api_key="sk", typesafe_api_key="ts", laya_base_url="http://laya.railway.internal/v1/systemone")
    assert [t.name for t in build_cascade(config).tiers] == ["laya", "jev", "luna"]
    # Laya stays out of production while LAYA_BASE_URL is unset (ADR 0007).
    assert [t.name for t in build_cascade(AskConfig(api_key="sk", typesafe_api_key="ts")).tiers] == ["jev", "luna"]
    with pytest.raises(RuntimeError):
        build_cascade(AskConfig())


def test_laya_adapter_speaks_systemone_locally_for_free():
    import httpx

    from server.ask.interpreters.laya import LayaAdapter
    from server.ask.interpreters.pricing import price_for

    seen = []

    def handler(request):
        seen.append(str(request.url))
        return httpx.Response(503)

    adapter = LayaAdapter(url="http://laya.test/v1/systemone", model="laya-en",
                          http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    out = adapter.interpret(REQUEST)
    assert (out.outcome, out.metadata.adapter, out.metadata.provider) == ("unavailable", "laya", "laya")
    assert seen and seen[0] == "http://laya.test/v1/systemone"
    assert price_for("laya-en").input == 0
    with pytest.raises(ValueError):
        LayaAdapter(model="jev-1.13.0")


def test_daily_budget_prices_a_cascade_by_its_tiers(tmp_path):
    from server.ask.budget import BudgetUnavailable, DailyBudget

    budget = DailyBudget(tmp_path, 1.0)
    config = AskConfig(api_key="sk", typesafe_api_key="ts")
    reservation = budget.reserve(build_cascade(config).model, 0.001)
    budget.settle(reservation, 0.0)
    with pytest.raises(BudgetUnavailable):
        budget.reserve("jev-1.13.0+unknown-model", 0.001)


def test_merged_output_keeps_only_fields_the_intent_uses():
    jev = Fake("jev", sel("intent", "game_search"), sel("date", "date:0"), absent("teams"), sel("stat", "points"))
    out = cascade(jev).interpret(REQUEST)
    assert {f.field for f in out.fields} == {"intent", "date", "teams"}
    assert "stat" not in out.metadata.field_tiers
