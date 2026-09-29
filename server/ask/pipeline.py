"""Ask coordinator: one bounded interpretation, then verified Python data."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import logging
import re
import time
import uuid
from typing import Callable

from server.ask.candidates.lookup import CandidateLookupService
from server.ask.budget import DailyBudget
from server.ask.cache import AskCache
from server.ask.config import AskConfig
from server.ask.diagnostics import AskDiagnostics, DiagnosticEvent
from server.ask.interpreters.cascade import ThresholdCascadePolicy
from server.ask.interpreters.factory import build_cascade, build_policy
from server.ask.interpreters.openai_responses import INSTRUCTIONS
from server.ask.interpreters.tiered import TieredAdapter
from server.ask.models.common import NEW_YORK, canonical_json
from server.ask.models.interpreter import InterpreterInput, InterpreterOutput
from server.ask.models.request import AskContext, AskRequest, BoxscoreStatRequest, GameSearchRequest, GameSelector, StatSelection
from server.ask.models.response import AskQuery, AskResponse, InterpreterInfo, Notice
from server.ask.normalize import Normalizer
from server.ask.present import clarification, interpretation, notice, suggestions
from server.ask.protocols import CascadeAttempt, CascadeState
from server.ask.resolution import PendingResolution, ResolutionStore
from server.ask.resolvers import resolve
from server.ask.resolvers.errors import AmbiguousError, ClarificationError, NotFoundError, UnavailableError, UnsupportedError


logger = logging.getLogger(__name__)

_EXACT_DATE = re.compile(r"^(?:games|scores)(?: on| for)? (\d{4}-\d{2}-\d{2})\??$", re.IGNORECASE)
_EXACT_LEADERS = re.compile(r"^(?:who led in|leaders? in|most) (points|rebounds|assists|steals|blocks)\??$", re.IGNORECASE)


def _key(*parts: object) -> str:
    return hashlib.sha256(json.dumps(parts, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


class AskPipeline:
    def __init__(self, config: AskConfig | None = None, *, lookup=None, normalizer=None, adapter=None,
                 policy=None, cache=None, budget=None, resolutions: ResolutionStore | None = None,
                 diagnostics=None, clock: Callable[[], dt.datetime] | None = None):
        self.config = config or AskConfig.from_env()
        self.lookup = lookup or CandidateLookupService()
        self.normalizer = normalizer or Normalizer()
        self.adapter = adapter
        if policy is None:
            cascade = adapter is None or isinstance(adapter, TieredAdapter)
            # The same policy the release evaluation drives (`factory.build_policy`).
            policy = build_policy() if cascade else ThresholdCascadePolicy(primary_model=self.config.primary_model)
        self.policy = policy
        self.cache = cache if cache is not None else AskCache(max_entries=self.config.cache_max_entries, version=self.config.cache_version)
        self.budget = budget if budget is not None else DailyBudget(self.config.state_dir, self.config.daily_budget_usd)
        self.resolutions = resolutions or ResolutionStore(self.config.state_dir / "resolution.sqlite3")
        self.diagnostics = diagnostics if diagnostics is not None else AskDiagnostics()
        self.clock = clock or (lambda: dt.datetime.now(NEW_YORK))

    def _adapter(self):
        if self.adapter is None:
            self.adapter = build_cascade(self.config)
        return self.adapter

    def _context(self, query: AskQuery) -> AskContext:
        now = self.clock()
        client = query.context
        return AskContext(reference_time=now, route=client.route if client else None,
                          view_date=client.view_date if client else None,
                          game_id=client.game_id if client else None,
                          playoff_season=client.playoff_season if client else None)

    def _info(self, *, called: bool = False, hit: bool = False, adapter=None,
              output: InterpreterOutput | None = None) -> InterpreterInfo:
        metadata = output.metadata if output is not None else None
        field_tiers = dict(metadata.field_tiers) if metadata else {}
        first = adapter.tiers[0].name if isinstance(adapter, TieredAdapter) else None
        # Per-field tier details are development-only (ADR 0010); production responses
        # carry neither the tiers nor the confidences.
        details = self.config.dev and metadata is not None
        return InterpreterInfo(
            model_called=called, cache_hit=hit,
            adapter=metadata.adapter if metadata else adapter.name if adapter else None,
            model=(metadata.resolved_model or metadata.model) if metadata else adapter.model if adapter else None,
            fallback_used=first is not None and any(tier not in (first, "veto") for tier in field_tiers.values()),
            field_tiers=field_tiers if details else {},
            field_decisions=list(metadata.field_decisions) if details else [],
        )

    @staticmethod
    def _response(question: str, outcome: str, info: InterpreterInfo, **kwargs) -> AskResponse:
        return AskResponse(request_id=uuid.uuid4().hex, outcome=outcome, question=question,
                           interpreter=info, **kwargs)

    def disabled(self, question: str) -> AskResponse:
        return self._response(question, "unavailable", self._info(),
                              notice=notice("service_unavailable"))

    def _exact(self, question: str, context: AskContext) -> AskRequest | None:
        match = _EXACT_DATE.fullmatch(question.strip())
        if match:
            try:
                day = dt.date.fromisoformat(match[1])
                return GameSearchRequest(dates={"start": day, "end": day})
            except ValueError:
                return None
        leader = _EXACT_LEADERS.fullmatch(question.strip())
        if leader and context.route == "boxscore" and context.game_id:
            return BoxscoreStatRequest(scope="leaders", stat=StatSelection(stat=leader[1].lower()),
                                       game=GameSelector(game_id=context.game_id))
        return None

    def _parse_key(self, question: str, context: AskContext, alias_version: str, adapter) -> str:
        return _key(self.config.cache_version, "parse", "1", alias_version, adapter.model,
                    getattr(adapter, "label", adapter.model), hashlib.sha256(INSTRUCTIONS.encode()).hexdigest(),
                    canonical_json(context.model_copy(update={"reference_time": context.reference_time.replace(
                        hour=0, minute=0, second=0, microsecond=0)})),
                    " ".join(question.casefold().split()),
                    context.route, context.view_date, context.game_id, context.playoff_season)

    def _interpret(self, question: str, context: AskContext, candidates, deadline: float):
        from server.ask.cache import CacheValue
        adapter = self._adapter()
        stable_candidates = candidates.model_copy(update={"latency_ms": 0})
        key = _key(self._parse_key(question, context, candidates.alias_version, adapter), canonical_json(stable_candidates))

        def load():
            if time.monotonic() >= deadline:
                raise TimeoutError("Ask response deadline exceeded")
            remaining_ms = max(0, int((deadline - time.monotonic()) * 1000))
            budget_left = self.budget.remaining_usd() if self.budget else 1.0
            request = InterpreterInput(question=question, context=context, candidates=candidates,
                                       deadline_ms=remaining_ms, max_cost_usd=budget_left)
            estimate = adapter.estimate_cost(request)
            reservation = self.budget.reserve(adapter.model, estimate) if self.budget else None
            remaining_ms = int((deadline - time.monotonic()) * 1000)
            if remaining_ms <= 0:
                if reservation is not None:
                    self.budget.settle(reservation, 0.0)
                raise TimeoutError("Ask response deadline exceeded")
            request = request.model_copy(update={"deadline_ms": remaining_ms})
            try:
                output = adapter.interpret(request)
            except Exception:
                if reservation is not None:
                    self.budget.settle(reservation, None)
                raise
            if reservation is not None:
                usage = output.metadata.usage
                actual = usage.cost_usd if usage.provider_calls else 0.0
                self.budget.settle(reservation, actual)
            ttl = self.config.parse_ttl_seconds if output.outcome in {"interpreted", "unsupported"} else 0
            if output.outcome == "interpreted" and self.normalizer.normalize(output, candidates, context).status == "invalid":
                # A retry must be able to recover from a structurally valid
                # provider response that cannot form a valid request.
                ttl = 0
            return CacheValue(output, ttl)

        if self.cache is None:
            return load().value, False
        result = self.cache.get_or_load("parse", key, load)
        return result.value, result.hit

    def _execute(self, question: str, request: AskRequest, readout, info: InterpreterInfo) -> AskResponse:
        from server.ask.cache import CacheValue

        def load():
            output = resolve(request)
            ttl = self.config.answer_ttl_seconds if all(s.complete for s in output.sources) else min(30, self.config.answer_ttl_seconds)
            return CacheValue(output, ttl)

        try:
            if self.cache is not None:
                result = self.cache.get_or_load("answer", _key(
                    self.config.cache_version, "answer-1", self.lookup.alias_version,
                    readout.reference_time.date().isoformat(), canonical_json(request)), load)
                output, hit = result.value, result.hit
            else:
                output, hit = load().value, False
            info = info.model_copy(update={"cache_hit": info.cache_hit or hit})
            return self._response(question, "answer", info, interpretation=readout,
                                  result=output.result, links=list(output.links), sources=list(output.sources),
                                  spoiler_gate=output.spoiler_gate, suggestions=suggestions(request))
        except NotFoundError as error:
            return self._response(question, "not_found", info, interpretation=readout,
                                  notice=notice(error.code, reason=error.reason), spoiler_gate=error.spoiler_gate)
        except (AmbiguousError, ClarificationError) as error:
            return self._response(question, "needs_clarification", info, interpretation=readout,
                                  clarification={"field": error.field, "reason": error.clarify_reason,
                                                 "prompt": f"Which {error.field.replace('_', ' ')}?",
                                                 "hint": "Edit your question to identify one game or series."})
        except UnsupportedError as error:
            return self._response(question, "unsupported", info, interpretation=readout,
                                  notice=notice("unsupported", unsupported_reason=error.unsupported_reason))
        except UnavailableError:
            return self._response(question, "unavailable", info, interpretation=readout,
                                  notice=notice("service_unavailable"))

    def answer(self, query: AskQuery) -> AskResponse:
        from server.ask.budget import BudgetExhausted, BudgetUnavailable

        # Leave time for verified NBA retrieval after interpretation. The HTTP
        # boundary retains its full deadline and occupied-worker accounting.
        resolver_reserve = min(5.0, self.config.deadline_seconds / 4)
        deadline = time.monotonic() + self.config.deadline_seconds - resolver_reserve
        question, context = query.question, self._context(query)
        if not self.config.enabled:
            return self.disabled(question)
        pending = self.resolutions.read(query.resolution, question, context) if query.resolution else None
        if pending is not None:
            # Continue against server-stored candidates and original reference time.
            return self._from_pending(question, pending, self._info(output=pending.output))
        direct = self._exact(question, context)
        if direct is not None:
            return self._execute(question, direct, interpretation(None, None, context, direct), self._info())

        any_call = False
        cache_hit = False
        try:
            candidates = self.lookup.lookup(question, context)
            attempts = []
            expanded: list[str] = []
            for _ in range(3):
                output, hit = self._interpret(question, context, candidates, deadline)
                cache_hit = cache_hit or hit
                _log_decisions(output, hit)
                any_call = any_call or (not hit and output.metadata.usage.provider_calls > 0)
                normalized = self.normalizer.normalize(output, candidates, context) if output.outcome == "interpreted" else None
                attempts.append(CascadeAttempt(output=output, normalization=normalized))
                state = CascadeState(attempts=attempts, candidates=candidates, expanded_fields=expanded,
                                     fallback_enabled=False, remaining_budget_usd=self.budget.remaining_usd() if self.budget else 1,
                                     remaining_ms=max(0, int((deadline - time.monotonic()) * 1000)))
                decision = self.policy.decide(state)
                info = self._info(called=any_call,
                                  hit=cache_hit, adapter=self._adapter(), output=output)
                if decision.action == "accept":
                    return self._execute(question, normalized.request,
                                         interpretation(output, candidates, context, normalized.request), info)
                if decision.action == "clarify":
                    pending = PendingResolution(output, candidates, context)
                    clarify = clarification(decision.field, decision.clarify_reason, question, pending, self.resolutions)
                    return self._response(question, "needs_clarification", info,
                                          interpretation=interpretation(output, candidates, context), clarification=clarify)
                if decision.action == "unsupported":
                    reason = normalized.unsupported_reason if normalized and normalized.status == "unsupported" else output.unsupported_reason or "other"
                    recorded = self._diagnose(question, reason)
                    return self._response(question, "unsupported", info,
                                          interpretation=interpretation(output, candidates, context),
                                          notice=notice("unsupported", unsupported_reason=reason, diagnostics_recorded=recorded))
                if decision.action == "expand_candidates":
                    current = candidates.sets[decision.field]
                    widened = self.lookup.expand(question, context, decision.field, current)
                    candidates = candidates.model_copy(update={"sets": {**candidates.sets, decision.field: widened}})
                    expanded.append(decision.field)
                    continue
                break
            return self._response(question, "unavailable", self._info(called=any_call, hit=cache_hit),
                                  notice=notice("interpreter_unavailable"))
        except BudgetExhausted:
            return self._response(question, "budget_exhausted", self._info(called=any_call, hit=cache_hit),
                                  notice=notice("budget_exhausted"))
        except BudgetUnavailable:
            return self._response(question, "unavailable", self._info(called=any_call, hit=cache_hit),
                                  notice=notice("service_unavailable"))
        except Exception:
            # Provider text, prompts, and personal data never enter the response.
            return self._response(question, "unavailable", self._info(called=any_call, hit=cache_hit),
                                  notice=notice("interpreter_unavailable"))

    def _from_pending(self, question: str, pending: PendingResolution, info: InterpreterInfo) -> AskResponse:
        normalized = self.normalizer.normalize(pending.output, pending.candidates, pending.context)
        readout = interpretation(pending.output, pending.candidates, pending.context,
                                 normalized.request if normalized.status == "valid" else None)
        if normalized.status == "valid":
            return self._execute(question, normalized.request, readout, info)
        if normalized.status == "needs_clarification":
            clarify = clarification(normalized.clarify_field, normalized.clarify_reason, question,
                                    pending, self.resolutions)
            return self._response(question, "needs_clarification", info, interpretation=readout, clarification=clarify)
        if normalized.status == "unsupported":
            return self._response(question, "unsupported", info, interpretation=readout,
                                  notice=notice("unsupported", unsupported_reason=normalized.unsupported_reason))
        return self._response(question, "unavailable", info, notice=notice("interpreter_unavailable"))

    def _diagnose(self, question: str, reason: str) -> bool:
        if self.diagnostics is None:
            return False
        try:
            return self.diagnostics.record(DiagnosticEvent(question=question, operation="ask",
                                                           stat=None, missing_fields=(), reason=reason))
        except Exception:
            return False


def _log_decisions(output: InterpreterOutput, cache_hit: bool) -> None:
    """Log per-field tier decisions (ADRs 0009, 0010). Enumerated metadata only: never
    the question, candidate values, provider text, or keys."""
    metadata = output.metadata
    if not metadata.field_decisions and not metadata.field_tiers:
        return
    decisions = [decision.model_dump(mode="json") for decision in metadata.field_decisions]
    logger.info("ask cascade outcome=%s cache_hit=%s models=%s decisions=%s", output.outcome, cache_hit,
                metadata.resolved_model or metadata.model, json.dumps(decisions, separators=(",", ":")))


__all__ = ["AskPipeline", "build_cascade"]
