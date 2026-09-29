"""Tiered interpreter cascade (ADR 0002): Laya, then Jev, then GPT Luna.

`TieredAdapter` implements `InterpreterAdapter`, so the pipeline's cache, budget, and
normalizer treat the whole cascade as one interpreter. Each tier interprets the full
question; the adapter keeps a field from the first tier that reads it confidently:

* Laya and Jev accept a field when its confidence meets that tier's calibrated
  `accept_min`. Fields below it escalate to the next tier.
* The final tier (Luna) reports no confidence, so its reads are accepted as-is.
* Escalation stops as soon as every field the accepted intent needs is decided.

Vetoes (ADR 0002 consequence, needed for the zero-guess gate): when a later confident
read selects different values, or reads the field as absent, after an earlier tier
accepted a selection, the field is not executed. The final tier, which reports no
confidence, is also vetoed by an earlier selection that reached `veto_min`. Two
different selections become `ambiguous`; selected versus absent keeps a sub-threshold
confidence so the policy clarifies it. The user is asked instead of either tier's
answer being trusted.

The merged output drops confidence from decided fields and keeps it on undecided ones.
Paired with `CASCADE_POLICY_THRESHOLDS` (accept_min=1.0), the cascade policy then
clarifies any field no tier decided and never executes a low-confidence read.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from server.ask.interpreters.cascade import PolicyThresholds
from server.ask.models.interpreter import (
    FieldInterpretation,
    InterpreterInput,
    InterpreterMetadata,
    InterpreterOutput,
    InterpreterUsage,
)
from server.ask.normalize import relevant_fields
from server.ask.protocols import InterpreterAdapter

# Any field that still carries a confidence after merging was not decided by a tier.
CASCADE_POLICY_THRESHOLDS = PolicyThresholds(accept_min=1.0, clarify_min=0.0)


@dataclass(frozen=True)
class Tier:
    """One cascade position. `accept_min=None` marks the final tier (no confidences)."""

    name: str  # "laya", "jev", "luna"
    adapter: InterpreterAdapter
    accept_min: float | None


@dataclass
class _Merge:
    decided: dict[str, FieldInterpretation] = field(default_factory=dict)
    decided_by: dict[str, str] = field(default_factory=dict)
    # Best undecided read per field, with its confidence.
    pending: dict[str, FieldInterpretation] = field(default_factory=dict)
    # Earlier `selected` reads that can veto a later disagreement, with whether each was
    # accepted (vetoes any tier) or merely reached `veto_min` (vetoes only the final tier).
    vetoers: dict[str, list[tuple[FieldInterpretation, bool]]] = field(default_factory=dict)
    vetoed: set[str] = field(default_factory=set)


def _confident(tier: Tier, read: FieldInterpretation) -> bool:
    if tier.accept_min is None:
        return True
    return read.confidence is not None and read.confidence >= tier.accept_min


def _same(a: list[str], b: list[str]) -> bool:
    return sorted(a) == sorted(b)


class TieredAdapter:
    """Implements `server.ask.protocols.InterpreterAdapter`."""

    name = "cascade"
    provider = "cascade"

    def __init__(self, tiers: list[Tier], *, veto_min: float = 0.5):
        if not tiers:
            raise ValueError("a cascade needs at least one tier")
        if any(t.accept_min is None for t in tiers[:-1]):
            raise ValueError("only the final tier may omit accept_min")
        self.tiers = tiers
        self.veto_min = veto_min
        self.model = "+".join(t.adapter.model for t in tiers)[:80]
        # Cache keys must change whenever tiers or thresholds change.
        self.label = ";".join(f"{t.name}:{t.adapter.model}:{t.accept_min}" for t in tiers) + f";veto:{veto_min}"

    def estimate_cost(self, request: InterpreterInput) -> float:
        return sum(t.adapter.estimate_cost(request) for t in self.tiers)

    # -- merging ------------------------------------------------------------------

    def _absorb(self, merge: _Merge, tier: Tier, output: InterpreterOutput) -> None:
        for read in output.fields:
            name = read.field
            confident = _confident(tier, read)
            if confident and read.status in ("selected", "absent"):
                for earlier, accepted in merge.vetoers.get(name, []):
                    if not accepted and tier.accept_min is not None:
                        continue
                    if read.status != "selected" or not _same(earlier.selected, read.selected):
                        merge.vetoed.add(name)
            if name in merge.decided:
                continue
            if confident:
                merge.decided[name] = read.model_copy(update={"confidence": None})
                merge.decided_by[name] = tier.name
                merge.pending.pop(name, None)
            else:
                best = merge.pending.get(name)
                if best is None or (read.confidence or 0) >= (best.confidence or 0):
                    merge.pending[name] = read
        # Register this tier's reads as vetoers only after comparing, so a tier never
        # vetoes itself.
        for read in output.fields:
            if read.status != "selected":
                continue
            accepted = _confident(tier, read)
            if accepted or (read.confidence is not None and read.confidence >= self.veto_min):
                merge.vetoers.setdefault(read.field, []).append((read, accepted))

    @staticmethod
    def _needed(merge: _Merge) -> frozenset[str]:
        intent = merge.decided.get("intent")
        probe = InterpreterOutput(
            outcome="interpreted", fields=[intent] if intent else [],
            metadata=InterpreterMetadata(adapter="cascade", provider="cascade", model="probe", latency_ms=0),
        )
        return relevant_fields(probe)

    def _complete(self, merge: _Merge) -> bool:
        return "intent" in merge.decided and self._needed(merge) <= merge.decided.keys()

    def _fields(self, merge: _Merge) -> list[FieldInterpretation]:
        fields = {**merge.pending, **merge.decided}
        for name in merge.vetoed & self._needed(merge):
            reads = [read for read, _ in merge.vetoers[name]]
            options: list[str] = []
            for read in reads:
                options.extend(v for v in read.selected if v not in options)
            if len(options) >= 2:
                fields[name] = FieldInterpretation(field=name, status="ambiguous", alternatives=options[:12])
            else:
                # Selected versus absent: keep the earlier selection but below certainty,
                # so the cascade policy asks the user rather than executing either read.
                fields[name] = reads[0].model_copy(update={"confidence": min(reads[0].confidence or 0.5, 0.5)})
            merge.decided_by[name] = "veto"
        return list(fields.values())

    # -- InterpreterAdapter -----------------------------------------------------------

    def interpret(self, request: InterpreterInput) -> InterpreterOutput:
        started = time.perf_counter()
        deadline = time.monotonic() + request.deadline_ms / 1000
        spent = 0.0
        cost_known = True
        calls = 0
        tokens_in = 0
        merge = _Merge()
        extracted_date = None
        last: InterpreterOutput | None = None

        for tier in self.tiers:
            remaining_ms = int((deadline - time.monotonic()) * 1000)
            if remaining_ms <= 0:
                break
            attempt = request.model_copy(update={
                "deadline_ms": remaining_ms,
                "max_cost_usd": max(0.0, request.max_cost_usd - spent),
            })
            output = tier.adapter.interpret(attempt)
            usage = output.metadata.usage
            calls += usage.provider_calls
            tokens_in += usage.input_tokens or 0
            if usage.provider_calls:
                if usage.cost_usd is None:
                    cost_known = False
                else:
                    spent += usage.cost_usd
            if output.outcome == "unavailable":
                continue
            last = output
            if output.outcome == "unsupported":
                merge.decided_by = {"intent": tier.name}
                return self._result(output.model_copy(update={"fields": []}), started, calls, tokens_in,
                                    spent if cost_known else None, merge)
            self._absorb(merge, tier, output)
            if output.extracted_date is not None and "date" not in merge.decided:
                extracted_date = output.extracted_date
            if self._complete(merge):
                break

        if last is None:
            unavailable = InterpreterOutput(outcome="unavailable", error_code="all_tiers_unavailable",
                                            metadata=self._metadata(started, calls, tokens_in,
                                                                    spent if cost_known else None, merge))
            return unavailable
        fields = self._fields(merge)
        outcome = "interpreted" if "intent" in merge.decided else "unreliable"
        merged = InterpreterOutput(outcome=outcome, fields=fields, extracted_date=extracted_date,
                                   metadata=last.metadata)
        return self._result(merged, started, calls, tokens_in, spent if cost_known else None, merge)

    def _metadata(self, started: float, calls: int, tokens_in: int, cost: float | None,
                  merge: _Merge) -> InterpreterMetadata:
        return InterpreterMetadata(
            adapter="cascade", provider="cascade", model=self.model,
            resolved_model=None,
            latency_ms=int((time.perf_counter() - started) * 1000),
            usage=InterpreterUsage(input_tokens=tokens_in or None, provider_calls=calls,
                                   cost_usd=cost if calls else None),
            field_tiers=dict(merge.decided_by),
        )

    def _result(self, output: InterpreterOutput, started: float, calls: int, tokens_in: int,
                cost: float | None, merge: _Merge) -> InterpreterOutput:
        return output.model_copy(update={"metadata": self._metadata(started, calls, tokens_in, cost, merge)})
