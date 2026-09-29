"""Date expressions -> contract ``DateComponents`` resolved in America/New_York.

Rules (docs/ask-contract.md):
- Relative dates resolve against the reference date (the New York calendar
  day of ``AskContext.reference_time``).
- "Last week" is the preceding Monday-Sunday.
- A calendar date without a year stays ``year=None`` with
  ``unresolved_reason="year_required"``. The year is never defaulted.
- Ranges longer than seven days are kept but unresolved (``range_too_long``).
"""
from __future__ import annotations

import calendar
import datetime as dt
import re
from typing import Callable, Iterator

from server.ask.candidates.types import Hit, Mention
from server.ask.models.candidates import DateCandidateValue
from server.ask.models.common import MAX_GAME_SEARCH_DAYS, DateComponents, DateRange

MONTHS = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3, "april": 4, "apr": 4,
    "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7, "august": 8, "aug": 8,
    "september": 9, "sept": 9, "sep": 9, "october": 10, "oct": 10, "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}
WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
NUMBER_WORDS = {
    "a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "fourteen": 14, "thirty": 30,
}
_MONTH = r"(" + "|".join(sorted(MONTHS, key=len, reverse=True)) + r")\.?"
_DAY = r"(\d{1,2})(?:st|nd|rd|th)?"
_YEAR = r"(?:,?\s+(\d{4}))?"
_NUM = r"(\d{1,2}|" + "|".join(NUMBER_WORDS) + r")"
_WEEKDAY = r"(" + "|".join(WEEKDAYS) + r")s?"
MIN_YEAR = 1946


def _num(text: str) -> int:
    return int(text) if text.isdigit() else NUMBER_WORDS[text]


def _expand_two_digit_year(text: str) -> int:
    value = int(text)
    return value if len(text) == 4 else (1900 + value if value >= 46 else 2000 + value)


def _fmt(day: dt.date) -> str:
    return f"{day:%a} {day:%b} {day.day}, {day.year}"


def _hit(components: DateComponents, start: dt.date | None, end: dt.date | None, label: str,
         *, score: float = 1.0, reason: str | None = None, source: str = "date_parser") -> Hit:
    resolved = None
    if reason is None and start is not None and end is not None:
        if (end - start).days >= MAX_GAME_SEARCH_DAYS:
            reason = "range_too_long"
        else:
            resolved = DateRange(start=start, end=end)
    if resolved is not None:
        label = f"{label}: {_fmt(start)}" if start == end else f"{label}: {_fmt(start)} to {_fmt(end)}"
    elif reason == "year_required":
        label = f"{label} (year required)"
    elif reason == "range_too_long":
        label = f"{label} (longer than {MAX_GAME_SEARCH_DAYS} days)"
    elif reason == "invalid_date":
        label = f"{label} (not a real date)"
    return Hit(
        field="date", key="", label=label[:120], source=source, score=score,  # type: ignore[arg-type]
        value=DateCandidateValue(components=components, resolved=resolved, unresolved_reason=reason),
    )


def calendar_hit(year: int | None, month: int, day: int, label: str, *, score: float = 1.0,
                 source: str = "date_parser") -> Hit | None:
    if year is not None and not MIN_YEAR <= year <= 2100:
        return None
    # DateComponents has coarse month/day bounds; values outside those bounds
    # cannot be represented even as an invalid_date candidate.
    if not 1 <= month <= 12 or not 1 <= day <= 31:
        return None
    components = DateComponents(kind="calendar_date", year=year, month=month, day=day)
    try:
        dt.date(year or 2000, month, day)  # 2000 is a leap year, so Feb 29 is allowed without a year
    except ValueError:
        return _hit(components, None, None, label, score=score, reason="invalid_date", source=source)
    if year is None:
        return _hit(components, None, None, label, score=score, reason="year_required", source=source)
    day_value = dt.date(year, month, day)
    return _hit(components, day_value, day_value, label, score=score, source=source)


def range_hit(year: int | None, month: int, day: int, end_year: int | None, end_month: int, end_day: int,
              label: str, *, score: float = 1.0) -> Hit | None:
    if any(y is not None and not MIN_YEAR <= y <= 2100 for y in (year, end_year)):
        return None
    if not (1 <= month <= 12 and 1 <= day <= 31 and 1 <= end_month <= 12 and 1 <= end_day <= 31):
        return None
    components = DateComponents(
        kind="calendar_range", year=year, month=month, day=day,
        end_year=end_year, end_month=end_month, end_day=end_day,
    )
    if year is None or end_year is None:
        return _hit(components, None, None, label, score=score, reason="year_required")
    try:
        start, end = dt.date(year, month, day), dt.date(end_year, end_month, end_day)
    except ValueError:
        return _hit(components, None, None, label, score=score, reason="invalid_date")
    if end < start:
        return _hit(components, None, None, label, score=score, reason="invalid_date")
    return _hit(components, start, end, label, score=score)


def _dated_range(start: dt.date, end: dt.date, label: str, score: float = 1.0) -> Hit:
    """A relative phrase the contract has no enum for, resolved to explicit calendar components."""
    if start == end:
        return calendar_hit(start.year, start.month, start.day, label, score=score)  # type: ignore[return-value]
    return range_hit(start.year, start.month, start.day, end.year, end.month, end.day, label, score=score)  # type: ignore[return-value]


def relative_hit(relative: str, today: dt.date, label: str, *, weekday: int | None = None,
                 count: int | None = None, score: float = 1.0) -> Hit:
    monday = today - dt.timedelta(days=today.weekday())
    if relative in ("today", "tonight"):
        start = end = today
    elif relative in ("yesterday", "last_night"):
        start = end = today - dt.timedelta(days=1)
    elif relative == "tomorrow":
        start = end = today + dt.timedelta(days=1)
    elif relative == "this_week":
        start, end = monday, monday + dt.timedelta(days=6)
    elif relative == "last_week":
        start, end = monday - dt.timedelta(days=7), monday - dt.timedelta(days=1)
    elif relative == "last_weekday":
        assert weekday is not None
        start = end = today - dt.timedelta(days=(today.weekday() - weekday) % 7 or 7)
    elif relative == "this_weekday":
        assert weekday is not None
        start = end = monday + dt.timedelta(days=weekday)
    elif relative == "past_days":
        assert count is not None
        start, end = today - dt.timedelta(days=count - 1), today
    else:  # pragma: no cover - guarded by the contract Literal
        raise ValueError(relative)
    components = DateComponents(
        kind="relative", relative=relative,  # type: ignore[arg-type]
        weekday=WEEKDAYS[weekday] if weekday is not None else None, count=count,  # type: ignore[arg-type]
    )
    return _hit(components, start, end, label, score=score)


Handler = Callable[[re.Match, dt.date], list[Hit]]


def _month_day_range(m: re.Match, today: dt.date) -> list[Hit]:
    month, day, end_month_text, end_day, year = m.group(1), int(m.group(2)), m.group(3), int(m.group(4)), m.group(5)
    end_month = MONTHS[end_month_text] if end_month_text else MONTHS[month]
    y = int(year) if year else None
    end_y = y
    if y is not None and end_month < MONTHS[month]:
        end_y = y + 1
    hit = range_hit(y, MONTHS[month], day, end_y, end_month, end_day, m.group(0).strip())
    return [hit] if hit else []


_MONTH_RANGE_WITH_YEARS = re.compile(
    rf"\b(?:from\s+)?(?P<start_month>{'|'.join(sorted(MONTHS, key=len, reverse=True))})\.?\s+"
    rf"(?P<start_day>\d{{1,2}})(?:st|nd|rd|th)?(?P<start_year>,?\s+\d{{4}})?\s*"
    rf"(?:-|to|through|until)\s*(?P<end_month>{'|'.join(sorted(MONTHS, key=len, reverse=True))})\.?\s+"
    rf"(?P<end_day>\d{{1,2}})(?:st|nd|rd|th)?(?P<end_year>,?\s+\d{{4}})?\b"
)

_BETWEEN_MONTH_DAYS = re.compile(
    rf"\bbetween\s+(?P<start_month>{'|'.join(sorted(MONTHS, key=len, reverse=True))})\.?\s+"
    rf"(?P<start_day>\d{{1,2}})(?:st|nd|rd|th)?(?P<start_year>,?\s+\d{{4}})?\s+and\s+"
    rf"(?P<end_month>{'|'.join(sorted(MONTHS, key=len, reverse=True))})\.?\s+"
    rf"(?P<end_day>\d{{1,2}})(?:st|nd|rd|th)?(?P<end_year>,?\s+\d{{4}})?\b"
)


def _month_range_with_years(m: re.Match, today: dt.date) -> list[Hit]:
    start_month = MONTHS[m.group("start_month")]
    start_day = int(m.group("start_day"))
    end_month = MONTHS[m.group("end_month")]
    end_day = int(m.group("end_day"))
    start_year = int(m.group("start_year").replace(",", "").strip()) if m.group("start_year") else None
    end_year = int(m.group("end_year").replace(",", "").strip()) if m.group("end_year") else None
    if start_year is None and end_year is not None:
        start_year = end_year - (1 if end_month < start_month else 0)
    elif start_year is not None and end_year is None:
        end_year = start_year + (1 if end_month < start_month else 0)
    hit = range_hit(start_year, start_month, start_day, end_year, end_month, end_day, m.group(0).strip())
    return [hit] if hit else []


def _between_month_days(m: re.Match, today: dt.date) -> list[Hit]:
    start_month = MONTHS[m.group("start_month")]
    start_day = int(m.group("start_day"))
    end_month = MONTHS[m.group("end_month")]
    end_day = int(m.group("end_day"))
    start_year = int(m.group("start_year").replace(",", "").strip()) if m.group("start_year") else None
    end_year = int(m.group("end_year").replace(",", "").strip()) if m.group("end_year") else None
    if start_year is None and end_year is not None:
        start_year = end_year - (1 if end_month < start_month else 0)
    elif start_year is not None and end_year is None:
        end_year = start_year + (1 if end_month < start_month else 0)
    hit = range_hit(start_year, start_month, start_day, end_year, end_month, end_day, m.group(0).strip())
    return [hit] if hit else []


_ISO_RANGE = re.compile(r"\b(?:from\s+)?(\d{4})-(\d{1,2})-(\d{1,2})\s*(?:-|to|through|until)\s*(\d{4})-(\d{1,2})-(\d{1,2})\b")


def _iso_range(m: re.Match, today: dt.date) -> list[Hit]:
    hit = range_hit(int(m.group(1)), int(m.group(2)), int(m.group(3)),
                    int(m.group(4)), int(m.group(5)), int(m.group(6)), m.group(0).strip())
    return [hit] if hit else []


def _month_day(m: re.Match, today: dt.date) -> list[Hit]:
    hit = calendar_hit(int(m.group(3)) if m.group(3) else None, MONTHS[m.group(1)], int(m.group(2)), m.group(0).strip())
    return [hit] if hit else []


def _day_month(m: re.Match, today: dt.date) -> list[Hit]:
    hit = calendar_hit(int(m.group(3)) if m.group(3) else None, MONTHS[m.group(2)], int(m.group(1)), m.group(0).strip())
    return [hit] if hit else []


def _iso(m: re.Match, today: dt.date) -> list[Hit]:
    month, day = int(m.group(2)), int(m.group(3))
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return []
    hit = calendar_hit(int(m.group(1)), month, day, m.group(0))
    return [hit] if hit else []


def _numeric(m: re.Match, today: dt.date) -> list[Hit]:
    month, day = int(m.group(1)), int(m.group(2))
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return []
    year = _expand_two_digit_year(m.group(3)) if m.group(3) else None
    hit = calendar_hit(year, month, day, m.group(0))
    return [hit] if hit else []


def _month_year(m: re.Match, today: dt.date) -> list[Hit]:
    month, year = MONTHS[m.group(1)], int(m.group(2))
    last = calendar.monthrange(year, month)[1] if MIN_YEAR <= year <= 2100 else 31
    hit = range_hit(year, month, 1, year, month, last, m.group(0).strip())
    return [hit] if hit else []


def _month_only(m: re.Match, today: dt.date) -> list[Hit]:
    month = MONTHS[m.group(1)]
    last = 29 if month == 2 else calendar.monthrange(2001, month)[1]
    hit = range_hit(None, month, 1, None, month, last, m.group(0).strip())
    return [hit] if hit else []


def _christmas(m: re.Match, today: dt.date) -> list[Hit]:
    hit = calendar_hit(int(m.group(1)) if m.group(1) else None, 12, 25, m.group(0).strip())
    return [hit] if hit else []


def _leap_day(m: re.Match, today: dt.date) -> list[Hit]:
    # Feb 29 of a non-leap year becomes an invalid_date candidate, never a nearby day.
    hit = calendar_hit(int(m.group(1)) if m.group(1) else None, 2, 29, m.group(0).strip())
    return [hit] if hit else []


def _fixed(relative: str) -> Handler:
    return lambda m, today: [relative_hit(relative, today, m.group(0).strip())]


def _day_before_yesterday(m: re.Match, today: dt.date) -> list[Hit]:
    return [_dated_range(today - dt.timedelta(days=2), today - dt.timedelta(days=2), m.group(0).strip())]


def _past_days(m: re.Match, today: dt.date) -> list[Hit]:
    count = _num(m.group(1))
    if count < 1:
        return []
    if count <= MAX_GAME_SEARCH_DAYS:
        return [relative_hit("past_days", today, m.group(0).strip(), count=count)]
    return [_dated_range(today - dt.timedelta(days=count - 1), today, m.group(0).strip())]


def _ago(m: re.Match, today: dt.date) -> list[Hit]:
    count = _num(m.group(1)) * (7 if m.group(2).startswith("week") else 1)
    day = today - dt.timedelta(days=count)
    return [_dated_range(day, day, m.group(0).strip())]


def _next_week(m: re.Match, today: dt.date) -> list[Hit]:
    monday = today - dt.timedelta(days=today.weekday()) + dt.timedelta(days=7)
    return [_dated_range(monday, monday + dt.timedelta(days=6), m.group(0).strip())]


def _weekend(m: re.Match, today: dt.date) -> list[Hit]:
    saturday = today - dt.timedelta(days=today.weekday()) + dt.timedelta(days=5)
    shift = {"this": 0, "last": -7, "past": -7, "next": 7}[m.group(1)]
    saturday += dt.timedelta(days=shift)
    return [_dated_range(saturday, saturday + dt.timedelta(days=1), m.group(0).strip())]


def _month_relative(m: re.Match, today: dt.date) -> list[Hit]:
    year, month = today.year, today.month
    if m.group(1) == "last":
        year, month = (year - 1, 12) if month == 1 else (year, month - 1)
    elif m.group(1) == "next":
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    last = calendar.monthrange(year, month)[1]
    return [_dated_range(dt.date(year, month, 1), dt.date(year, month, last), m.group(0).strip())]


def _weekday(m: re.Match, today: dt.date) -> list[Hit]:
    qualifier, weekday = m.group(1), WEEKDAYS.index(m.group(2))
    text = m.group(0).strip()
    if qualifier and qualifier.split()[-1] in ("last", "past", "previous", "recent", "latest"):
        return [relative_hit("last_weekday", today, text, weekday=weekday)]
    if qualifier == "this":
        return [relative_hit("this_weekday", today, text, weekday=weekday)]
    if qualifier == "next":
        ahead = (weekday - today.weekday()) % 7 or 7
        upcoming = today + dt.timedelta(days=ahead)
        next_week = today - dt.timedelta(days=today.weekday()) + dt.timedelta(days=7 + weekday)
        hits = [_dated_range(upcoming, upcoming, text, score=0.6)]
        if next_week != upcoming:
            hits.append(_dated_range(next_week, next_week, text, score=0.4))
        return hits
    # A bare weekday ("on Friday") is ambiguous between the last one and this week's.
    hits = [relative_hit("last_weekday", today, text, weekday=weekday, score=0.6)]
    this_week = relative_hit("this_weekday", today, text, weekday=weekday, score=0.5)
    if this_week.value.resolved != hits[0].value.resolved:  # type: ignore[attr-defined]
        hits.append(this_week)
    return hits


PATTERNS: tuple[tuple[re.Pattern, Handler], ...] = tuple((re.compile(p), h) for p, h in (
    (_ISO_RANGE, _iso_range),
    (_MONTH_RANGE_WITH_YEARS, _month_range_with_years),
    (_BETWEEN_MONTH_DAYS, _between_month_days),
    (rf"\b{_MONTH}\s+{_DAY}\s*(?:-|to|through|until)\s*(?:{_MONTH}\s+)?{_DAY}{_YEAR}\b", _month_day_range),
    (rf"\b{_MONTH}\s+{_DAY}{_YEAR}\b", _month_day),
    (rf"\b{_DAY}\s+(?:of\s+)?{_MONTH}{_YEAR}\b", _day_month),
    (r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", _iso),
    (r"(?<![\d/])(\d{1,2})/(\d{1,2})(?:/(\d{4}|\d{2}))?(?![\d/])", _numeric),
    (rf"\b{_MONTH}\s+(?:of\s+)?(\d{{4}})\b", _month_year),
    (rf"\b(?:in|during|early|late|mid)\s+{_MONTH}(?=\s|$|[?.!,])", _month_only),
    (r"\bchristmas(?:\s+day)?(?:\s+(\d{4}))?\b", _christmas),
    (r"\bleap\s+day(?:(?:\s+(?:in|of)|,)?\s+(\d{4}))?\b", _leap_day),
    (r"\bday\s+before\s+yesterday\b", _day_before_yesterday),
    (r"\blast\s+night\b", _fixed("last_night")),
    (r"\byesterday(?:'s)?\b", _fixed("yesterday")),
    (r"\b(?:tonight|tonite)(?:'s)?\b", _fixed("tonight")),
    (r"\b(?:today(?:'s)?|this\s+(?:morning|afternoon|evening))\b", _fixed("today")),
    (r"\btomorrow(?:'s)?\b", _fixed("tomorrow")),
    (rf"\b(?:in\s+)?(?:the\s+)?(?:last|past|previous)\s+{_NUM}\s+days\b", _past_days),
    (rf"\b{_NUM}\s+(days?|weeks?)\s+ago\b", _ago),
    (r"\b(this|last|past|next)\s+weekend\b", _weekend),
    (r"\b(?:the\s+)?past\s+week\b", lambda m, today: [relative_hit("past_days", today, m.group(0).strip(), count=7)]),
    (r"\b(?:last|previous)\s+week(?:'s)?\b", _fixed("last_week")),
    (r"\bthis\s+week(?:'s)?\b", _fixed("this_week")),
    (r"\bnext\s+week(?:'s)?\b", _next_week),
    (r"\b(last|this|next)\s+month(?:'s)?\b", _month_relative),
    (rf"\b(?:(last|past|previous|most\s+recent|latest|this|next|on)\s+)?{_WEEKDAY}(?:'s)?(?:\s+night)?\b", _weekday),
))


def extract(folded: str, today: dt.date) -> Iterator[tuple[int, int, list[Hit]]]:
    """Yield (start, end, hits) for each date phrase, earliest patterns first.

    The caller masks each span so later patterns and entity matchers skip it.
    """
    text = folded
    found: list[tuple[int, int, list[Hit]]] = []
    for pattern, handler in PATTERNS:
        for m in pattern.finditer(text):
            found.append((m.start(), m.end(), handler(m, today)))
        for start, end, _ in found:
            text = text[:start] + " " * (end - start) + text[end:]
    yield from sorted(found, key=lambda item: item[0])


def mentions(folded: str, original: str, today: dt.date) -> tuple[list[Mention], str]:
    out: list[Mention] = []
    text = folded
    for start, end, hits in extract(folded, today):
        span_text = original[start:end].strip()
        lead = len(original[start:end]) - len(original[start:end].lstrip())
        out.append(Mention(field="date", start=start + lead, end=start + lead + len(span_text), text=span_text,
                           hits=hits, total=len(hits), note=None if hits else "unrecognized or out-of-range date"))
        text = text[:start] + " " * (end - start) + text[end:]
    return out, text
