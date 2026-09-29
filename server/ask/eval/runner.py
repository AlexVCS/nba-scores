"""Evaluation driver and scoring for #199 (network-free; adapters are injected).

`drive()` runs one question through a configuration exactly as #201's pipeline will:
adapter -> normalizer -> policy, looping on fallback / expand decisions. `run()` does that
for every labeled case and configuration under one hard spend cap.

Scoring: a case is correct only when the final action matches the label and, for
`accept`, the normalized AskRequest equals the labeled request (team order ignored).
An `accept` with a wrong request, or where the label expects a clarification or
unsupported outcome, is a schema-valid guess and counts as a failure.
"""

from __future__ import annotations

import datetime as dt
import math
import statistics
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Protocol, get_args

from server.ask.interpreters.pricing import SpendCapExceeded, SpendGuard
from server.ask.models.candidates import CandidateLookupResult, CandidateSet
from server.ask.models.common import ClarifyField, ClarifyReason
from server.ask.models.interpreter import InterpreterInput, InterpreterOutput, UnsupportedReason
from server.ask.models.request import ASK_REQUEST_ADAPTER, AskContext
from server.ask.normalize import Normalizer, canonical_request
from server.ask.protocols import (
    ClarifyDecision,
    CascadeAttempt,
    CascadeDecision,
    CascadePolicy,
    CascadeState,
    FailDecision,
    InterpreterAdapter,
)

MAX_ATTEMPTS = 4
LABELED_ACTIONS = frozenset({"accept", "clarify", "unsupported"})
CLARIFY_FIELDS = frozenset(get_args(ClarifyField))
CLARIFY_REASONS = frozenset(get_args(ClarifyReason))
UNSUPPORTED_REASONS = frozenset(get_args(UnsupportedReason))

# Expand one candidate field: (question, context, candidate field, previous set) -> set.
Expander = Callable[[str, AskContext, str, CandidateSet], CandidateSet]


class CostEstimating(Protocol):
    def estimate_cost(self, request: InterpreterInput) -> float: ...


@dataclass
class Configuration:
    name: str
    primary: InterpreterAdapter
    policy: CascadePolicy
    fallback: InterpreterAdapter | None = None
    fallback_enabled: bool = True


@dataclass
class DriveResult:
    decision: CascadeDecision
    request: Any | None
    attempts: list[CascadeAttempt]
    expanded_fields: list[str]
    latency_ms: int
    cost_usd: float | None
    fallback_used: bool
    budget_blocked: bool = False


def _call(adapter: InterpreterAdapter, request: InterpreterInput, guard: SpendGuard) -> tuple[InterpreterOutput, bool]:
    """Call an adapter under the hard cap. Returns (output, blocked_by_budget)."""
    estimate = adapter.estimate_cost(request) if hasattr(adapter, "estimate_cost") else 0.0
    try:
        reserved = guard.reserve(estimate)
    except SpendCapExceeded:
        return _budget_output(adapter), True
    output = adapter.interpret(request)
    actual = output.metadata.usage.cost_usd
    if output.metadata.usage.provider_calls == 0:
        actual = 0.0
    guard.settle(reserved, actual)
    return output, output.error_code == "budget_exceeded"


def _budget_output(adapter: InterpreterAdapter) -> InterpreterOutput:
    from server.ask.models.interpreter import InterpreterMetadata, InterpreterUsage

    return InterpreterOutput(
        outcome="unavailable",
        error_code="budget_exceeded",
        metadata=InterpreterMetadata(
            adapter=adapter.name, provider=getattr(adapter, "provider", "unknown"), model=adapter.model,
            latency_ms=0, usage=InterpreterUsage(provider_calls=0),
        ),
    )


def drive(
    config: Configuration,
    question: str,
    context: AskContext,
    candidates: CandidateLookupResult,
    *,
    guard: SpendGuard,
    deadline_ms: int = 30_000,
    expand: Expander | None = None,
    normalizer: Normalizer | None = None,
    cached_primary: InterpreterOutput | None = None,
) -> DriveResult:
    normalizer = normalizer or Normalizer()
    started = time.perf_counter()
    cached_latency_ms = cached_primary.metadata.latency_ms if cached_primary is not None else 0
    attempts: list[CascadeAttempt] = []
    expanded: list[str] = []
    adapter = config.primary
    budget_blocked = False
    decision: CascadeDecision = FailDecision(reason="no attempts")

    for index in range(MAX_ATTEMPTS):
        elapsed = cached_latency_ms + int((time.perf_counter() - started) * 1000)
        remaining_ms = max(0, deadline_ms - elapsed)
        if index == 0 and cached_primary is not None:
            output = cached_primary
        else:
            request = InterpreterInput(
                question=question, context=context, candidates=candidates,
                deadline_ms=remaining_ms, max_cost_usd=guard.remaining_usd,
            )
            output, blocked = _call(adapter, request, guard)
            budget_blocked = budget_blocked or blocked
        normalization = (
            normalizer.normalize(output, candidates, context) if output.outcome == "interpreted" else None
        )
        attempts.append(CascadeAttempt(output=output, normalization=normalization))
        elapsed = cached_latency_ms + int((time.perf_counter() - started) * 1000)
        state = CascadeState(
            attempts=attempts, candidates=candidates, expanded_fields=expanded,
            fallback_enabled=config.fallback_enabled and config.fallback is not None,
            remaining_budget_usd=guard.remaining_usd, remaining_ms=max(0, deadline_ms - elapsed),
        )
        decision = config.policy.decide(state)
        if decision.action == "fallback" and config.fallback is not None:
            adapter = config.fallback
            continue
        if decision.action == "expand_candidates":
            cand_field = decision.field
            previous = candidates.sets[cand_field]
            grown = expand(question, context, cand_field, previous) if expand else previous
            if grown == previous or len(attempts) >= MAX_ATTEMPTS:
                interpreter_field = "teams" if cand_field == "team" else cand_field
                decision = ClarifyDecision(
                    field=interpreter_field, clarify_reason="no_matching_candidate",
                    reason="lookup could not expand",
                )
                break
            candidates = CandidateLookupResult(
                sets={**candidates.sets, cand_field: grown},
                alias_version=candidates.alias_version, latency_ms=candidates.latency_ms,
            )
            expanded.append(cand_field)
            continue
        break

    request = None
    if decision.action == "accept":
        request = attempts[-1].normalization.request
    fallback_model = config.fallback.model if config.fallback is not None else None
    return DriveResult(
        decision=decision,
        request=request,
        attempts=attempts,
        expanded_fields=expanded,
        latency_ms=int((time.perf_counter() - started) * 1000) + cached_latency_ms,
        cost_usd=(
            None if any(a.output.metadata.usage.provider_calls > 0
                        and a.output.metadata.usage.cost_usd is None for a in attempts)
            else sum(a.output.metadata.usage.cost_usd or 0.0 for a in attempts)
        ),
        fallback_used=fallback_model is not None and any(a.output.metadata.model == fallback_model for a in attempts),
        budget_blocked=budget_blocked,
    )


# -- labeled cases ------------------------------------------------------------------------


@dataclass
class LabeledCase:
    id: str
    question: str
    context: AskContext
    action: str  # accept | clarify | unsupported
    request: Any | None = None
    clarify_field: str | None = None
    clarify_reason: str | None = None
    unsupported_reason: str | None = None
    also_accept: frozenset[str] = frozenset()
    tags: tuple[str, ...] = ()
    # Hand-built candidates embedded in the fixture: smoke tests and probes only.
    candidates: CandidateLookupResult | None = None

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> LabeledCase:
        expected = data["expected"]
        case_id = data["id"]
        action = expected["action"]
        if action not in LABELED_ACTIONS:
            raise ValueError(f"{case_id}: unknown expected action {action!r}")
        if (action == "accept") != (expected.get("request") is not None):
            raise ValueError(f"{case_id}: request is required only for accept labels")
        if (action == "clarify") != (expected.get("clarify_field") is not None):
            raise ValueError(f"{case_id}: clarify_field is required only for clarify labels")
        if action == "clarify" and expected["clarify_field"] not in CLARIFY_FIELDS:
            raise ValueError(f"{case_id}: unknown clarify_field {expected['clarify_field']!r}")
        if expected.get("clarify_reason") is not None:
            if action != "clarify" or expected["clarify_reason"] not in CLARIFY_REASONS:
                raise ValueError(f"{case_id}: invalid clarify_reason {expected['clarify_reason']!r}")
        if (action == "unsupported") != (expected.get("unsupported_reason") is not None):
            raise ValueError(f"{case_id}: unsupported_reason is required only for unsupported labels")
        if action == "unsupported" and expected["unsupported_reason"] not in UNSUPPORTED_REASONS:
            raise ValueError(f"{case_id}: unknown unsupported_reason {expected['unsupported_reason']!r}")
        also_accept = frozenset(expected.get("also_accept", []))
        if also_accept - LABELED_ACTIONS or "accept" in also_accept:
            raise ValueError(f"{case_id}: invalid also_accept actions")
        context = AskContext.model_validate(
            {"reference_time": data["reference_time"], **(data.get("context") or {})}
        )
        request = ASK_REQUEST_ADAPTER.validate_python(expected["request"]) if action == "accept" else None
        return cls(
            id=case_id,
            question=data["question"],
            context=context,
            action=action,
            request=request,
            clarify_field=expected.get("clarify_field"),
            clarify_reason=expected.get("clarify_reason"),
            unsupported_reason=expected.get("unsupported_reason"),
            also_accept=also_accept,
            tags=tuple(data.get("tags", [])),
            candidates=CandidateLookupResult.model_validate(data["candidates"]) if data.get("candidates") else None,
        )


CandidateProvider = Callable[[LabeledCase], CandidateLookupResult]


def embedded_candidates(case: LabeledCase) -> CandidateLookupResult:
    """Hand-built fixture candidates (smoke tests and probes only)."""
    if case.candidates is None:
        raise ValueError(f"case {case.id} has no embedded candidates")
    return case.candidates


@dataclass
class CaseScore:
    case_id: str
    config: str
    action: str
    correct: bool
    guess: bool
    failure: str | None
    latency_ms: int
    cost_usd: float | None
    fallback_used: bool
    first_outcome: str
    resolved_models: list[str]
    error_codes: list[str]
    clarify_field: str | None = None
    unsupported_reason: str | None = None
    actual_request: dict[str, Any] | None = None


def scored_request(request: Any) -> dict[str, Any]:
    """Compare IDs and request parameters, ignoring required entity display fields.

    TeamRef and PlayerRef require names (and team tricodes) in the request
    schema. Lookup supplies those values; the interpreter selects the ID.
    The full actual request stays in CaseScore so display errors remain visible.
    """
    data = canonical_request(request)

    def strip_display(value: Any) -> None:
        if isinstance(value, dict):
            if "team_id" in value:
                value.pop("name", None)
                value.pop("tricode", None)
            elif "player_id" in value:
                value.pop("name", None)
            for child in value.values():
                strip_display(child)
        elif isinstance(value, list):
            for child in value:
                strip_display(child)

    strip_display(data)
    return data


def score(case: LabeledCase, config: str, result: DriveResult) -> CaseScore:
    action = result.decision.action
    failure = None
    guess = False
    if case.action == "accept":
        correct = action == "accept" and scored_request(result.request) == scored_request(case.request)
        if not correct:
            if action == "accept":
                guess, failure = True, "wrong_request"
            elif action == "clarify":
                failure = "unneeded_clarification"
            elif action == "unsupported":
                failure = "false_unsupported"
            else:
                failure = "service_failure"
    else:
        correct = action == case.action or action in case.also_accept
        if correct and action == "clarify" and case.clarify_field and result.decision.field != case.clarify_field:
            correct, failure = False, "wrong_clarify_field"
        elif correct and action == "unsupported" and case.unsupported_reason:
            actual_reason = next(
                (attempt.normalization.unsupported_reason for attempt in result.attempts[::-1]
                 if attempt.normalization is not None and attempt.normalization.status == "unsupported"),
                outputs_reason(result.attempts),
            )
            if actual_reason != case.unsupported_reason:
                correct, failure = False, "wrong_unsupported_reason"
        elif not correct:
            if action == "accept":
                guess, failure = True, "schema_valid_guess"
            elif action == "fail":
                failure = "service_failure"
            else:
                failure = f"expected_{case.action}_got_{action}"
    outputs = [a.output for a in result.attempts]
    return CaseScore(
        case_id=case.id,
        config=config,
        action=action,
        correct=correct,
        guess=guess,
        failure=failure,
        latency_ms=result.latency_ms,
        cost_usd=round(result.cost_usd, 8) if result.cost_usd is not None else None,
        fallback_used=result.fallback_used,
        first_outcome=outputs[0].outcome if outputs else "none",
        resolved_models=sorted({o.metadata.resolved_model for o in outputs if o.metadata.resolved_model}),
        error_codes=[o.error_code for o in outputs if o.error_code],
        clarify_field=result.decision.field if isinstance(result.decision, ClarifyDecision) else None,
        unsupported_reason=(
            next((a.normalization.unsupported_reason for a in result.attempts[::-1]
                  if a.normalization is not None and a.normalization.status == "unsupported"),
                 outputs_reason(result.attempts)) if action == "unsupported" else None
        ),
        actual_request=result.request.model_dump(mode="json") if action == "accept" and result.request else None,
    )


def outputs_reason(attempts: list[CascadeAttempt]) -> str | None:
    return next((a.output.unsupported_reason for a in attempts[::-1] if a.output.unsupported_reason), None)


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(1, math.ceil(pct / 100 * len(ordered))) - 1]


def summarize(cases: dict[str, LabeledCase], scores: list[CaseScore]) -> dict[str, Any]:
    n = len(scores)
    correct = sum(s.correct for s in scores)
    exp_clarify = [s for s in scores if cases[s.case_id].action == "clarify"]
    exp_unsupported = [s for s in scores if cases[s.case_id].action == "unsupported"]
    clarified = [s for s in scores if s.action == "clarify"]
    unsupported = [s for s in scores if s.action == "unsupported"]
    latencies = [s.latency_ms for s in scores]
    total_cost = None if any(s.cost_usd is None for s in scores) else sum(s.cost_usd for s in scores)
    return {
        "cases": n,
        "complete_request_accuracy": round(correct / n, 4) if n else None,
        "correct": correct,
        "schema_valid_guesses": sum(s.guess for s in scores),
        "service_failures": sum(s.failure == "service_failure" for s in scores),
        "clarification": {
            "expected": len(exp_clarify),
            "correct": sum(s.correct for s in exp_clarify),
            "issued": len(clarified),
            "unneeded": sum(cases[s.case_id].action != "clarify" for s in clarified),
        },
        "unsupported": {
            "expected": len(exp_unsupported),
            "correct": sum(s.correct for s in exp_unsupported),
            "issued": len(unsupported),
            "false": sum(cases[s.case_id].action != "unsupported" for s in unsupported),
        },
        "latency_ms": {"median": statistics.median(latencies) if latencies else None, "p95": percentile(latencies, 95)},
        "total_cost_usd": round(total_cost, 6) if total_cost is not None else None,
        "cost_per_successful_answer_usd": round(total_cost / correct, 6)
        if correct and total_cost is not None else None,
        "fallback_rate": round(sum(s.fallback_used for s in scores) / n, 4) if n else None,
        "resolved_models": sorted({m for s in scores for m in s.resolved_models}),
        "failures": {k: sum(s.failure == k for s in scores) for k in sorted({s.failure for s in scores if s.failure})},
    }


def fallback_effect(alone: list[CaseScore], cascade: list[CaseScore]) -> dict[str, list[str]]:
    base = {s.case_id: s for s in alone}
    return {
        "fixed": [s.case_id for s in cascade if s.case_id in base and s.correct and not base[s.case_id].correct],
        "worsened": [s.case_id for s in cascade if s.case_id in base and not s.correct and base[s.case_id].correct],
    }


@dataclass
class Run:
    scores: dict[str, list[CaseScore]] = field(default_factory=dict)
    not_run: dict[str, list[str]] = field(default_factory=dict)
    candidate_errors: dict[str, str] = field(default_factory=dict)
    stopped_reason: str | None = None


def run(
    cases: list[LabeledCase],
    candidate_provider: CandidateProvider,
    configs: list[Configuration],
    guard: SpendGuard,
    *,
    deadline_ms: int = 30_000,
    expand: Expander | None = None,
) -> Run:
    """Run every configuration on every case. Configurations sharing a primary adapter
    object reuse its first call, so the cascade and the primary alone see the same read."""
    result = Run(scores={c.name: [] for c in configs}, not_run={c.name: [] for c in configs})
    cache: dict[tuple[int, str], InterpreterOutput] = {}
    for case in cases:
        try:
            candidates = candidate_provider(case)
        except Exception as exc:  # external lookup; record and continue
            result.candidate_errors[case.id] = f"{type(exc).__name__}: {str(exc)[:200]}"
            continue
        for config in configs:
            if result.stopped_reason:
                result.not_run[config.name].append(case.id)
                continue
            key = (id(config.primary), case.id)
            outcome = drive(
                config, case.question, case.context, candidates, guard=guard,
                deadline_ms=deadline_ms, expand=expand, cached_primary=cache.get(key),
            )
            if outcome.budget_blocked:
                result.stopped_reason = "spend cap reached"
                result.not_run[config.name].append(case.id)
                continue
            cache.setdefault(key, outcome.attempts[0].output)
            result.scores[config.name].append(score(case, config.name, outcome))
    return result


def report(cases: list[LabeledCase], outcome: Run, configs: list[Configuration], guard: SpendGuard,
           meta: dict[str, Any]) -> dict[str, Any]:
    by_id = {c.id: c for c in cases}
    summaries: dict[str, Any] = {}
    for config in configs:
        summary = summarize(by_id, outcome.scores[config.name])
        summary["not_run"] = outcome.not_run[config.name]
        if config.fallback is not None:
            alone = next((c for c in configs if c.fallback is None and c.primary is config.primary), None)
            if alone is not None:
                summary["fallback_effect_vs_primary_alone"] = fallback_effect(
                    outcome.scores[alone.name], outcome.scores[config.name]
                )
        summaries[config.name] = summary
    return {
        **meta,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "spend": {"cap_usd": guard.cap_usd, "spent_usd": round(guard.spent_usd, 6)},
        "stopped_reason": outcome.stopped_reason,
        "candidate_errors": outcome.candidate_errors,
        "configs": summaries,
        "cases": {name: [asdict(s) for s in scores] for name, scores in outcome.scores.items()},
    }
