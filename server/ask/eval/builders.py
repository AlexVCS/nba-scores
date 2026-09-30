"""Small constructors for contract candidate objects.

Used by unit tests, the live access probe, and hand-built smoke fixtures. Hand-built
candidates are never valid for the #199 comparison, which must use #200's lookup.
"""

from __future__ import annotations

import datetime as dt
from typing import Iterable

from server.ask.models.candidates import (
    CANDIDATE_FIELDS,
    Candidate,
    CandidateLookupResult,
    CandidateSet,
    DateCandidateValue,
    GameNumberCandidateValue,
    PlayerCandidateValue,
    RoundCandidateValue,
    SeasonCandidateValue,
    TeamCandidateValue,
)
from server.ask.models.common import DateComponents, DateRange, PlayerRef, TeamRef

HAND_BUILT_ALIAS_VERSION = "hand-built"


def player(player_id: int, name: str, *, matched: str | None = None, first: str | None = None,
           last: str | None = None, score: float = 0.9) -> Candidate:
    return Candidate(
        id=f"player:{player_id}", field="player", label=name, matched_text=matched,
        source="player_catalog", match_score=score,
        value=PlayerCandidateValue(player=PlayerRef(player_id=player_id, name=name),
                                   first_season=first, last_season=last),
    )


def team(team_id: int, tricode: str, name: str, *, matched: str | None = None,
         source: str = "team_catalog", score: float = 0.9) -> Candidate:
    return Candidate(
        id=f"team:{team_id}", field="team", label=name, matched_text=matched, source=source,
        match_score=score, value=TeamCandidateValue(team=TeamRef(team_id=team_id, tricode=tricode, name=name)),
    )


def date(index: int, label: str, components: DateComponents, *, start: dt.date | None = None,
         end: dt.date | None = None, unresolved: str | None = None, matched: str | None = None) -> Candidate:
    resolved = DateRange(start=start, end=end or start) if start else None
    return Candidate(
        id=f"date:{index}", field="date", label=label, matched_text=matched, source="date_parser",
        match_score=1.0,
        value=DateCandidateValue(components=components, resolved=resolved, unresolved_reason=unresolved),
    )


def season(season_label: str, *, from_year: int | None = None, matched: str | None = None) -> Candidate:
    return Candidate(
        id=f"season:{season_label}", field="season",
        label=f"{season_label} season" + (f" ({from_year} playoffs)" if from_year else ""),
        matched_text=matched, source="pattern", match_score=1.0,
        value=SeasonCandidateValue(season=season_label, from_year=from_year),
    )


def playoff_round(round_name: str, *, conference: str | None = None, matched: str | None = None) -> Candidate:
    suffix = f".{conference}" if conference else ""
    label = round_name.replace("_", " ").title() + (f" ({conference.title()})" if conference else "")
    return Candidate(
        id=f"round:{round_name}{suffix}", field="round", label=label, matched_text=matched,
        source="pattern", match_score=1.0, value=RoundCandidateValue(round=round_name, conference=conference),
    )


def game_number(number: int, *, matched: str | None = None) -> Candidate:
    return Candidate(
        id=f"game_number:{number}", field="game_number", label=f"Game {number}", matched_text=matched,
        source="pattern", match_score=1.0, value=GameNumberCandidateValue(game_number=number),
    )


def lookup_result(candidates: Iterable[Candidate], *, unmatched: dict[str, list[str]] | None = None,
                  truncated: Iterable[str] = ()) -> CandidateLookupResult:
    """Group candidates into a complete CandidateLookupResult.

    Fields listed in `unmatched` without candidates become `no_candidates`; others with
    no candidates become `not_mentioned`.
    """
    unmatched = unmatched or {}
    truncated = set(truncated)
    grouped: dict[str, list[Candidate]] = {f: [] for f in CANDIDATE_FIELDS}
    for c in candidates:
        grouped[c.field].append(c)
    sets = {}
    for field, items in grouped.items():
        if items:
            status = "candidates"
        elif field in unmatched:
            status = "no_candidates"
        else:
            status = "not_mentioned"
        sets[field] = CandidateSet(
            field=field, status=status, candidates=items, truncated=field in truncated,
            unmatched_text=unmatched.get(field, []),
        )
    return CandidateLookupResult(sets=sets, alias_version=HAND_BUILT_ALIAS_VERSION, latency_ms=0)
