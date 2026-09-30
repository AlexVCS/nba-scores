"""Deterministic guard against dropping unsupported season-query constraints.

Both HTTP and evaluation use this after interpretation, including clarification
continuations. Closed tools answer full seasons, not unrepresented splits.
"""
import re

from server.ask.candidates.text import fold
from server.ask.models.common import MAX_LEADER_LIMIT
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
    if intent is None or intent.status != "selected" or intent.selected[0] not in {"player_season_stats", "team_records", "season_leaders"}:
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
    if intent.selected == ["season_leaders"]:
        return _leaders(result, candidates, question, text, explicit_constraints)
    players = [c for c in candidates.sets["player"].candidates if c.source != "app_context"]
    player_mentions = {(c.span, c.matched_text) for c in players}
    player_split = bool(players) if intent.selected == ["team_records"] else len(player_mentions) > 1
    if explicit_constraints or player_split or _SPLIT.search(text) or _COMPARE.search(text):
        return NormalizationResult(status="unsupported", unsupported_reason="other")
    if ambiguous_season_candidates(candidates, question):
        return NormalizationResult(status="needs_clarification", clarify_field="season", clarify_reason="ambiguous")
    playoff_wording = re.search(r"\b(?:playoffs?|postseason)\b", text)
    if _combined_phases(text):
        return NormalizationResult(status="unsupported", unsupported_reason="other")
    if playoff_wording and result.status == "valid":
        if intent.selected == ["team_records"]:
            return NormalizationResult(status="unsupported", unsupported_reason="other")
        if result.request.season_type != "playoffs":
            return NormalizationResult(status="needs_clarification", clarify_field="season_type", clarify_reason="ambiguous")
    return result


def _combined_phases(text):
    """Regular season plus playoffs in one number is never answered."""
    return bool(re.search(r"\b(?:playoffs?|postseason)\b", text)) and bool(
        re.search(r"\bregular[ -]season\b", text)
        or re.search(r"\b(?:season|regular)\s+(?:and|&|\+)\s+(?:the\s+)?(?:playoffs?|postseason)\b", text)
        or re.search(r"\b(?:including|combined|plus|with)\s+(?:the\s+)?(?:playoffs?|postseason)\b", text)
        or re.search(r"\b(?:playoffs?|postseason)\s+(?:included|combined)\b", text))


# Season leaders (docs/ask-stage3.md). "best", "highest", "most", "top" and "lead" are
# the question itself here, so the Stage 2 split list is replaced, not reused.
_LEADER_SPLIT = re.compile(
    r"\b(?:home|away|road|division|divisional|against|versus|vs|before|after|since|until|through|between|"
    r"january|february|march|april|may|june|july|august|september|october|november|december|"
    r"jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec|last\s+\w+\s+games?|"
    r"preseason|play[ -]?in|all[ -]?star|cup|tournament|summer\s+league|per\s*36|per\s*100|per\s*possessions?|"
    r"per\s*(?:48|40|minute)|true\s+shooting|effective\s+field|usage|efficiency|advanced|pace|fantasy|"
    r"win\s+shares?|per(?!\s*game)|vorp|plus[ -]?minus|\+/-|fouls?|double[ -]doubles?|triple[ -]doubles?|"
    r"lowest|fewest|least|worst|bottom|streak|seed|seeds|seeded|career|all[ -]?time|ever|history|historic(?:al)?|"
    r"records?|finals|round|series|clutch|quarter|half|overtime|starters?|bench|back[ -]to[ -]back|"
    r"without|when|in\s+(?:their\s+|his\s+)?(?:wins|losses)|conference|eastern|western|east|west|"
    r"rookies?|sophomores?|guards?|forwards?|centers?|position|teams?|franchises?|"
    r"in\s+(?:a|one|any|single)\s+game|single[ -]game|game[ -]high|season[ -]high|games?\s+with|"
    r"at\s+least|or\s+more|more\s+than|less\s+than|fewer\s+than|compare|compared|comparison|difference)\b"
)
# Stat families, most specific first; each match is blanked before the next family.
_STAT_FAMILIES = (
    r"\b(?:3|three)[ -]?(?:point(?:ers?)?|pt|pointers?)s?(?:\s+field[ -]goals?)?(?:\s+(?:percentage|pct))?|\bthrees\b|\b3s\b|\b3p%?|\bfg3m?\b",
    r"\bfree[ -]throws?(?:\s+(?:percentage|pct))?|\bft%?",
    r"\bfield[ -]goals?(?:\s+(?:percentage|pct))?|\bfg%?|\bshooting\s+percentage",
    r"\bpoints?\b|\bscor(?:ing|er|ers|ed)\b|\bppg\b|\bpts\b",
    r"\b(?:offensive\s+|defensive\s+)?rebound(?:s|ing|er|ers)?\b|\bboards\b|\brpg\b",
    r"\bassists?\b|\bapg\b|\bdimes\b",
    r"\bsteals?\b|\bspg\b",
    r"\bblock(?:s|ed|er|ers)?\b|\bbpg\b",
    r"\bturnovers?\b",
    r"\bminutes\b|\bmpg\b",
)
_NUMBER_WORDS = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen "
    "sixteen seventeen eighteen nineteen twenty".split())}
_TOP = re.compile(r"\btop[\s-]+(\d{1,3}|twenty[\s-]+(?:one|two|three|four|five)|" + "|".join(_NUMBER_WORDS) + r")\b")


def _top_n(text):
    """The requested top N (None when absent), or 0 when out of range."""
    match = _TOP.search(text)
    if match is None:
        return None
    word = re.sub(r"[\s-]+", " ", match.group(1))
    if word.isdigit():
        n = int(word)
    elif word.startswith("twenty "):
        n = 20 + _NUMBER_WORDS[word.split()[1]]
    else:
        n = _NUMBER_WORDS[word]
    return n if 1 <= n <= MAX_LEADER_LIMIT else 0


def _leaders(result, candidates, question, text, explicit_constraints):
    # Bare years ("2024") are masked too; any other number is a threshold or a count.
    for candidate in candidates.sets["season"].candidates:
        if candidate.matched_text:
            pattern = r"(?<![a-z0-9])" + re.escape(fold(candidate.matched_text)) + r"(?![a-z0-9])"
            text = re.sub(pattern, lambda m: " " * len(m.group()), text)
    named = any(c.source != "app_context" for name in ("player", "team") for c in candidates.sets[name].candidates)
    seasons = {(c.span, c.matched_text) for c in candidates.sets["season"].candidates if c.source != "app_context"}
    families, remaining = 0, text
    for pattern in _STAT_FAMILIES:
        remaining, hits = re.subn(pattern, lambda m: " " * len(m.group()), remaining)
        families += bool(hits)
    top = _top_n(remaining)  # after blanking stats, so "top 3-point shooters" is not N=3
    numbers = re.sub(_TOP, " ", remaining)
    if (explicit_constraints or named or len(seasons) > 1 or families > 1 or top == 0
            or re.search(r"\d", numbers) or _LEADER_SPLIT.search(text) or _combined_phases(text)):
        return NormalizationResult(status="unsupported", unsupported_reason="other")
    if ambiguous_season_candidates(candidates, question):
        return NormalizationResult(status="needs_clarification", clarify_field="season", clarify_reason="ambiguous")
    if result.status != "valid":
        return result
    if re.search(r"\b(?:playoffs?|postseason)\b", text) and result.request.season_type != "playoffs":
        return NormalizationResult(status="needs_clarification", clarify_field="season_type", clarify_reason="ambiguous")
    if top:
        request = result.request.model_validate({**result.request.model_dump(), "limit": top})
        return NormalizationResult(status="valid", request=request)
    return result
