"""Candidate lookup: question text + app context -> bounded, typed candidates.

Order of work, each step masking the text it consumed:

1. game numbers, dates, seasons, playoff rounds (fixed patterns)
2. multi-word player names and aliases ("Jalen Brunson", "King James")
3. team names, historical names, cities, tricodes, aliases (dated records)
4. single-word player names/aliases, then capitalized names nothing matched

A phrase that looks like a player's full name but is not in the catalog
("Dwight Schrute") yields no candidates. Its parts are not offered as
partial matches, because a missing candidate is never evidence for a
different player. ``expand`` relaxes that for the cascade.
"""
from __future__ import annotations

import dataclasses
import datetime as dt
import re
import time
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from server.ask.candidates import dates, locations, patterns
from server.ask.candidates.aliases import alias_version
from server.ask.candidates.players import PlayerIndex, get_player_index, season_label
from server.ask.candidates.teams import TeamIndex, get_team_index, resolve_phrase
from server.ask.candidates.text import STOPWORDS, Token, fold, tokenize
from server.ask.candidates.types import DEFAULT_LIMITS, EXPANDED_LIMITS, Hit, LookupLimits, Mention
from server.ask.models.candidates import (
    CANDIDATE_FIELDS,
    MAX_CANDIDATES_PER_FIELD,
    MAX_TOTAL_CANDIDATES,
    Candidate,
    CandidateField,
    CandidateLookupResult,
    CandidateSet,
    PlayerCandidateValue,
)
from server.ask.models.common import MAX_QUESTION_LENGTH, PlayerRef
from server.ask.models.request import AskContext

NEW_YORK = ZoneInfo("America/New_York")
_JOINER = re.compile(r"^[\s.\-']{0,3}$")
_SENTENCE_BREAK = re.compile(r"[.?!:;]\s*$")


# --- player matching --------------------------------------------------------

_MATCH_RANK = {"full_name": 0, "alias": 0, "last_name": 1, "first_name": 2, "fuzzy": 3, "partial": 4}
_MATCH_SCORE = {"full_name": 1.0, "alias": 0.95, "last_name": 0.8, "first_name": 0.6, "partial": 0.3}


def _player_hits(index: PlayerIndex, matches: list[tuple[int, str, float | None, str | None]],
                 seasons: frozenset[int], limit: int) -> tuple[list[Hit], int]:
    """Rank (player_id, match kind, similarity, alias) tuples and apply the bound.

    Ranking only decides which candidates survive the bound: strongest match
    first, then players whose career covers a season the question names, then
    players who appeared in a game, then the most recent careers.
    """
    best: dict[int, tuple[int, str, float | None, str | None]] = {}
    for match in matches:
        seen = best.get(match[0])
        if seen is None or _MATCH_RANK[match[1]] < _MATCH_RANK[seen[1]]:
            best[match[0]] = match

    def era(player_id: int) -> bool:
        p = index.players[player_id]
        if not seasons or p.from_year is None:
            return False
        to_year = p.to_year if p.to_year is not None else p.from_year
        return any(p.from_year <= s <= to_year for s in seasons)

    ordered = sorted(best.values(), key=lambda m: (
        _MATCH_RANK[m[1]], not era(m[0]), not index.players[m[0]].played, -(index.players[m[0]].to_year or 0),
        index.players[m[0]].full_name,
    ))
    hits = []
    for player_id, kind, similarity, alias in ordered[:limit]:
        p = index.players[player_id]
        span = p.span_label()
        score = round(similarity * 0.8, 3) if kind == "fuzzy" and similarity else _MATCH_SCORE.get(kind, 0.3)
        hits.append(Hit(
            field="player", key=str(player_id),
            label=f"{p.full_name} ({span})" if span else p.full_name,
            source="alias" if kind == "alias" else "player_catalog",
            score=score, alias=alias,
            value=PlayerCandidateValue(
                player=PlayerRef(player_id=player_id, name=p.full_name),
                first_season=season_label(p.from_year) if p.from_year is not None else None,
                last_season=None if p.active or p.to_year is None else season_label(p.to_year),
            ),
        ))
    return hits, len(ordered)


@dataclass
class _Scan:
    question: str
    tokens: list[Token]
    consumed: list[bool]
    team_tokens: set[int] = dataclasses.field(default_factory=set)

    def contiguous(self, i: int, j: int) -> bool:
        """Tokens i..j (inclusive) are all free and joined only by spaces/hyphens/periods."""
        if any(self.consumed[k] for k in range(i, j + 1)):
            return False
        return all(_JOINER.match(self.question[self.tokens[k].end:self.tokens[k + 1].start]) for k in range(i, j))

    def text(self, i: int, j: int) -> tuple[int, int, str]:
        start, end = self.tokens[i].start, self.tokens[j].end
        return start, end, self.question[start:end]

    def key(self, i: int, j: int) -> str:
        return " ".join(t.norm for t in self.tokens[i:j + 1])

    def eligible(self, k: int) -> bool:
        """Can this token be a one-word name? Needs a capital if the user writes in mixed case."""
        token = self.tokens[k]
        return (
            not self.consumed[k] and token.norm not in STOPWORDS and not token.norm.isdigit()
            and (token.capitalized or not self.mixed_case())
        )

    def mixed_case(self) -> bool:
        """Does the user capitalize names? Sentence-initial capitals ("How"), acronyms
        ("NBA") and team names ("Celtics") say nothing about that; a capitalized
        player name ("Tatum") does."""
        return any(
            t.capitalized and i not in self.team_tokens and not self.sentence_initial(i) and not self.upper(i, i)
            for i, t in enumerate(self.tokens)
        )

    def sentence_initial(self, k: int) -> bool:
        return k == 0 or bool(_SENTENCE_BREAK.search(self.question[:self.tokens[k].start]))

    def upper(self, i: int, j: int) -> bool:
        raw = re.sub(r"['\u2019][sS]?$", "", self.question[self.tokens[i].start:self.tokens[j].end])
        return raw.upper() == raw and any(c.isalpha() for c in raw)


def _entity_mentions(question: str, masked: str, seasons: frozenset[int], limits: LookupLimits,
                     players: PlayerIndex, teams: TeamIndex) -> list[Mention]:
    tokens = tokenize(masked, question)
    scan = _Scan(question, tokens, [False] * len(tokens))
    out: list[Mention] = []
    n_tokens = len(tokens)

    def add(field: str, i: int, j: int, hits: list[Hit], total: int, note: str | None = None) -> None:
        start, end, text = scan.text(i, j)
        out.append(Mention(field=field, start=start, end=end, text=text, hits=hits, total=total, note=note))  # type: ignore[arg-type]
        for k in range(i, j + 1):
            scan.consumed[k] = True

    # 1. Multi-word player names and aliases, longest first.
    for size in range(players.max_phrase_tokens, 1, -1):
        for i in range(0, n_tokens - size + 1):
            j = i + size - 1
            if not scan.contiguous(i, j):
                continue
            key = scan.key(i, j)
            matches = [(pid, "full_name", None, None) for pid in players.full.get(key, ())]
            if key in players.aliases and (key not in players.caps_only_aliases or scan.upper(i, j)):
                alias = scan.text(i, j)[2]
                matches += [(pid, "alias", None, alias) for pid in players.aliases[key]]
            if matches:
                hits, total = _player_hits(players, matches, seasons, limits.per_mention)
                add("player", i, j, hits, total)

    # 2. Teams: full names, historical names, cities, nicknames, tricodes, aliases.
    for size in range(teams.max_phrase_tokens, 0, -1):
        for i in range(0, n_tokens - size + 1):
            j = i + size - 1
            if not scan.contiguous(i, j):
                continue
            key = scan.key(i, j)
            if key not in teams.phrases or (key in teams.caps_only and not scan.upper(i, j)):
                continue
            if size == 1 and key in STOPWORDS:
                continue
            hits, note = resolve_phrase(teams, key, seasons)
            add("team", i, j, hits[:limits.per_mention], len(hits), note)
            scan.team_tokens.update(range(i, j + 1))

    # 3. Runs of name-like words that are not a known full name ("Dwight Schrute").
    k = 0
    while k < n_tokens:
        if not scan.eligible(k):
            k += 1
            continue
        run_end = k
        while run_end + 1 < n_tokens and scan.eligible(run_end + 1) and scan.contiguous(k, run_end + 1):
            run_end += 1
        if 1 <= run_end - k <= 2 and _looks_like_full_name(players, scan, k):
            key = scan.key(k, run_end)
            matches = [(pid, "fuzzy", sim, None) for pid, sim in players.fuzzy(key, full=True, cutoff=limits.fuzzy_full_cutoff)]
            if limits.partial_names_in_unknown_full_names:
                for t in range(k, run_end + 1):
                    norm = scan.tokens[t].norm
                    matches += [(pid, "partial", None, None) for pid in (*players.first.get(norm, ()), *players.last.get(norm, ()))]
            hits, total = _player_hits(players, matches, seasons, limits.per_mention)
            add("player", k, run_end, hits, total, None if hits else "no player by that name in the catalog")
            k = run_end + 1
            continue
        k += 1

    # 4. Single words: aliases, one-word names, last names, first names.
    for k in range(n_tokens):
        if not scan.eligible(k):
            continue
        norm = scan.tokens[k].norm
        matches: list[tuple[int, str, float | None, str | None]] = []
        if norm in players.aliases and (norm not in players.caps_only_aliases or scan.upper(k, k)):
            matches += [(pid, "alias", None, scan.text(k, k)[2]) for pid in players.aliases[norm]]
        matches += [(pid, "full_name", None, None) for pid in players.full.get(norm, ())]
        matches += [(pid, "last_name", None, None) for pid in players.last.get(norm, ())]
        matches += [(pid, "first_name", None, None) for pid in players.first.get(norm, ())]
        # Fuzzy one-word matches need a capital, unless the whole question is lowercase:
        # in sentence case, common words ("time" ~ "Timme") would match surnames.
        if not matches and len(norm) >= 4 and (scan.tokens[k].capitalized or not any(c.isupper() for c in question)):
            matches = [(pid, "fuzzy", sim, None) for pid, sim in players.fuzzy(norm, full=False, cutoff=limits.fuzzy_last_cutoff)]
        if matches:
            hits, total = _player_hits(players, matches, seasons, limits.per_mention)
            add("player", k, k, hits, total)
        elif scan.tokens[k].capitalized and not scan.sentence_initial(k) and len(norm) >= 3:
            add("player", k, k, [], 0, "capitalized name matched no player or team")
    return out


def _looks_like_full_name(players: PlayerIndex, scan: _Scan, i: int) -> bool:
    """A run of name-like words starting with a word used mostly as a first name.

    "Michael Scott" is treated as one (unknown) full name rather than as a
    Michael plus a Scott. "Brunson Hart" (two surnames) is not.
    """
    first = scan.tokens[i].norm
    return len(players.first.get(first, ())) > len(players.last.get(first, ()))


# --- app context -----------------------------------------------------------

# Words that place a day on the user's screen: "the date I have open", "the day
# I'm looking at", "the date on my screen", "the displayed date".
_ON_SCREEN = (
    r"(?:(?:currently\s+)?(?:selected|shown|showing|displayed|open|in\s+view)"
    r"|on\s+(?:this|the|my)\s+(?:page|screen)|here"
    r"|i\s+(?:have|had|'ve\s+got)\s+(?:(?:open(?:ed)?|up|pulled\s+up|selected)\b|on\s+(?:the\s+|my\s+)?screen)"
    r"|i(?:'m|\s+am)\s+(?:on|viewing|looking\s+at|seeing))"
)
_THAT_DAY = re.compile(
    r"\b(?:that|this|the\s+same)\s+(?:day|date|night)\b|\bon\s+this\s+date\b"
    rf"|\b(?:the\s+)?(?:day|date)\s+(?:(?:that|which)(?:\s+is|'s)?\s+)?{_ON_SCREEN}(?:\s+(?:on\s+(?:this|the|my)\s+(?:page|screen)|here))?"
    r"(?![a-z])"
    r"|\b(?:the\s+)?(?:selected|shown|displayed|open|on-?screen)\s+(?:day|date)\b"
)
_ON_SCREEN_SEASON = re.compile(r"\b(?:this|that|these|those)\s+(?:series|bracket|playoffs?|postseason)\b")


def _context_mentions(folded: str, masked: str, question: str, context: AskContext, playoff_context: bool,
                      mentions: list[Mention]) -> tuple[list[Mention], str]:
    """Candidates from the page the user is on, only when the question points at it."""
    out = []
    for m in _THAT_DAY.finditer(masked):
        hits = []
        if context.view_date is not None:
            d = context.view_date
            hit = dates.calendar_hit(d.year, d.month, d.day, "date on screen", score=0.9, source="app_context")
            if hit:
                hits.append(hit)
        out.append(Mention(field="date", start=m.start(), end=m.end(), text=question[m.start():m.end()],
                           hits=hits, total=len(hits), note=None if hits else "no date in the app context"))
        masked = patterns._mask(masked, m.start(), m.end())
    if context.playoff_season:
        pointer = _ON_SCREEN_SEASON.search(folded)
        has_season = any(mm.field == "season" for mm in mentions)
        on_playoff_page = playoff_context and context.route in ("playoffs", "series") and not has_season
        if (pointer and not has_season) or on_playoff_page:
            season = context.playoff_season
            hit = patterns._season_hit(int(season[:4]), f"{season} (season on screen)", score=0.8, source="app_context")
            start, end = (pointer.start(), pointer.end()) if pointer else (0, 0)
            out.append(Mention(field="season", start=start, end=end, text=question[start:end], hits=[hit], total=1))
    return out, masked


# --- assembly --------------------------------------------------------------

def assemble(mentions: list[Mention], version: str, latency_ms: int) -> CandidateLookupResult:
    """The one place internal mentions become the contract's CandidateLookupResult."""
    per_field: dict[str, list[tuple[Hit, Mention]]] = {f: [] for f in CANDIDATE_FIELDS}
    truncated: dict[str, bool] = {f: False for f in CANDIDATE_FIELDS}
    unmatched: dict[str, list[str]] = {f: [] for f in CANDIDATE_FIELDS}
    mentioned: set[str] = set()
    for m in sorted(mentions, key=lambda m: m.start):
        mentioned.add(m.field)
        truncated[m.field] |= m.truncated
        if not m.hits and m.text and m.text not in unmatched[m.field]:
            unmatched[m.field].append(m.text)
        for hit in m.hits:
            per_field[m.field].append((hit, m))

    chosen: dict[str, list[Candidate]] = {}
    for field in CANDIDATE_FIELDS:
        candidates: list[Candidate] = []
        seen_ids: set[str] = set()
        seen_values: list[object] = []
        for hit, m in per_field[field]:
            if field == "date":
                if hit.value in seen_values:
                    continue
                seen_values.append(hit.value)
                cid = f"date:{len(candidates)}"
            else:
                cid = f"{field}:{hit.key}"
            if cid in seen_ids:
                continue
            seen_ids.add(cid)
            candidates.append(Candidate(
                id=cid, field=field, label=hit.label[:120], matched_text=m.text[:120] or None,
                span=(m.start, m.end) if m.end > m.start else None, source=hit.source,
                alias=hit.alias[:80] if hit.alias else None, match_score=max(0.0, min(1.0, hit.score)),
                value=hit.value,
            ))
        if len(candidates) > MAX_CANDIDATES_PER_FIELD:
            candidates = candidates[:MAX_CANDIDATES_PER_FIELD]
            truncated[field] = True
        chosen[field] = candidates

    while sum(len(c) for c in chosen.values()) > MAX_TOTAL_CANDIDATES:
        largest = max(CANDIDATE_FIELDS, key=lambda f: len(chosen[f]))
        chosen[largest] = chosen[largest][:-1]
        truncated[largest] = True

    sets = {}
    for field in CANDIDATE_FIELDS:
        status = "candidates" if chosen[field] else ("no_candidates" if field in mentioned else "not_mentioned")
        sets[field] = CandidateSet(
            field=field, status=status, candidates=chosen[field], truncated=truncated[field],
            unmatched_text=[t[:120] for t in unmatched[field][:4]] if status != "not_mentioned" else [],
        )
    return CandidateLookupResult(sets=sets, alias_version=version, latency_ms=latency_ms)


def reference_date(context: AskContext) -> dt.date:
    return context.reference_time.astimezone(NEW_YORK).date()


def find_mentions(question: str, context: AskContext, limits: LookupLimits = DEFAULT_LIMITS,
                  players: PlayerIndex | None = None, teams: TeamIndex | None = None) -> list[Mention]:
    players = players or get_player_index()
    teams = teams or get_team_index()
    question = question[:MAX_QUESTION_LENGTH]
    today = reference_date(context)
    folded = fold(question)
    playoff_context = bool(patterns.PLAYOFF_CONTEXT.search(folded))

    mentions, masked = patterns.game_number_mentions(folded, question, playoff_context)
    date_mentions, masked = dates.mentions(masked, question, today)
    page_season = context.playoff_season if context.route in ("playoffs", "series") else None
    season_mentions, masked = patterns.season_mentions(masked, question, today, playoff_context, page_season)
    round_mentions, masked = patterns.round_mentions(masked, question)
    location_mentions, masked = locations.mentions(masked, question)
    mentions += date_mentions + season_mentions + round_mentions + location_mentions
    context_mentions, masked = _context_mentions(folded, masked, question, context, playoff_context, mentions)
    mentions += context_mentions
    seasons = patterns.season_start_years(mentions)
    mentions += _entity_mentions(question, masked, seasons, limits, players, teams)
    return mentions


class CandidateLookupService:
    """Implements ``server.ask.protocols.CandidateLookup``."""

    def __init__(self, limits: LookupLimits = DEFAULT_LIMITS) -> None:
        self.limits = limits
        self.alias_version = alias_version()

    def lookup(self, question: str, context: AskContext) -> CandidateLookupResult:
        started = time.perf_counter()
        mentions = find_mentions(question, context, self.limits)
        latency_ms = int((time.perf_counter() - started) * 1000)
        return assemble(mentions, self.alias_version, latency_ms)

    def expand(self, question: str, context: AskContext, field: CandidateField, previous: CandidateSet) -> CandidateSet:
        """Looser matching for one field, within the same per-field limit.

        Previous candidates stay first; new ones are appended. Date candidates
        have nothing looser to offer, so ``previous`` comes back unchanged.
        """
        if field == "date":
            return previous
        wider = assemble(find_mentions(question, context, EXPANDED_LIMITS), self.alias_version, 0).sets[field]
        known = {c.id for c in previous.candidates}
        extra = [c for c in wider.candidates if c.id not in known]
        if not extra:
            return previous
        merged = [*previous.candidates, *extra]
        return CandidateSet(
            field=field, status="candidates", candidates=merged[:MAX_CANDIDATES_PER_FIELD],
            truncated=previous.truncated or wider.truncated or len(merged) > MAX_CANDIDATES_PER_FIELD,
            unmatched_text=previous.unmatched_text,
        )
