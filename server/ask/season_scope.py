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
    r"best|worst|highest|lowest|streak|rank|seed|seeds|seeded|career|all[ -]?time|"
    r"finals|round|series|clutch|quarter|half|overtime|starter|bench|back[ -]to[ -]back|"
    r"without|when|per\s*(?:48|40|minute)|last\s+\w+\s+games?|"
    r"in\s+(?:their\s+)?(?:wins|losses)|conference\s+record)\b"
)
_COMPARE = re.compile(r"\b(?:compare|compared|comparison|more\s+than|less\s+than|difference)\b")


def ambiguous_season_candidates(candidates, question):
    """A bare year offers two seasons; model confidence cannot resolve it."""
    text = fold(question)
    groups = {}
    for candidate in candidates.sets["season"].candidates:
        phrase = candidate.matched_text
        if candidate.source == "app_context" or candidate.value.from_year is None or not phrase:
            continue
        pattern = r"(?<![a-z0-9/-])" + re.escape(fold(phrase)) + r"(?![a-z0-9]|\s*[-/]\s*\d)"
        if re.search(pattern, text):
            groups.setdefault((candidate.span, phrase), []).append(candidate)
    return [candidate for group in groups.values() if len({c.value.season for c in group}) > 1 for candidate in group]


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
            # Continuations rewrite names and shift spans. Match actual text,
            # never apply offsets belonging to the original question.
            phrases = [candidate.value.season] if name == "season" else [candidate.matched_text]
            if name == "player":
                phrases.append(candidate.value.player.name)
            elif name == "team":
                phrases.append(candidate.value.team.name)
            for phrase in sorted((p for p in phrases if p), key=len, reverse=True):
                pattern = r"(?<![a-z0-9])" + re.escape(fold(phrase)) + r"(?![a-z0-9])"
                text = re.sub(pattern, lambda m: " " * len(m.group()), text)
    explicit_constraints = any(c.source != "app_context" for name in ("date", "round", "game_number", "location")
                               for c in candidates.sets[name].candidates)
    players = [c for c in candidates.sets["player"].candidates if c.source != "app_context"]
    player_mentions = {(c.span, c.matched_text) for c in players}
    player_split = bool(players) if intent.selected == ["team_records"] else len(player_mentions) > 1
    if explicit_constraints or player_split or _SPLIT.search(text) or _COMPARE.search(text):
        return NormalizationResult(status="unsupported", unsupported_reason="other")
    if ambiguous_season_candidates(candidates, question):
        return NormalizationResult(status="needs_clarification", clarify_field="season", clarify_reason="ambiguous")
    playoff_wording = re.search(r"\b(?:playoffs?|postseason)\b", text)
    if playoff_wording and (re.search(r"\bregular[ -]season\b", text)
                            or re.search(r"\b(?:including|combined|plus|with)\s+(?:the\s+)?(?:playoffs?|postseason)\b", text)
                            or re.search(r"\b(?:playoffs?|postseason)\s+(?:included|combined)\b", text)):
        return NormalizationResult(status="unsupported", unsupported_reason="other")
    if playoff_wording and result.status == "valid":
        if intent.selected == ["team_records"]:
            return NormalizationResult(status="unsupported", unsupported_reason="other")
        if result.request.season_type != "playoffs":
            return NormalizationResult(status="needs_clarification", clarify_field="season_type", clarify_reason="ambiguous")
    return result
