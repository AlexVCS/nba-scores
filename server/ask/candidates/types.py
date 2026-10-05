"""Internal intermediate types for candidate lookup.

Matchers emit ``Mention`` objects (one per detected phrase) holding ``Hit``s
whose ``value`` is already a contract ``CandidateValue``. ``lookup.assemble``
is the single place that turns mentions into the contract's
``CandidateLookupResult``.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from server.ask.models.candidates import CandidateField, CandidateSource


@dataclass(frozen=True)
class Hit:
    field: CandidateField
    key: str  # candidate ID suffix: "1627759", "2023-24", "finals.east"
    label: str
    source: CandidateSource
    score: float
    value: object  # a contract CandidateValue model
    alias: str | None = None


@dataclass
class Mention:
    field: CandidateField
    start: int
    end: int
    text: str
    hits: list[Hit] = field(default_factory=list)
    total: int = 0  # matches before the per-mention bound
    note: str | None = None  # why there are no hits, for diagnostics

    @property
    def truncated(self) -> bool:
        return self.total > len(self.hits)


@dataclass(frozen=True)
class LookupLimits:
    per_mention: int = 8
    """Largest candidate list kept for one phrase ("Jalen" has 18 catalog matches)."""
    fuzzy_full_cutoff: float = 0.88
    fuzzy_last_cutoff: float = 0.85
    partial_names_in_unknown_full_names: bool = False
    """``expand`` sets this: "Michael Scott" then also offers Michaels and Scotts."""


DEFAULT_LIMITS = LookupLimits()
EXPANDED_LIMITS = LookupLimits(
    fuzzy_full_cutoff=0.78, fuzzy_last_cutoff=0.75, partial_names_in_unknown_full_names=True,
)
