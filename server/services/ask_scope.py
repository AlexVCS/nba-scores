"""Deterministic guards for requests outside the Ask v1 query scope."""

from __future__ import annotations

import re
import unicodedata


_REGULAR_SEASON = re.compile(r"\bregular(?:\s+|-\s*)season\b")
_RECORD_TOTAL = re.compile(
    r"(?:"
    r"\bhow\s+many\s+(?:wins?|losses?)\b(?=.{0,100}\b(?:did|does|do|has|have|had)\b)"
    r"|\b(?:win|wins|loss|losses)\s*[-/]?\s*(?:loss\s*[-/]?\s*)?record\b"
    r"|\b(?:win|wins|loss|losses)\s+(?:total|totals)\b"
    r"|\b(?:standings|most\s+wins?|most\s+games)\b"
    r")"
)
_SEASON_WIDE_RESULT = re.compile(
    r"\b(?:largest|biggest|most\s+lopsided|highest\s+margin)\b"
    r"(?:\s+regular(?:\s+|-\s*)season)?\s+(?:win|wins|loss|losses)\b"
)

_RECORD_MESSAGE = (
    "Regular-season win totals and standings are not supported yet. You can "
    "search games by date or ask about a playoff series."
)
_RESULT_MESSAGE = (
    "Search cannot find a team’s biggest win or loss across a full regular "
    "season yet. For player statistics, ask about a specific game and include "
    "its date."
)


def _normalize(question: str) -> str:
    """Normalize punctuation users commonly use in season questions."""
    normalized = unicodedata.normalize("NFKC", question).casefold()
    normalized = normalized.replace("\u2018", "'").replace("\u2019", "'")
    normalized = re.sub(r"[\u2010-\u2015\u2212\ufe58\ufe63\uff0d]", "-", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def unsupported_scope_message(question: str) -> str | None:
    """Return a user-facing scope explanation for two unimplemented query shapes.

    The guard deliberately requires an explicit ``regular season`` selector so
    ordinary dated game searches and playoff questions continue to the parser.
    """
    if not isinstance(question, str):
        return None
    normalized = _normalize(question)
    if not _REGULAR_SEASON.search(normalized):
        return None
    if _SEASON_WIDE_RESULT.search(normalized):
        return _RESULT_MESSAGE
    if _RECORD_TOTAL.search(normalized):
        return _RECORD_MESSAGE
    return None
