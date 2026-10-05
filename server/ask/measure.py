"""The measure (season totals or per game) comes from the question text, never a model.

Live testing showed Jev confidently choosing totals for "Who led the league in assists
in 2019-20?", which states no measure. Python therefore decides whether a measure was
stated, and the interpreter's `aggregation` read is replaced before normalization:

- stated per game ("per game", "a game", "ppg", "average"/"averaged") -> per_game
- "scoring title" -> per_game: the NBA decides it by points per game
- stated totals ("total", "totals", "in total", "how many") -> total
- both stated -> ambiguous (a clarification where the tool needs one measure)
- nothing stated -> absent; each tool then applies its documented rule
  (season leaders ask, player season stats show per game with a totals toggle,
  career stats default to totals per ADR 0013, except a player's full career line,
  which shows per game with a totals toggle per the ADR's 2026-10-01 amendment).

"How many" is a weak totals signal: "how many points did he average" is per game.
Clarification rewrites append "season totals" / "per game" / "career totals", so a
continuation states its measure and needs no model call.
"""
from __future__ import annotations

import re
from typing import Literal

from server.ask.candidates.text import fold
from server.ask.models.interpreter import FieldDecision, FieldInterpretation, InterpreterOutput

MEASURED_INTENTS = frozenset({"player_season_stats", "season_leaders", "career_stats"})
# Diagnostics name for a field Python read from the question text.
QUESTION_TIER = "question"

_PER_GAME = re.compile(
    r"\b(?:per[\s-]*game|(?<!\bin )(?:a|each|every)\s+(?:game|night|contest)|per\s+(?:night|contest)|"
    r"averag(?:e|es|ed|ing)|avg|ppg|rpg|apg|spg|bpg|mpg|topg|scoring\s+(?:title|crown)s?)\b"
)
_TOTAL = re.compile(r"\b(?:totals?|in\s+total|altogether|cumulative)\b")
_HOW_MANY = re.compile(r"\bhow\s+many\b")

StatedMeasure = Literal["total", "per_game", "both"]


def stated_measure(question: str) -> StatedMeasure | None:
    text = fold(question)
    per_game = bool(_PER_GAME.search(text))
    total = bool(_TOTAL.search(text))
    if per_game and total:
        return "both"
    if per_game:
        return "per_game"
    if total or _HOW_MANY.search(text):
        return "total"
    return None


def with_stated_measure(output: InterpreterOutput, question: str) -> InterpreterOutput:
    """Replace the interpreter's aggregation with the one the question states.

    Only for tools with a measure; other outputs are returned unchanged. Idempotent.
    """
    if output.outcome != "interpreted":
        return output
    intent = output.get_field("intent")
    if intent is None or intent.status != "selected" or intent.selected[0] not in MEASURED_INTENTS:
        return output
    stated = stated_measure(question)
    if stated in ("total", "per_game"):
        field = FieldInterpretation(field="aggregation", status="selected", selected=[stated])
    elif stated == "both" and intent.selected[0] != "player_season_stats":
        field = FieldInterpretation(field="aggregation", status="ambiguous", alternatives=["total", "per_game"])
    else:
        # Nothing stated (or both, for a player season, which shows both measures).
        field = FieldInterpretation(field="aggregation", status="absent")
    current = output.get_field("aggregation")
    if current == field and output.metadata.field_tiers.get("aggregation") == QUESTION_TIER:
        return output
    fields = [f for f in output.fields if f.field != "aggregation"] + [field]
    metadata = output.metadata
    decisions = []
    for decision in metadata.field_decisions:
        if decision.field == "aggregation":
            decision = decision.model_copy(update={"decided_by": QUESTION_TIER, "confidence": None, "outcome": "accepted"})
        decisions.append(decision)
    if not any(d.field == "aggregation" for d in decisions) and metadata.field_decisions:
        decisions.append(FieldDecision(field="aggregation", decided_by=QUESTION_TIER, outcome="accepted"))
    metadata = metadata.model_copy(update={
        "field_tiers": {**metadata.field_tiers, "aggregation": QUESTION_TIER},
        "field_decisions": decisions,
    })
    return output.model_copy(update={"fields": fields, "metadata": metadata})
