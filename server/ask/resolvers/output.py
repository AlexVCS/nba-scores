"""What a resolver returns: a contract result payload plus links and sources."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

from server.ask.models.response import SourceMetadata, VerifiedLink

R = TypeVar("R")

SOURCE_LABEL = "NBA.com"


@dataclass(frozen=True)
class ResolverOutput(Generic[R]):
    """``result`` is a contract result model (``GamesResult``, ``BoxscoreStatResult``,
    ``PlayoffSeriesResult`` or ``PostseasonSummaryResult``). ``links`` are
    response-level links, most useful first. ``sources[].complete`` is the
    completion state for cache lifetimes: False while any game or series in
    the answer can still change."""

    result: R
    links: tuple[VerifiedLink, ...]
    sources: tuple[SourceMetadata, ...]


def stats_source(complete: bool) -> SourceMetadata:
    # Every resolver reads stats.nba.com endpoints through the cached services.
    # fetched_at is left unset: cached entries do not record their fetch time.
    return SourceMetadata(name="nba_stats", label=SOURCE_LABEL, fetched_at=None, complete=complete)
