import datetime as dt
import json
from pathlib import Path

import pytest

from server.ask.config import AskConfig
from server.ask.eval import builders as b
from server.ask.interpreters.cascade import ThresholdCascadePolicy
from server.ask.interpreters.tiered import CASCADE_POLICY_THRESHOLDS, Tier, TieredAdapter
from server.ask.models.candidates import CandidateLookupResult
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
    assert out.metadata.field_tiers == {"intent": "jev", "date": "jev", "teams": "jev", "location": "lookup"}
    assert (out.metadata.model, out.metadata.resolved_model) == ("jev-model+luna-model", "jev-model")
    assert out.metadata.usage.cost_usd == pytest.approx(0.0001)
    assert decide(out).action == "accept"


def test_uncertain_field_escalates_and_keeps_confident_reads():
    laya = Fake("laya", sel("intent", "game_search"), sel("date", "date:0"), sel("teams", CLE.id, confidence=0.5))
    jev = Fake("jev", sel("intent", "game_search", confidence=0.6), sel("teams", CLE.id))
    out = cascade(laya, jev).interpret(REQUEST)
    assert out.metadata.field_tiers == {"intent": "laya", "date": "laya", "teams": "jev", "location": "lookup"}
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


def test_later_ambiguous_read_vetoes_an_accepted_selection():
    jev = Fake("jev", sel("intent", "game_search"), sel("teams", CLE.id), sel("date", "date:0", confidence=0.3))
    luna = Fake("luna", sel("intent", "game_search", confidence=None), sel("date", "date:0", confidence=None),
                FieldInterpretation(field="teams", status="ambiguous", alternatives=[BOS.id, CLE.id]))
    out = cascade(jev, luna).interpret(REQUEST)
    teams = out.get_field("teams")
    assert (teams.status, teams.alternatives) == ("ambiguous", [CLE.id, BOS.id])
    assert out.metadata.field_tiers["teams"] == "veto"
    decision = decide(out)
    assert (decision.action, decision.field) == ("clarify", "teams")


def test_confident_jev_ambiguity_vetoes_an_accepted_laya_selection():
    laya = Fake("laya", sel("intent", "game_search"), sel("teams", CLE.id), sel("date", "date:0", confidence=0.3))
    jev = Fake("jev", sel("date", "date:0"),
               FieldInterpretation(field="teams", status="ambiguous", alternatives=[CLE.id, BOS.id], confidence=0.95))
    out = cascade(laya, jev).interpret(REQUEST)
    assert out.get_field("teams").status == "ambiguous"
    assert decide(out).action == "clarify"


FROZEN_UNSEEN = Path(__file__).resolve().parents[3] / "docs" / "verification" / "ask-unseen-2026-09-29.jsonl"


class Replay:
    """Returns one tier's recorded output from the frozen unseen run."""

    def __init__(self, name, recorded):
        self.name = name
        self.model = recorded["metadata"]["model"]
        self.output = InterpreterOutput.model_validate(recorded)

    def estimate_cost(self, request):
        return 0.0

    def interpret(self, request):
        return self.output


def replay(case_id):
    record = next(json.loads(line) for line in FROZEN_UNSEEN.read_text().splitlines()
                  if json.loads(line)["case_id"] == f"unseen-2026-09-29-{case_id}")
    candidates = CandidateLookupResult.model_validate(record["candidates"])
    tiers = [Tier(t["tier"], Replay(t["tier"], t["output"]), None if t["tier"] == "luna" else 0.85)
             for t in record["tier_outputs"]]
    request = REQUEST.model_copy(update={"candidates": candidates})
    out = TieredAdapter(tiers).interpret(request)
    norm = Normalizer().normalize(out, candidates, CONTEXT)
    state = CascadeState(attempts=[CascadeAttempt(output=out, normalization=norm)], candidates=candidates,
                         fallback_enabled=False, remaining_budget_usd=1, remaining_ms=20_000)
    return out, norm, POLICY.decide(state)


def test_bare_surname_with_several_players_is_clarified_not_guessed():
    # Unseen case 082, "How many points did Curry score on January 15, 2025?": Jev picked
    # Stephen Curry at 1.0; Luna read the player as ambiguous. Seth Curry was also active
    # in 2024-25, so the merge must ask which Curry instead of keeping Jev's pick.
    out, _, decision = replay("082")
    player = out.get_field("player")
    assert player.status == "ambiguous"
    assert {"player:201939", "player:203552"} <= set(player.alternatives)
    # Eddy, JamesOn, Michael and Dell Curry all retired before 2024-25.
    assert set(player.alternatives) == {"player:201939", "player:203552"}
    assert (decision.action, decision.field) == ("clarify", "player")


@pytest.mark.parametrize(("case_id", "player_id"), [
    ("002", 893),  # MJ, 1998 Finals: MJ Walker debuted in 2021-22.
    ("026", 406),  # Shaq, 2001 Finals: Shaq Buchanan played only in 2021-22.
])
def test_ambiguity_with_only_out_of_era_players_keeps_the_accepted_pick(case_id, player_id):
    out, norm, decision = replay(case_id)
    assert out.metadata.field_tiers["player"] == "jev"
    assert decision.action == "accept"
    assert norm.request.player.player_id == player_id


def test_era_filter_keeps_alternatives_when_the_season_is_unknown():
    mj = b.player(893, "Michael Jordan", first="1984-85", last="2002-03")
    walker = b.player(1630640, "MJ Walker", first="2021-22", last="2021-22")
    candidates = b.lookup_result([mj, walker])
    request = REQUEST.model_copy(update={"question": "MJ points", "candidates": candidates})
    jev = Fake("jev", sel("intent", "boxscore_stat"), sel("player", mj.id), sel("date", "date:0", confidence=0.3))
    luna = Fake("luna", sel("intent", "boxscore_stat", confidence=None), absent("date", confidence=None),
                FieldInterpretation(field="player", status="ambiguous", alternatives=[mj.id, walker.id]))
    out = cascade(jev, luna).interpret(request)
    assert (out.get_field("player").status, out.metadata.field_tiers["player"]) == ("ambiguous", "veto")


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
    assert out.metadata.field_tiers == {"intent": "jev", "date": "jev", "teams": "jev", "location": "lookup"}
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
    assert {f.field for f in out.fields} == {"intent", "date", "teams", "location"}
    assert "stat" not in out.metadata.field_tiers


def no_match(field, confidence=0.95):
    return FieldInterpretation(field=field, status="no_matching_candidate", confidence=confidence)


def _team_stat_reads(season_read, *, teams_confidence):
    return [sel("intent", "boxscore_stat"), sel("stat_scope", "team"), sel("stat", "points"),
            sel("aggregation", "total"), absent("player"), sel("date", "date:0"), season_read,
            absent("round"), absent("game_number"), sel("teams", CLE.id, confidence=teams_confidence)]


def _stat_request(candidates):
    return REQUEST.model_copy(update={"question": "cleveland points last week", "candidates": candidates})


def test_later_absent_read_replaces_an_uncorroborated_no_match():
    one_day = b.date(0, "sep 21", DateComponents(kind="calendar_date", year=2026, month=9, day=21),
                     start=dt.date(2026, 9, 21))
    request = _stat_request(b.lookup_result([CLE, one_day]))  # lookup saw no season text
    jev = Fake("jev", *_team_stat_reads(no_match("season"), teams_confidence=0.5))
    luna = Fake("luna", *[r.model_copy(update={"confidence": None})
                          for r in _team_stat_reads(absent("season"), teams_confidence=None)])
    out = cascade(jev, luna).interpret(request)
    assert out.get_field("season").status == "absent"
    assert out.metadata.field_tiers["season"] == "luna"
    norm = Normalizer().normalize(out, request.candidates, CONTEXT)
    assert norm.status == "valid"


def test_no_match_backed_by_unmatched_lookup_text_survives_a_later_absent_read():
    one_day = b.date(0, "sep 21", DateComponents(kind="calendar_date", year=2026, month=9, day=21),
                     start=dt.date(2026, 9, 21))
    request = _stat_request(b.lookup_result([CLE, one_day], unmatched={"season": ["2199"]}))
    jev = Fake("jev", *_team_stat_reads(no_match("season"), teams_confidence=0.5))
    luna = Fake("luna", *[r.model_copy(update={"confidence": None})
                          for r in _team_stat_reads(absent("season"), teams_confidence=None)])
    out = cascade(jev, luna).interpret(request)
    assert out.get_field("season").status == "no_matching_candidate"
    assert out.metadata.field_tiers["season"] == "jev"


def test_target_team_is_lookup_absent_without_team_text_and_needed_only_for_team_scope():
    one_day = b.date(0, "sep 21", DateComponents(kind="calendar_date", year=2026, month=9, day=21),
                     start=dt.date(2026, 9, 21))
    player_reads = [sel("intent", "boxscore_stat"), sel("stat_scope", "player"), sel("stat", "points"),
                    sel("aggregation", "total"), sel("player", "player:1"), sel("date", "date:0"),
                    absent("season"), absent("round"), absent("game_number"), absent("teams")]
    tatum = b.player(1, "Some Player")
    request = _stat_request(b.lookup_result([tatum, one_day]))
    jev, luna = Fake("jev", *player_reads), Fake("luna")
    out = cascade(jev, luna).interpret(request)
    assert luna.calls == 0 and out.get_field("target_team") is None

    # Team scope: Jev unsure which named team the stat belongs to escalates to Luna.
    request = _stat_request(b.lookup_result([CLE, BOS, one_day]))
    team_reads = [sel("intent", "boxscore_stat"), sel("stat_scope", "team"), sel("stat", "points"),
                  sel("aggregation", "total"), absent("player"), sel("date", "date:0"), absent("season"),
                  absent("round"), absent("game_number"), sel("teams", CLE.id, BOS.id)]
    jev = Fake("jev", *team_reads, sel("target_team", BOS.id, confidence=0.6))
    luna = Fake("luna", sel("intent", "boxscore_stat", confidence=None),
                sel("target_team", BOS.id, confidence=None))
    out = cascade(jev, luna).interpret(request)
    assert luna.calls == 1 and out.metadata.field_tiers["target_team"] == "luna"
    norm = Normalizer().normalize(out, request.candidates, CONTEXT)
    assert norm.status == "valid" and norm.request.team == BOS.value.team


def test_undecided_target_team_is_clarified_as_teams():
    state_output = InterpreterOutput(
        outcome="interpreted",
        fields=[sel("intent", "boxscore_stat", confidence=None), sel("stat_scope", "team", confidence=None),
                sel("teams", CLE.id, BOS.id, confidence=None), sel("date", "date:0", confidence=None),
                sel("target_team", CLE.id, confidence=0.5)],
        metadata=InterpreterMetadata(adapter="cascade", provider="cascade", model="m", latency_ms=1),
    )
    one_day = b.date(0, "sep 21", DateComponents(kind="calendar_date", year=2026, month=9, day=21),
                     start=dt.date(2026, 9, 21))
    candidates = b.lookup_result([CLE, BOS, one_day])
    norm = Normalizer().normalize(state_output, candidates, CONTEXT)
    assert norm.status == "valid"  # executable, but the target read is below certainty
    state = CascadeState(attempts=[CascadeAttempt(output=state_output, normalization=norm)], candidates=candidates,
                         fallback_enabled=False, remaining_budget_usd=1, remaining_ms=20_000)
    decision = POLICY.decide(state)
    assert (decision.action, decision.field) == ("clarify", "teams")
