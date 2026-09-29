"""CascadePolicy implementing the #199 fallback table.

`ThresholdCascadePolicy(primary_model="jev-1.13.0")` is the single-provider policy (it
never returns "fallback"); adding `fallback=("openai_responses", "gpt-6-luna")` makes it
the Jev -> Luna cascade.

| Situation (last attempt)                                   | Decision                                    |
| ---------------------------------------------------------- | ------------------------------------------- |
| valid request, weakest relevant confidence >= accept_min    | accept                                      |
| valid request, a relevant field below accept_min           | fallback once, else clarify that field      |
| clarification (missing/ambiguous/year) read confidently    | clarify; the fallback never fills the gap   |
| clarification read with low confidence                     | fallback once, else clarify                 |
| no_matching_candidate                                      | expand that field once, else clarify        |
| unsupported (adapter or normalizer)                        | unsupported                                 |
| unreliable / invalid output                                | fallback once, else clarify-or-fail         |
| primary unavailable                                        | fallback if enabled and budget/time allow   |
| both paths unreliable                                      | clarify if the user can resolve it, else fail |

`not_found` / `unavailable` from the basketball data service are decided after execution
by #201 and never reach this policy: switching models does not repair a data source.
"""

from __future__ import annotations

from dataclasses import dataclass

from server.ask.models.interpreter import AdapterName, CANDIDATE_BACKED_FIELDS
from server.ask.normalize import relevant_fields
from server.ask.protocols import CascadeAttempt, CascadeDecision, CascadeState


@dataclass(frozen=True)
class PolicyThresholds:
    """UNCALIBRATED placeholders. Calibrate on development data before production;
    cookbook values are not production settings."""

    # Weakest relevant field confidence needed to accept a valid request.
    accept_min: float = 0.7
    # Confidence needed to trust an absent/ambiguous read enough to ask the user.
    clarify_min: float = 0.6
    # Minimum remaining budget/time before a fallback attempt.
    min_fallback_budget_usd: float = 0.002
    min_fallback_ms: int = 3000
    max_expansions: int = 1


class ThresholdCascadePolicy:
    """Implements `server.ask.protocols.CascadePolicy`."""

    def __init__(
        self,
        primary_model: str,
        fallback: tuple[AdapterName, str] | None = None,
        thresholds: PolicyThresholds | None = None,
    ):
        if fallback is not None and fallback[1] == primary_model:
            raise ValueError("fallback model must differ from the primary model")
        self.primary_model = primary_model
        self.fallback = fallback
        self.thresholds = thresholds or PolicyThresholds()

    # -- helpers ----------------------------------------------------------------------

    def _fallback_used(self, state: CascadeState) -> bool:
        return self.fallback is not None and any(
            a.output.metadata.model == self.fallback[1] for a in state.attempts
        )

    def _fallback_blocker(self, state: CascadeState) -> str | None:
        if self.fallback is None:
            return "no fallback configured"
        if self._fallback_used(state):
            return "fallback already used"
        if not state.fallback_enabled:
            return "fallback disabled"
        if state.remaining_budget_usd < self.thresholds.min_fallback_budget_usd:
            return "insufficient budget for fallback"
        if state.remaining_ms < self.thresholds.min_fallback_ms:
            return "insufficient time for fallback"
        return None

    def _fallback_or(self, state: CascadeState, reason: str, otherwise: CascadeDecision) -> CascadeDecision:
        if self._fallback_blocker(state) is None:
            return CascadeDecision(action="fallback", adapter=self.fallback[0], reason=reason[:120])
        return otherwise

    @staticmethod
    def _weakest(attempt: CascadeAttempt) -> tuple[str | None, float | None]:
        output = attempt.output
        relevant = relevant_fields(output)
        scored = [(f.field, f.confidence) for f in output.fields if f.field in relevant and f.confidence is not None]
        if not scored:
            return None, None
        return min(scored, key=lambda fc: fc[1])

    def _give_up(self, state: CascadeState, reason: str) -> CascadeDecision:
        """Both paths unreliable: clarify when some attempt pinned down the unclear
        field, otherwise report failure. Never execute guessed parameters."""
        for attempt in reversed(state.attempts):
            norm = attempt.normalization
            if norm is not None and norm.status == "needs_clarification":
                return CascadeDecision(action="clarify", field=norm.clarify_field, reason=reason[:120])
            if norm is not None and norm.status == "valid":
                field, _ = self._weakest(attempt)
                if field is not None:
                    return CascadeDecision(action="clarify", field=field, reason=reason[:120])
        return CascadeDecision(action="fail", reason=reason[:120])

    # -- policy -----------------------------------------------------------------------

    def decide(self, state: CascadeState) -> CascadeDecision:
        if not state.attempts:
            return CascadeDecision(action="fail", reason="no interpreter attempts")
        t = self.thresholds
        last = state.attempts[-1]
        output = last.output
        norm = last.normalization

        if output.outcome == "unavailable":
            return self._fallback_or(
                state, f"interpreter unavailable ({output.error_code})",
                self._give_up(state, f"interpreter unavailable ({output.error_code})"),
            )
        if output.outcome == "unsupported":
            return CascadeDecision(action="unsupported", reason=f"out of scope ({output.unsupported_reason})")
        if output.outcome == "unreliable" or norm is None or norm.status == "invalid":
            why = "unreliable interpretation" if output.outcome == "unreliable" else "invalid interpretation"
            return self._fallback_or(state, why, self._give_up(state, why))
        if norm.status == "unsupported":
            return CascadeDecision(action="unsupported", reason=f"out of scope ({norm.unsupported_reason})")

        if norm.status == "valid":
            field, confidence = self._weakest(last)
            if confidence is None or confidence >= t.accept_min:
                return CascadeDecision(action="accept", reason="complete request")
            clarify = CascadeDecision(action="clarify", field=field, reason=f"low confidence in {field}")
            return self._fallback_or(state, f"low confidence in {field}", clarify)

        # needs_clarification
        field = norm.clarify_field
        if norm.clarify_reason == "no_matching_candidate":
            expanded = len(state.expanded_fields)
            candidate_field = "team" if field == "teams" else field
            if (
                field in CANDIDATE_BACKED_FIELDS
                and candidate_field not in state.expanded_fields
                and expanded < t.max_expansions
            ):
                return CascadeDecision(action="expand_candidates", field=field, reason=f"no candidate for {field}")
            return CascadeDecision(action="clarify", field=field, reason=f"no candidate for {field}")

        read = output.get_field(field)
        confidence = read.confidence if read is not None else None
        intent = output.get_field("intent")
        intent_confidence = intent.confidence if intent is not None else None
        shaky = [c for c in (confidence, intent_confidence) if c is not None and c < t.clarify_min]
        clarify = CascadeDecision(action="clarify", field=field, reason=f"{norm.clarify_reason} {field}")
        if shaky:
            return self._fallback_or(state, f"unsure whether {field} is {norm.clarify_reason}", clarify)
        return clarify
