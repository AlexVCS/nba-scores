"""Seasons, playoff rounds and game numbers from fixed language patterns."""
from __future__ import annotations

import datetime as dt
import re

from server.ask.candidates.types import Hit, Mention
from server.ask.models.candidates import DateCandidateValue, GameNumberCandidateValue, RoundCandidateValue, SeasonCandidateValue
from server.utils.season import get_nba_season

FIRST_SEASON = 1946  # 1946-47, the first BAA season

PLAYOFF_CONTEXT = re.compile(
    r"\b(finals|final(?!\s+(?:score|minute|seconds?|quarter|play|shot))|playoffs?|postseason|champions?"
    r"|championship|champs|title|series|round|semi-?finals?|semis|ecf|wcf|seed|seeds"
    r"|game\s*(?:#\s*)?(?:\d|one|two|three|four|five|six|seven))\b"
)
GAME_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7}


def season_label(start_year: int) -> str:
    return f"{start_year}-{(start_year + 1) % 100:02d}"


def _mask(text: str, start: int, end: int) -> str:
    return text[:start] + " " * (end - start) + text[end:]


def _mention(field: str, m: re.Match | tuple[int, int], original: str, hits: list[Hit], note: str | None = None) -> Mention:
    start, end = (m.start(), m.end()) if isinstance(m, re.Match) else m
    raw = original[start:end]
    lead = len(raw) - len(raw.lstrip())
    text = raw.strip()
    return Mention(field=field, start=start + lead, end=start + lead + len(text), text=text,  # type: ignore[arg-type]
                   hits=hits, total=len(hits), note=note)


# --- game numbers -----------------------------------------------------------

_GAME_NUMBER = re.compile(r"\bgame\s*(?:#\s*|no\.?\s*|number\s+)?(\d{1,2}|one|two|three|four|five|six|seven)\b(?!\s*(?:pm|am|p\.m|a\.m|:|/\d))")
_G_NUMBER = re.compile(r"\bg([1-9])\b")


def game_number_mentions(folded: str, original: str) -> tuple[list[Mention], str]:
    out = []
    for pattern in (_GAME_NUMBER, _G_NUMBER):
        for m in pattern.finditer(folded):
            raw = m.group(1)
            number = int(raw) if raw.isdigit() else GAME_WORDS[raw]
            if 1 <= number <= 7:
                hits = [Hit(field="game_number", key=str(number), label=f"Game {number}", source="pattern",
                            score=1.0, value=GameNumberCandidateValue(game_number=number))]
                out.append(_mention("game_number", m, original, hits))
            else:
                out.append(_mention("game_number", m, original, [], note="playoff games are numbered 1-7"))
            folded = _mask(folded, m.start(), m.end())
    return out, folded


# --- seasons ----------------------------------------------------------------

def _season_hit(start_year: int, label: str, *, score: float, from_year: int | None = None,
                source: str = "pattern") -> Hit:
    season = season_label(start_year)
    return Hit(field="season", key=season, label=label[:120], source=source, score=score,  # type: ignore[arg-type]
               value=SeasonCandidateValue(season=season, from_year=from_year))


def year_hits(year: int, playoff_context: bool, latest_start: int) -> list[Hit]:
    """A bare year. With playoff language it is the playoff year ("2024 Finals" -> 2023-24);
    otherwise both seasons that touch the year are candidates."""
    if playoff_context:
        start = year - 1
        if FIRST_SEASON <= start <= latest_start:
            return [_season_hit(start, f"{season_label(start)} ({year} playoffs)", score=1.0, from_year=year)]
        return []
    hits = []
    for start, label, score in (
        (year - 1, f"{season_label(year - 1)} (season ending in {year})", 0.6),
        (year, f"{season_label(year)} (season starting in {year})", 0.5),
    ):
        if FIRST_SEASON <= start <= latest_start:
            hits.append(_season_hit(start, label, score=score, from_year=year))
    return hits


_EXPLICIT_SEASON = re.compile(r"\b((?:19|20)\d{2})\s*[-/]\s*((?:19|20)?\d{2})\b(?![-/]\d)")
_RELATIVE_SEASON = re.compile(r"\b(this|current|last|previous|next)\s+(season|year)(?:'s)?\b")
_THESE_PLAYOFFS = re.compile(r"\b(?:these|this\s+year'?s|this)\s+(?:playoffs|postseason)\b")
_APOSTROPHE_YEAR = re.compile(r"(?<![a-z0-9])'(\d{2})\b")
_BARE_YEAR = re.compile(r"\b(19[4-9]\d|20\d{2})\b")


def season_mentions(folded: str, original: str, today: dt.date, playoff_context: bool,
                    page_season: str | None = None) -> tuple[list[Mention], str]:
    current_start = int(get_nba_season(today.year, today.month)[:4])
    offseason = today.month in (7, 8, 9)
    latest_start = current_start + 1
    out: list[Mention] = []

    for m in _EXPLICIT_SEASON.finditer(folded):
        start, end_text = int(m.group(1)), m.group(2)
        end = int(end_text) if len(end_text) == 4 else (start // 100) * 100 + int(end_text)
        if len(end_text) == 2 and end < start:
            end += 100
        if end == start + 1 and FIRST_SEASON <= start <= latest_start + 5:
            out.append(_mention("season", m, original, [_season_hit(start, season_label(start), score=1.0)]))
        else:
            out.append(_mention("season", m, original, [], note="not a valid NBA season"))
        folded = _mask(folded, m.start(), m.end())

    for m in _THESE_PLAYOFFS.finditer(folded):
        if page_season is None:
            hit = _season_hit(current_start, f"{season_label(current_start)} ({current_start + 1} playoffs)",
                              score=0.9, from_year=current_start + 1)
            out.append(_mention("season", m, original, [hit]))
        folded = _mask(folded, m.start(), m.end())

    for m in _RELATIVE_SEASON.finditer(folded):
        which, unit = m.group(1), m.group(2)
        text = m.group(0).strip()
        if unit == "year":
            year = today.year - (1 if which in ("last", "previous") else 0) + (1 if which == "next" else 0)
            hits = year_hits(year, playoff_context, latest_start)
        elif which in ("this", "current"):
            hits = [_season_hit(current_start, f"{season_label(current_start)} ({text})", score=0.9)]
            if offseason:  # between the Finals and opening night either season can be meant
                hits[0] = _season_hit(current_start, f"{season_label(current_start)} (just finished)", score=0.6)
                hits.append(_season_hit(current_start + 1, f"{season_label(current_start + 1)} (upcoming)", score=0.5))
        elif which in ("last", "previous"):
            if offseason:
                hits = [_season_hit(current_start, f"{season_label(current_start)} (most recent)", score=0.6),
                        _season_hit(current_start - 1, f"{season_label(current_start - 1)} (season before)", score=0.5)]
            else:
                hits = [_season_hit(current_start - 1, f"{season_label(current_start - 1)} ({text})", score=0.9)]
        else:
            hits = [_season_hit(current_start + 1, f"{season_label(current_start + 1)} ({text})", score=0.9)]
        out.append(_mention("season", m, original, hits))
        folded = _mask(folded, m.start(), m.end())

    for pattern, expand in ((_APOSTROPHE_YEAR, True), (_BARE_YEAR, False)):
        for m in pattern.finditer(folded):
            raw = m.group(1)
            year = (1900 + int(raw) if int(raw) >= 46 else 2000 + int(raw)) if expand else int(raw)
            if year > today.year + 1:
                continue  # probably not a year ("2100 points"); leave it alone
            hits = year_hits(year, playoff_context, latest_start)
            out.append(_mention("season", m, original, hits, note=None if hits else "no NBA season for that year"))
            folded = _mask(folded, m.start(), m.end())
    return out, folded


def season_start_years(mentions: list[Mention]) -> frozenset[int]:
    """Season start years implied by season and date mentions (for dated team names)."""
    years: set[int] = set()
    for mention in mentions:
        for hit in mention.hits:
            value = hit.value
            if isinstance(value, SeasonCandidateValue):
                years.add(int(value.season[:4]))
            elif isinstance(value, DateCandidateValue):
                components = value.components
                if components.kind.startswith("calendar_") and components.year is not None:
                    try:
                        start = dt.date(components.year, components.month, components.day)
                        if components.kind == "calendar_range":
                            if components.end_year is None:
                                continue
                            end = dt.date(components.end_year, components.end_month, components.end_day)
                        else:
                            end = start
                    except (TypeError, ValueError):
                        continue
                elif value.resolved is not None:
                    start, end = value.resolved.start, value.resolved.end
                else:
                    continue
                # Calendar components remain useful for team-name dating when
                # a valid range is too wide to resolve for a game search.
                cursor = start
                while cursor <= end:
                    years.add(int(get_nba_season(cursor.year, cursor.month)[:4]))
                    if cursor.month == 12:
                        cursor = dt.date(cursor.year + 1, 1, 1)
                    else:
                        cursor = dt.date(cursor.year, cursor.month + 1, 1)
    return frozenset(years)


# --- playoff rounds ---------------------------------------------------------

_CONF = r"(east(?:ern)?|west(?:ern)?)"
_CONF_WORD = r"(?:\s+conf(?:erence|\.)?)?"
_SEMIS = r"(?:semi-?finals?|semis)"
ROUND_LABELS = {
    "first_round": "First Round",
    "conference_semifinals": "Conference Semifinals",
    "conference_finals": "Conference Finals",
    "finals": "NBA Finals",
}
_ROUNDS: tuple[tuple[re.Pattern, str, float, str | None], ...] = tuple(
    (re.compile(p), key, score, note) for p, key, score, note in (
        (rf"\b{_CONF}{_CONF_WORD}\s+(?:finals?|championship)\b", "conference_finals", 1.0, None),
        (r"\b(ecf|wcf)\b", "conference_finals", 1.0, None),
        (r"\bconf(?:erence|\.)?\s+(?:finals?|championship)\b", "conference_finals", 1.0, None),
        (rf"\b{_CONF}{_CONF_WORD}\s+{_SEMIS}\b", "conference_semifinals", 1.0, None),
        (rf"\bconf(?:erence|\.)?\s+{_SEMIS}\b", "conference_semifinals", 1.0, None),
        (r"\bdivision\s+finals?\b", "conference_finals", 0.7, None),
        (rf"\bdivision\s+{_SEMIS}\b", "conference_semifinals", 0.7, None),
        (r"\b(?:first|1st|opening)[\s-]+round\b", "first_round", 1.0, None),
        (r"\b(?:second|2nd)[\s-]+round\b", "conference_semifinals", 1.0, None),
        (r"\b(?:third|3rd)[\s-]+round\b", "conference_finals", 0.9, None),
        (r"\bplay-?in(?:\s+tournament|\s+games?)?\b", "", 0.0, "the play-in tournament is not a playoff round"),
        (r"\bquarter-?finals?\b", "first_round", 0.6, None),
        (rf"\b{_SEMIS}\b", "conference_semifinals", 0.8, None),
        (r"\b(?:nba|baa)\s+finals?\b|\bthe\s+final\b(?!\s+(?:score|minute|seconds?|quarter|play|shot))|\bfinals\b"
         r"|\bchampionship(?:\s+series)?\b|\btitle(?:\s+series)?\b", "finals", 1.0, None),
        (r"\bchampions?\b|\bchamps\b|\bwon\s+it\s+all\b", "finals", 0.8, None),
    )
)


def _conference(text: str | None) -> str | None:
    if not text:
        return None
    return "east" if text.startswith("e") else "west"


def round_mentions(folded: str, original: str) -> tuple[list[Mention], str]:
    out = []
    for pattern, key, score, note in _ROUNDS:
        for m in pattern.finditer(folded):
            hits = []
            if key:
                conference = _conference(m.group(1) if m.groups() and m.group(1) else None)
                label = ROUND_LABELS[key]
                if conference:
                    label = f"{'Eastern' if conference == 'east' else 'Western'} {label}"
                hits.append(Hit(
                    field="round", key=key + (f".{conference}" if conference else ""), label=label,
                    source="pattern", score=score,
                    value=RoundCandidateValue(round=key, conference=conference),  # type: ignore[arg-type]
                ))
            out.append(_mention("round", m, original, hits, note=note))
            folded = _mask(folded, m.start(), m.end())
    return out, folded
