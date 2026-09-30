"""Deterministic guard against dropping unsupported season-query constraints.

Both HTTP and evaluation use this after interpretation, including clarification
continuations. Closed tools answer full seasons, not unrepresented splits.
"""
import re

from server.ask.candidates.text import fold
from server.ask.models.interpreter import NormalizationResult

_SPLIT = re.compile(
    r"\b(?:home|away|road|division|divisional|against|versus|vs|before|after|since|until|through|between|"
    r"january|february|march|april|may|june|july|august|september|october|november|december|"
    r"jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec|last\s+\d+\s+games?|"
    r"preseason|play[ -]?in|all[ -]?star|per\s*36|per\s*100|per\s*possessions?|"
    r"true\s+shooting|effective\s+field|usage|efficiency|advanced|pace|fantasy|"
    r"best|worst|highest|lowest|streak|rank|seed|seeds|seeded|career|all[ -]?time)\b"
)
_COMPARE = re.compile(r"\b(?:compare|compared|comparison|more\s+than|less\s+than|difference)\b")


def normalize_question(normalizer, output, candidates, context, question):
    result = normalizer.normalize(output, candidates, context)
    intent = output.get_field("intent")
    if intent is None or intent.status != "selected" or intent.selected[0] not in {"player_season_stats", "team_records"}:
        return result
    text = fold(question)
    # Mask known names and seasons so names such as Kevin May/De'Andre Hunter,
    # or Boston's historical Division name, are never mistaken for split language.
    for name in ("player", "team", "season"):
        for candidate in candidates.sets[name].candidates:
            if candidate.span is not None:
                start, end = candidate.span
                text = text[:start] + " " * (end - start) + text[end:]
    explicit_dates = any(c.source != "app_context" for c in candidates.sets["date"].candidates)
    if explicit_dates or _SPLIT.search(text) or _COMPARE.search(text):
        return NormalizationResult(status="unsupported", unsupported_reason="other")
    return result
