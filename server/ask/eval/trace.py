"""Record-once, replay-many calibration for the tiered cascade (#199, ADRs 0002 and 0009).

`collect()` runs every tier on every case exactly once: the record-all cascade uses
thresholds above 1.0, so no tier accepts anything and each tier sees the question. Each
output is saved under a key derived from the question, reference date, and candidates.

`sweep()` then replays those outputs through `TieredAdapter` for a grid of thresholds
and scores each configuration with the normal runner. Threshold sweeps make no
provider calls. A replay whose candidates were never recorded (a different expansion
path) returns `unavailable` with `not_recorded` and is reported as such.

`tier_stats()` measures each System One tier on its own (ADR 0009): of the relevant
fields whose confidence reaches the threshold, how many are correct (precision), and
what share of relevant fields that is (coverage). The field oracle is deliberately
conservative: it scores only `selected` reads on accept labels, and only for fields the
labeled request pins down.
"""

from __future__ import annotations

import hashlib
import itertools
from dataclasses import dataclass
from typing import Any, Iterable

from server.ask.eval.runner import (
    Configuration,
    Expander,
    LabeledCase,
    Run,
    drive,
    score,
    summarize,
)
from server.ask.interpreters.cascade import ThresholdCascadePolicy
from server.ask.interpreters.pricing import SpendGuard
from server.ask.interpreters.tiered import CASCADE_POLICY_THRESHOLDS, Tier, TieredAdapter
from server.ask.models.candidates import CandidateLookupResult
from server.ask.models.common import canonical_json
from server.ask.models.interpreter import (
    InterpreterInput,
    InterpreterMetadata,
    InterpreterOutput,
    InterpreterUsage,
)
from server.ask.normalize import RELEVANT_FIELDS

RECORD_ALL = 1.01  # above any confidence, so every tier runs


def trace_key(request: InterpreterInput) -> str:
    candidates = request.candidates.model_copy(update={"latency_ms": 0})
    raw = "\n".join([request.question, request.context.reference_time.date().isoformat(), canonical_json(candidates)])
    return hashlib.sha256(raw.encode()).hexdigest()


class RecordingAdapter:
    """Wraps a live adapter and records each output by `trace_key`."""

    def __init__(self, adapter, store: dict[str, Any]):
        self.adapter = adapter
        self.name = adapter.name
        self.model = adapter.model
        self.store = store

    def estimate_cost(self, request: InterpreterInput) -> float:
        return self.adapter.estimate_cost(request)

    def interpret(self, request: InterpreterInput) -> InterpreterOutput:
        output = self.adapter.interpret(request)
        self.store[trace_key(request)] = output.model_dump(mode="json")
        return output


class ReplayAdapter:
    """Returns recorded outputs; never calls a provider."""

    def __init__(self, name: str, model: str, store: dict[str, Any]):
        self.name = name
        self.model = model
        self.store = store
        self.misses = 0

    def estimate_cost(self, request: InterpreterInput) -> float:
        return 0.0

    def interpret(self, request: InterpreterInput) -> InterpreterOutput:
        recorded = self.store.get(trace_key(request))
        if recorded is None:
            self.misses += 1
            return InterpreterOutput(outcome="unavailable", error_code="not_recorded", metadata=InterpreterMetadata(
                adapter=self.name, provider="replay", model=self.model, latency_ms=0,
                usage=InterpreterUsage(provider_calls=0)))
        return InterpreterOutput.model_validate(recorded)


def _adapter_name(tier: str) -> str:
    return "openai_responses" if tier == "luna" else tier


def cascade_config(name: str, tiers: list[Tier], veto_min: float = 0.5) -> Configuration:
    adapter = TieredAdapter(tiers, veto_min=veto_min)
    return Configuration(name, adapter, ThresholdCascadePolicy(adapter.model, thresholds=CASCADE_POLICY_THRESHOLDS),
                         fallback_enabled=False)


def collect(cases: list[LabeledCase], candidates_for, adapters: dict[str, Any], guard: SpendGuard, *,
            deadline_ms: int = 30_000, expand: Expander | None = None) -> dict[str, Any]:
    """Run each tier once per case. `adapters` maps tier name ("laya", "jev", "luna") to a
    live adapter, in cascade order."""
    stores: dict[str, dict[str, Any]] = {name: {} for name in adapters}
    tiers = [Tier(name, RecordingAdapter(adapter, stores[name]), None if name == "luna" else RECORD_ALL)
             for name, adapter in adapters.items()]
    config = cascade_config("record-all", tiers)
    candidates: dict[str, Any] = {}
    stopped = None
    for case in cases:
        cands = candidates_for(case)
        candidates[case.id] = cands.model_dump(mode="json")
        result = drive(config, case.question, case.context, cands, guard=guard, deadline_ms=deadline_ms, expand=expand)
        if result.budget_blocked:
            stopped = f"spend cap reached at {case.id}"
            break
    return {
        "tiers": {name: {"model": adapters[name].model, "outputs": stores[name]} for name in adapters},
        "candidates": candidates,
        "spend": {"cap_usd": guard.cap_usd, "spent_usd": round(guard.spent_usd, 6)},
        "stopped_reason": stopped,
    }


def replay_tiers(trace: dict[str, Any], thresholds: dict[str, float | None]) -> list[Tier]:
    tiers = []
    for name, accept_min in thresholds.items():
        recorded = trace["tiers"][name]
        tiers.append(Tier(name, ReplayAdapter(_adapter_name(name), recorded["model"], recorded["outputs"]), accept_min))
    return tiers


def evaluate(cases: list[LabeledCase], trace: dict[str, Any], thresholds: dict[str, float | None], *,
             veto_min: float = 0.5, expand: Expander | None = None) -> tuple[Run, dict[str, Any]]:
    """Replay one threshold configuration over every case (no provider calls)."""
    tiers = replay_tiers(trace, thresholds)
    name = ",".join(f"{k}={v}" for k, v in thresholds.items()) + f",veto={veto_min}"
    config = cascade_config(name, tiers, veto_min)
    # Replays spend nothing; the guard only totals recorded list-price costs.
    guard = SpendGuard(1e9)
    run = Run(scores={name: []}, not_run={name: []})
    for case in cases:
        if case.id not in trace["candidates"]:
            run.not_run[name].append(case.id)
            continue
        cands = CandidateLookupResult.model_validate(trace["candidates"][case.id])
        result = drive(config, case.question, case.context, cands, guard=guard, expand=expand)
        run.scores[name].append(score(case, name, result))
    summary = summarize({c.id: c for c in cases}, run.scores[name])
    summary["replay_misses"] = sum(t.adapter.misses for t in tiers)
    summary["tier_share"] = _tier_share(run.scores[name], trace, cases, thresholds, veto_min)
    return run, summary


def _tier_share(scores, trace, cases, thresholds, veto_min) -> dict[str, int]:
    """How many cases each tier finished (the last tier that decided a field)."""
    counts: dict[str, int] = {}
    tiers = replay_tiers(trace, thresholds)
    adapter = TieredAdapter(tiers, veto_min=veto_min)
    by_id = {c.id: c for c in cases}
    for s in scores:
        case = by_id[s.case_id]
        cands = CandidateLookupResult.model_validate(trace["candidates"][case.id])
        out = adapter.interpret(InterpreterInput(question=case.question, context=case.context, candidates=cands,
                                                 deadline_ms=30_000, max_cost_usd=0))
        used = [t.name for t in tiers if t.name in set(out.metadata.field_tiers.values())]
        key = used[-1] if used else "none"
        counts[key] = counts.get(key, 0) + 1
    return counts


def sweep(cases: list[LabeledCase], trace: dict[str, Any], grids: dict[str, Iterable[float | None]], *,
          veto_mins: Iterable[float] = (0.5,), expand: Expander | None = None) -> list[dict[str, Any]]:
    names = list(grids)
    rows = []
    for combo in itertools.product(*(list(grids[n]) for n in names)):
        for veto_min in veto_mins:
            thresholds = dict(zip(names, combo))
            _, summary = evaluate(cases, trace, thresholds, veto_min=veto_min, expand=expand)
            rows.append({"thresholds": thresholds, "veto_min": veto_min, **summary})
    return rows


# -- field oracle -------------------------------------------------------------------------


def expected_fields(case: LabeledCase) -> dict[str, Any]:
    """Field -> expected value set for accept labels. Omitted fields are not scored."""
    if case.action != "accept" or case.request is None:
        return {}
    r = case.request
    expected: dict[str, Any] = {"intent": {r.intent}}
    if r.intent == "game_search":
        expected["date"] = {(r.dates.start, r.dates.end)}
        expected["teams"] = {t.team_id for t in r.teams}
    elif r.intent == "boxscore_stat":
        expected["stat_scope"] = {r.scope}
        expected["stat"] = {r.stat.stat}
        expected["aggregation"] = {r.stat.aggregation}
        if r.player is not None:
            expected["player"] = {r.player.player_id}
        if r.scope == "team" and r.team is not None:
            expected["target_team"] = {r.team.team_id}
        game = r.game
        if game.date is not None:
            expected["date"] = {(game.date, game.date)}
        if game.season is not None:
            expected["season"] = {game.season}
        if game.round is not None:
            expected["round"] = {game.round}
        if game.game_number is not None:
            expected["game_number"] = {game.game_number}
    elif r.intent == "playoff_series":
        expected["season"] = {r.season}
        expected["teams"] = {t.team_id for t in r.teams}
        expected["round"] = {r.round} if r.round else set()
    elif r.intent == "postseason_summary":
        expected["season"] = {r.season}
        expected["teams"] = {r.team.team_id} if r.team else set()
    elif r.intent == "player_season_stats":
        expected.update(player={r.player.player_id}, season={r.season}, stat={r.stat.stat},
                        aggregation={r.stat.aggregation}, season_type={r.season_type},
                        teams={r.team.team_id} if r.team else set())
    elif r.intent == "team_records":
        expected.update(season={r.season}, teams={r.team.team_id} if r.team else set(),
                        season_type={"regular_season"}, standings_scope={r.standings_scope})
    elif r.intent == "season_leaders":
        expected.update(season={r.season}, stat={r.stat.stat}, aggregation={r.stat.aggregation},
                        season_type={r.season_type})
    return expected


def _values(field: str, selected: list[str], candidates: CandidateLookupResult) -> set[Any] | None:
    if field in ("intent", "stat_scope", "stat", "aggregation", "season_type", "standings_scope"):
        return set(selected)
    values = set()
    for cid in selected:
        candidate = candidates.by_id(cid)
        if candidate is None:
            return None
        v = candidate.value
        if v.kind == "team":
            values.add(v.team.team_id)
        elif v.kind == "player":
            values.add(v.player.player_id)
        elif v.kind == "date":
            if v.resolved is None:
                return None
            values.add((v.resolved.start, v.resolved.end))
        elif v.kind == "season":
            values.add(v.season)
        elif v.kind == "round":
            values.add(v.round)
        elif v.kind == "game_number":
            values.add(v.game_number)
    return values


@dataclass
class FieldRead:
    case_id: str
    field: str
    confidence: float
    correct: bool


def field_reads(cases: list[LabeledCase], trace: dict[str, Any], tier: str) -> list[FieldRead]:
    """Scored `selected` reads from one tier's first attempt on each accept case."""
    store = trace["tiers"][tier]["outputs"]
    reads = []
    for case in cases:
        expected = expected_fields(case)
        if not expected or case.id not in trace["candidates"]:
            continue
        cands = CandidateLookupResult.model_validate(trace["candidates"][case.id])
        request = InterpreterInput(question=case.question, context=case.context, candidates=cands,
                                   deadline_ms=0, max_cost_usd=0)
        recorded = store.get(trace_key(request))
        if recorded is None:
            continue
        output = InterpreterOutput.model_validate(recorded)
        relevant = RELEVANT_FIELDS[case.request.intent] | {"intent"}
        for read in output.fields:
            if read.field not in relevant or read.field not in expected or read.confidence is None:
                continue
            if read.status == "selected":
                got = _values(read.field, read.selected, cands)
                reads.append(FieldRead(case.id, read.field, read.confidence, got == expected[read.field]))
            elif read.status == "absent" and read.field in expected:
                defaults = {"aggregation": {"total"}, "season_type": {"regular_season"}, "standings_scope": {"league"}}
                got = defaults.get(read.field, set())
                reads.append(FieldRead(case.id, read.field, read.confidence, got == expected[read.field]))
    return reads


def tier_stats(reads: list[FieldRead], threshold: float) -> dict[str, Any]:
    accepted = [r for r in reads if r.confidence >= threshold]
    wrong = [r for r in accepted if not r.correct]
    return {
        "threshold": threshold,
        "scored_fields": len(reads),
        "accepted": len(accepted),
        "coverage": round(len(accepted) / len(reads), 4) if reads else None,
        "precision": round(1 - len(wrong) / len(accepted), 4) if accepted else None,
        "errors": [f"{r.case_id}:{r.field}" for r in wrong],
    }


def calibrate_tier(reads: list[FieldRead], *, precision_min: float = 0.98,
                   grid: Iterable[float] = tuple(x / 100 for x in range(50, 100))) -> dict[str, Any]:
    """Lowest threshold (most coverage) at and above which accepted-field precision
    meets the gate. Precision is not monotonic in the threshold, so a lucky dip below a
    failing threshold is never chosen."""
    rows = [tier_stats(reads, t) for t in sorted(grid)]
    chosen = None
    for row in reversed(rows):
        if row["precision"] is not None and row["precision"] < precision_min:
            break
        if row["accepted"]:
            chosen = row
    return {"chosen": chosen, "curve": rows}
