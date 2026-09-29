"""Interfaces between Ask components. Typed stubs only; no implementation.

All calls are synchronous (existing NBA services use ``requests``); the
endpoint runs them in FastAPI's threadpool. Implementations must not depend on
HTTP request objects, so resolvers, lookup, and adapters stay reusable in
scripts and evaluations.

Frozen contract (docs/ask-contract.md). Coordinate before changing.
"""

from __future__ import annotations

from typing import Literal, Protocol, runtime_checkable

from pydantic import Field

from .models.candidates import CandidateField, CandidateLookupResult, CandidateSet
from .models.common import ContractModel
from .models.interpreter import (
    AdapterName,
    InterpreterField,
    InterpreterInput,
    InterpreterOutput,
    NormalizationResult,
)
from .models.request import AskContext


@runtime_checkable
class CandidateLookup(Protocol):
    """#200. Bounded, typed candidates from question text + app context."""

    alias_version: str  # included in cache keys

    def lookup(self, question: str, context: AskContext) -> CandidateLookupResult:
        """Return a CandidateSet for every CandidateField. Never raises for
        "no match"; report ``no_candidates`` instead."""
        ...

    def expand(
        self, question: str, context: AskContext, field: CandidateField, previous: CandidateSet
    ) -> CandidateSet:
        """Widen one field's search (looser matching, more history) within
        the same per-field limit. Used by the cascade when an interpreter
        reports ``no_matching_candidate``. Returns ``previous`` if nothing new."""
        ...


@runtime_checkable
class InterpreterAdapter(Protocol):
    """#199. One provider/model. Jev and OpenAI-Responses (gpt-4.1-mini,
    Luna) implement this."""

    name: AdapterName
    model: str  # pinned, e.g. "jev-1.13.0", "gpt-4.1-mini-2025-04-14"

    def interpret(self, request: InterpreterInput) -> InterpreterOutput:
        """Must not raise for provider failures, timeouts, or quota; return
        ``outcome="unavailable"`` with an ``error_code``. Must respect
        ``request.deadline_ms`` and ``request.max_cost_usd``."""
        ...


@runtime_checkable
class RequestNormalizer(Protocol):
    """#199 implements, #201 calls. Validates an InterpreterOutput against the
    candidates and context and builds an AskRequest. Pure; no I/O."""

    def normalize(
        self, output: InterpreterOutput, candidates: CandidateLookupResult, context: AskContext
    ) -> NormalizationResult: ...


class CascadeAttempt(ContractModel):
    output: InterpreterOutput
    normalization: NormalizationResult | None = None  # None if outcome was not "interpreted"


class CascadeState(ContractModel):
    attempts: list[CascadeAttempt] = Field(default_factory=list, max_length=4)
    candidates: CandidateLookupResult
    expanded_fields: list[CandidateField] = Field(default_factory=list)
    fallback_enabled: bool
    remaining_budget_usd: float = Field(ge=0)
    remaining_ms: int = Field(ge=0)


class CascadeDecision(ContractModel):
    action: Literal[
        "accept",  # execute attempts[-1].normalization.request
        "fallback",  # run `adapter` once more on the original question
        "expand_candidates",  # expand `field`, then re-run the last adapter
        "clarify",  # ask the user about `field`
        "unsupported",
        "fail",  # report unavailable; never execute guessed parameters
    ]
    adapter: AdapterName | None = None
    field: InterpreterField | None = None
    reason: str = Field(max_length=120)


@runtime_checkable
class CascadePolicy(Protocol):
    """#199 implements (single-provider or cascade), #201 drives it. Encodes
    the fallback table in #199; thresholds come from the evaluation."""

    def decide(self, state: CascadeState) -> CascadeDecision: ...
