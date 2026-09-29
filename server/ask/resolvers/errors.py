"""Explicit outcomes for resolvers that cannot return a result.

Resolvers return a result or raise one of these; each maps onto one
``AskResponse`` outcome:

* ``NotFoundError`` -> ``not_found``: the arguments were valid and the source
  answered, but no matching record exists (no games, a historical gap, a
  series game that was never played). ``code`` is the notice code.
* ``UnavailableError`` -> ``unavailable`` / ``service_unavailable``: an
  upstream source failed or answered unusably. Retrying can succeed.
* ``AmbiguousError`` -> ``needs_clarification`` with reason ``ambiguous``:
  several records match and the resolver will not choose. ``options`` holds
  the verified candidates for the pipeline to turn into clarification options.
* ``ClarificationError`` -> ``needs_clarification`` for a missing or
  out-of-range detail (``missing``, ``range_too_long``).
* ``UnsupportedError`` -> ``unsupported`` with an ``UnsupportedReason``.

``reason`` is a machine code for logs and templates; ``message`` is developer
text, not user copy. ``spoiler`` marks ambiguity whose candidates would reveal
a result (which teams reached a round), so any options built from them must be
flagged as spoilers. Outcomes themselves are never protected: asking is
consent (ADR 0006).
"""

from __future__ import annotations

from typing import Any, Literal, Mapping, Sequence

from server.ask.models.interpreter import UnsupportedReason
from server.ask.models.response import ClarifyField, ClarifyReason
from server.services import nba_stats_client

NotFoundCode = Literal["no_games", "no_record", "player_did_not_play"]


class ResolverError(Exception):
    def __init__(self, reason: str, message: str = "", *, spoiler: bool = False, details: Mapping[str, Any] | None = None):
        super().__init__(message or reason)
        self.reason = reason
        self.message = message or reason
        self.spoiler = spoiler
        self.details = dict(details or {})


class NotFoundError(ResolverError):
    def __init__(self, code: NotFoundCode, reason: str, message: str = "", **kwargs):
        super().__init__(reason, message, **kwargs)
        self.code = code


class UnavailableError(ResolverError):
    retryable = True

    @classmethod
    def from_upstream(cls, error: Exception) -> UnavailableError:
        if isinstance(error, nba_stats_client.UpstreamError):
            reason = "upstream_unavailable" if isinstance(error, nba_stats_client.UpstreamUnavailableError) else "upstream_bad_response"
            return cls(reason, str(error), details=error.public_detail())
        return cls("upstream_unavailable", f"{type(error).__name__}: {error}")


class AmbiguousError(ResolverError):
    def __init__(self, field: ClarifyField, reason: str, message: str = "", *, options: Sequence[Mapping[str, Any]] = (), **kwargs):
        super().__init__(reason, message, **kwargs)
        self.field = field
        self.clarify_reason: ClarifyReason = "ambiguous"
        self.options = [dict(option) for option in options]


class ClarificationError(ResolverError):
    def __init__(self, field: ClarifyField, clarify_reason: ClarifyReason, reason: str, message: str = "", **kwargs):
        super().__init__(reason, message, **kwargs)
        self.field = field
        self.clarify_reason = clarify_reason


class UnsupportedError(ResolverError):
    def __init__(self, unsupported_reason: UnsupportedReason, reason: str, message: str = "", **kwargs):
        super().__init__(reason, message, **kwargs)
        self.unsupported_reason = unsupported_reason
