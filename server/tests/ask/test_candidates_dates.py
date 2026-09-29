import datetime as dt
from zoneinfo import ZoneInfo

import pytest

from server.ask.candidates import CandidateLookupService
from server.ask.models.request import AskContext

NY = ZoneInfo("America/New_York")
WEDNESDAY = dt.datetime(2026, 3, 18, 20, 0, tzinfo=NY)
FRIDAY = dt.datetime(2026, 3, 20, 12, 0, tzinfo=NY)


@pytest.fixture(scope="module")
def service():
    return CandidateLookupService()


def dates(service, question, reference_time=WEDNESDAY):
    result = service.lookup(question, AskContext(reference_time=reference_time))
    return result.sets["date"]


def resolved(date_set):
    return [
        (c.value.resolved.start.isoformat(), c.value.resolved.end.isoformat())
        for c in date_set.candidates
        if c.value.resolved is not None
    ]


def test_last_week_is_the_preceding_monday_to_sunday(service):
    date_set = dates(service, "Cavs games last week")
    assert resolved(date_set) == [("2026-03-09", "2026-03-15")]
    assert date_set.candidates[0].value.components.relative == "last_week"


def test_last_week_on_a_monday_and_across_new_year(service):
    monday = dt.datetime(2026, 3, 16, 9, 0, tzinfo=NY)
    assert resolved(dates(service, "games last week", monday)) == [("2026-03-09", "2026-03-15")]
    new_year = dt.datetime(2026, 1, 1, 9, 0, tzinfo=NY)
    assert resolved(dates(service, "games last week", new_year)) == [("2025-12-22", "2025-12-28")]


def test_relative_dates_use_new_york_calendar_day(service):
    # 03:00 UTC on Jan 2 is still Jan 1 in New York.
    utc = dt.datetime(2026, 1, 2, 3, 0, tzinfo=dt.timezone.utc)
    assert resolved(dates(service, "Heat games yesterday", utc)) == [("2025-12-31", "2025-12-31")]
    assert resolved(dates(service, "games today", utc)) == [("2026-01-01", "2026-01-01")]


def test_last_weekday_excludes_today(service):
    assert resolved(dates(service, "Suns games last Friday", FRIDAY)) == [("2026-03-13", "2026-03-13")]
    assert resolved(dates(service, "Suns games last Friday", WEDNESDAY)) == [("2026-03-13", "2026-03-13")]


def test_bare_weekday_keeps_both_readings(service):
    date_set = dates(service, "What did Steph do on Friday?")
    assert resolved(date_set) == [("2026-03-13", "2026-03-13"), ("2026-03-20", "2026-03-20")]


@pytest.mark.parametrize("question, month, day", [
    ("Games on February 14", 2, 14),
    ("What were the scores on Christmas?", 12, 25),
    ("Anthony Edwards points on March 2", 3, 2),
    ("Lakers game 1/23", 1, 23),
    ("Knicks on the 5th of May", 5, 5),
])
def test_calendar_date_without_year_is_never_defaulted(service, question, month, day):
    date_set = dates(service, question)
    assert date_set.status == "candidates"
    [candidate] = date_set.candidates
    assert candidate.value.components.year is None
    assert (candidate.value.components.month, candidate.value.components.day) == (month, day)
    assert candidate.value.resolved is None
    assert candidate.value.unresolved_reason == "year_required"


@pytest.mark.parametrize("question, expected", [
    ("Lakers versus Celtics on January 23, 2025", ("2025-01-23", "2025-01-23")),
    ("Mavs vs Nuggets 3/5/2026", ("2026-03-05", "2026-03-05")),
    ("Pistons games on 2026-02-10", ("2026-02-10", "2026-02-10")),
    ("Bucks game on the 2nd of March 2026", ("2026-03-02", "2026-03-02")),
    ("Blazers games from December 1-7, 2025", ("2025-12-01", "2025-12-07")),
    ("Lakers games from 2025-03-01 to 2025-03-03", ("2025-03-01", "2025-03-03")),
    ("Lakers games from March 1, 2025 to March 3, 2025", ("2025-03-01", "2025-03-03")),
    ("Lakers games from March 1 to March 3, 2025", ("2025-03-01", "2025-03-03")),
    ("games from December 30, 2025 to January 2", ("2025-12-30", "2026-01-02")),
    ("games between April 29 and May 2, 2024", ("2024-04-29", "2024-05-02")),
    ("games between December 30 and January 2, 2025", ("2024-12-30", "2025-01-02")),
    ("games in the past 3 days", ("2026-03-16", "2026-03-18")),
    ("games from two days ago", ("2026-03-16", "2026-03-16")),
    ("Warriors games this weekend", ("2026-03-21", "2026-03-22")),
    ("games this week", ("2026-03-16", "2026-03-22")),
    ("Knicks scores from last night", ("2026-03-17", "2026-03-17")),
])
def test_resolved_dates(service, question, expected):
    assert resolved(dates(service, question)) == [expected]


def test_long_ranges_are_kept_but_unresolved(service):
    [candidate] = dates(service, "every game from last month").candidates
    assert candidate.value.resolved is None
    assert candidate.value.unresolved_reason == "range_too_long"
    [candidate] = dates(service, "Games in March 2025").candidates
    assert candidate.value.unresolved_reason == "range_too_long"


def test_between_range_without_year_stays_unresolved(service):
    [candidate] = dates(service, "games between April 29 and May 2").candidates
    assert candidate.value.resolved is None
    assert candidate.value.unresolved_reason == "year_required"
    assert candidate.value.components.year is None
    assert candidate.value.components.end_year is None


def test_impossible_date_is_flagged_not_moved(service):
    [candidate] = dates(service, "games on February 30, 2025").candidates
    assert candidate.value.resolved is None
    assert candidate.value.unresolved_reason == "invalid_date"


def test_leap_day_names_february_29_of_its_year(service):
    result = service.lookup("Any NBA games on leap day in 2024?", AskContext(reference_time=WEDNESDAY))
    assert resolved(result.sets["date"]) == [("2024-02-29", "2024-02-29")]
    # The year belongs to the date, so it is not also offered as a season.
    assert result.sets["season"].status == "not_mentioned"
    [candidate] = dates(service, "games on leap day 2023").candidates
    assert candidate.value.unresolved_reason == "invalid_date"
    [candidate] = dates(service, "games on leap day").candidates
    assert candidate.value.unresolved_reason == "year_required"


@pytest.mark.parametrize("question", [
    "games on January 32, 2025",
    "games from March 0-5, 2025",
])
def test_unrepresentable_invalid_date_components_abstain(service, question):
    date_set = dates(service, question)
    assert date_set.status == "no_candidates"
    assert date_set.candidates == []
    assert date_set.unmatched_text


def test_no_date_language_means_not_mentioned(service):
    assert dates(service, "Who won the 2016 Finals?").status == "not_mentioned"
