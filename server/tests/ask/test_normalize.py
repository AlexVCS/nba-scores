import datetime as dt

import pytest

from server.ask.eval import builders as b
from server.ask.models.common import DateComponents, DateRange
from server.ask.models.interpreter import (
    FieldInterpretation,
    InterpreterMetadata,
    InterpreterOutput,
)
from server.ask.models.request import AskContext
from server.ask.normalize import Normalizer, canonical_request, relevant_fields, resolve_components
from server.ask.protocols import RequestNormalizer

TUESDAY = dt.date(2026, 9, 29)
CONTEXT = AskContext(reference_time=dt.datetime.fromisoformat("2026-09-29T12:00:00-04:00"))
META = InterpreterMetadata(adapter="jev", provider="typesafe", model="jev-1.13.0", latency_ms=1)
CLE = b.team(1610612739, "CLE", "Cleveland Cavaliers")
BOS = b.team(1610612738, "BOS", "Boston Celtics")
TATUM = b.player(1628369, "Jayson Tatum")
LAST_WEEK = b.date(0, "last week", DateComponents(kind="relative", relative="last_week"),
                   start=dt.date(2026, 9, 21), end=dt.date(2026, 9, 27))
JAN_23 = b.date(1, "January 23", DateComponents(kind="calendar_date", month=1, day=23), unresolved="year_required")
SEASON = b.season("2023-24", from_year=2024)
FINALS = b.playoff_round("finals")
GAME_4 = b.game_number(4)


def sel(field, *values, confidence=None):
    return FieldInterpretation(field=field, status="selected", selected=list(values), confidence=confidence)


def output(*fields, extracted_date=None):
    return InterpreterOutput(outcome="interpreted", fields=list(fields), extracted_date=extracted_date, metadata=META)


def normalize(out, candidates):
    return Normalizer().normalize(out, candidates, CONTEXT)


def test_normalizer_satisfies_protocol():
    assert isinstance(Normalizer(), RequestNormalizer)


def test_game_search_with_candidate_date_and_team():
    result = normalize(output(sel("intent", "game_search"), sel("date", "date:0"), sel("teams", CLE.id)),
                       b.lookup_result([CLE, LAST_WEEK]))
    assert result.status == "valid"
    assert result.request.dates == DateRange(start=dt.date(2026, 9, 21), end=dt.date(2026, 9, 27))
    assert [t.tricode for t in result.request.teams] == ["CLE"]


def test_player_stat_by_playoff_game():
    candidates = b.lookup_result([TATUM, SEASON, FINALS, GAME_4])
    result = normalize(output(
        sel("intent", "boxscore_stat"), sel("stat_scope", "player"), sel("stat", "points"),
        sel("aggregation", "total"), sel("player", TATUM.id), sel("season", SEASON.id),
        sel("round", FINALS.id), sel("game_number", GAME_4.id),
    ), candidates)
    assert result.status == "valid"
    game = result.request.game
    assert (game.season, game.round, game.game_number) == ("2023-24", "finals", 4)
    assert result.request.player.player_id == 1628369


def test_date_does_not_discard_named_playoff_game_constraints():
    game_day = b.date(2, "June 9, 2024", DateComponents(kind="calendar_date", year=2024, month=6, day=9),
                      start=dt.date(2024, 6, 9), end=dt.date(2024, 6, 9))
    result = normalize(output(
        sel("intent", "boxscore_stat"), sel("stat_scope", "player"), sel("stat", "points"),
        sel("player", TATUM.id), sel("date", game_day.id), sel("season", SEASON.id),
        sel("round", FINALS.id), sel("game_number", b.game_number(1).id),
    ), b.lookup_result([TATUM, game_day, SEASON, FINALS, b.game_number(1)]))
    assert result.status == "valid"
    assert (result.request.game.date, result.request.game.season, result.request.game.round,
            result.request.game.game_number) == (dt.date(2024, 6, 9), "2023-24", "finals", 1)


def test_boxscore_page_game_is_used_without_an_explicit_selector():
    context = CONTEXT.model_copy(update={"route": "boxscore", "game_id": "0022400001"})
    result = Normalizer().normalize(output(
        sel("intent", "boxscore_stat"), sel("stat_scope", "player"),
        sel("stat", "rebounds"), sel("player", TATUM.id),
    ), b.lookup_result([TATUM]), context)
    assert result.status == "valid"
    assert result.request.game.game_id == "0022400001"


def test_context_game_keeps_named_team_for_participant_verification():
    context = CONTEXT.model_copy(update={"route": "boxscore", "game_id": "0022400001"})
    result = Normalizer().normalize(output(
        sel("intent", "boxscore_stat"), sel("stat_scope", "team"),
        sel("stat", "rebounds"), sel("teams", CLE.id),
    ), b.lookup_result([CLE]), context)
    assert result.status == "valid"
    assert result.request.game.game_id == "0022400001"
    assert result.request.game.teams == [CLE.value.team]


def test_two_team_stat_does_not_broaden_to_both_teams():
    game_day = b.date(2, "January 12, 2024", DateComponents(kind="calendar_date", year=2024, month=1, day=12),
                      start=dt.date(2024, 1, 12), end=dt.date(2024, 1, 12))
    candidates = b.lookup_result([CLE, BOS, game_day])
    result = normalize(output(
        sel("intent", "boxscore_stat"), sel("stat_scope", "team"),
        sel("stat", "turnovers"), sel("teams", CLE.id, BOS.id), sel("date", game_day.id),
    ), candidates)
    assert (result.status, result.clarify_field, result.clarify_reason) == (
        "needs_clarification", "teams", "ambiguous"
    )

    # A standalone clarification rewrite names the chosen team and can be
    # normalized without interpreting list order as the target.
    resolved = normalize(output(
        sel("intent", "boxscore_stat"), sel("stat_scope", "team"),
        sel("stat", "turnovers"), sel("teams", CLE.id), sel("date", game_day.id),
    ), candidates)
    assert resolved.status == "valid"
    assert resolved.request.team == CLE.value.team
    assert resolved.request.game.teams == [CLE.value.team]


def test_explicit_game_selection_takes_priority_over_context_game():
    context = CONTEXT.model_copy(update={"route": "boxscore", "game_id": "0022400001"})
    game_day = b.date(2, "June 9, 2024", DateComponents(kind="calendar_date", year=2024, month=6, day=9),
                      start=dt.date(2024, 6, 9), end=dt.date(2024, 6, 9))
    cases = [
        (output(sel("intent", "boxscore_stat"), sel("stat_scope", "player"), sel("player", TATUM.id),
                sel("date", game_day.id)), b.lookup_result([TATUM, game_day]), "valid", "date"),
        (output(sel("intent", "boxscore_stat"), sel("stat_scope", "player"), sel("player", TATUM.id),
                sel("season", SEASON.id), sel("round", FINALS.id), sel("game_number", GAME_4.id)),
         b.lookup_result([TATUM, SEASON, FINALS, GAME_4]), "valid", "season"),
        (output(sel("intent", "boxscore_stat"), sel("stat_scope", "player"), sel("player", TATUM.id),
                sel("round", FINALS.id)), b.lookup_result([TATUM, FINALS]), "needs_clarification", "season"),
    ]
    for interpreted, candidates, status, field in cases:
        result = Normalizer().normalize(interpreted, candidates, context)
        assert result.status == status
        if status == "valid":
            assert result.request.game.game_id is None
            assert getattr(result.request.game, field) is not None
        else:
            assert result.clarify_field == field


def test_dated_leader_with_no_team_remains_a_supported_boxscore_request():
    game_day = b.date(2, "February 12, 2023", DateComponents(kind="calendar_date", year=2023, month=2, day=12),
                      start=dt.date(2023, 2, 12), end=dt.date(2023, 2, 12))
    result = normalize(output(sel("intent", "boxscore_stat"), sel("stat_scope", "leaders"),
                              sel("stat", "rebounds"), sel("date", game_day.id)),
                       b.lookup_result([game_day]))
    assert result.status == "valid"
    assert result.request.game.date == dt.date(2023, 2, 12)
    assert result.request.game.teams == []


def test_missing_stat_means_full_line_for_player_scope_but_not_leaders():
    candidates = b.lookup_result([TATUM, SEASON, FINALS, GAME_4])
    base = [sel("intent", "boxscore_stat"), sel("player", TATUM.id), sel("season", SEASON.id),
            sel("round", FINALS.id), sel("game_number", GAME_4.id)]
    assert normalize(output(*base, sel("stat_scope", "player")), candidates).request.stat.stat == "stat_line"
    leaders = normalize(output(*base[:1], *base[2:], sel("stat_scope", "leaders")), candidates)
    assert (leaders.status, leaders.clarify_field, leaders.clarify_reason) == ("needs_clarification", "stat", "missing")


def test_per_game_is_unsupported_not_answered_as_total():
    result = normalize(output(sel("intent", "boxscore_stat"), sel("stat_scope", "player"), sel("stat", "points"),
                              sel("aggregation", "per_game"), sel("player", TATUM.id), sel("season", SEASON.id)),
                       b.lookup_result([TATUM, SEASON]))
    assert result.status == "unsupported" and result.unsupported_reason == "multi_game_average"


@pytest.mark.parametrize("status", ["ambiguous", "no_matching_candidate"])
def test_unresolved_aggregation_returns_invalid_without_defaulting(status):
    aggregation = FieldInterpretation(field="aggregation", status=status,
                                      alternatives=["total", "per_game"] if status == "ambiguous" else [])
    result = normalize(output(sel("intent", "boxscore_stat"), sel("stat_scope", "player"),
                              sel("stat", "points"), sel("player", TATUM.id), aggregation),
                       b.lookup_result([TATUM]))
    assert result.status == "invalid"
    assert result.errors and "aggregation" in result.errors[0]


@pytest.mark.parametrize("stat", ["field_goal_percentage", "three_point_percentage", "free_throw_percentage", "stat_line"])
def test_leader_stat_without_ranking_rule_is_unsupported(stat):
    result = normalize(output(sel("intent", "boxscore_stat"), sel("stat_scope", "leaders"),
                              sel("stat", stat), sel("date", LAST_WEEK.id)),
                       b.lookup_result([LAST_WEEK]))
    assert (result.status, result.unsupported_reason) == ("unsupported", "unsupported_leader_stat")


def test_candidate_date_without_year_requires_year():
    result = normalize(output(sel("intent", "game_search"), sel("date", JAN_23.id)), b.lookup_result([JAN_23]))
    assert (result.status, result.clarify_field, result.clarify_reason) == ("needs_clarification", "date", "year_required")


def test_extracted_date_is_resolved_only_without_date_candidates():
    no_year = DateComponents(kind="calendar_date", month=1, day=23)
    result = normalize(output(sel("intent", "game_search"), extracted_date=no_year), b.lookup_result([]))
    assert result.clarify_reason == "year_required"

    with_year = DateComponents(kind="calendar_date", year=2025, month=1, day=23)
    result = normalize(output(sel("intent", "game_search"), extracted_date=with_year), b.lookup_result([]))
    assert result.request.dates == DateRange(start=dt.date(2025, 1, 23), end=dt.date(2025, 1, 23))

    # With a date candidate present, an extracted date is ignored (never overrides lookup).
    result = normalize(output(sel("intent", "game_search"), extracted_date=with_year), b.lookup_result([LAST_WEEK]))
    assert (result.status, result.clarify_field) == ("needs_clarification", "date")


@pytest.mark.parametrize("field, status", [("player", "ambiguous"), ("player", "no_matching_candidate")])
def test_unclear_required_field_is_clarified(field, status):
    alternatives = [TATUM.id, "player:2544"] if status == "ambiguous" else []
    candidates = b.lookup_result([TATUM, b.player(2544, "LeBron James"), LAST_WEEK])
    result = normalize(output(
        sel("intent", "boxscore_stat"), sel("stat_scope", "player"), sel("date", "date:0"),
        FieldInterpretation(field=field, status=status, alternatives=alternatives),
    ), candidates)
    assert (result.status, result.clarify_field, result.clarify_reason) == ("needs_clarification", field, status)


def test_unclear_optional_team_is_not_silently_dropped():
    result = normalize(output(sel("intent", "game_search"), sel("date", "date:0"),
                              FieldInterpretation(field="teams", status="no_matching_candidate")),
                       b.lookup_result([LAST_WEEK]))
    assert (result.clarify_field, result.clarify_reason) == ("teams", "no_matching_candidate")


def test_unknown_or_misfiled_ids_are_invalid():
    candidates = b.lookup_result([CLE, LAST_WEEK])
    assert normalize(output(sel("intent", "game_search"), sel("date", "date:9")), candidates).status == "invalid"
    assert normalize(output(sel("intent", "game_search"), sel("date", CLE.id)), candidates).status == "invalid"
    assert normalize(output(sel("intent", "space_search")), candidates).status == "invalid"


def test_series_and_postseason():
    season = b.season("2022-23", from_year=2023)
    result = normalize(output(sel("intent", "playoff_series"), sel("season", season.id), sel("round", FINALS.id)),
                       b.lookup_result([season, FINALS]))
    assert result.status == "valid" and result.request.round == "finals"

    incomplete = normalize(output(sel("intent", "playoff_series"), sel("season", season.id)), b.lookup_result([season]))
    assert (incomplete.status, incomplete.clarify_field) == ("needs_clarification", "round")

    den = b.team(1610612743, "DEN", "Denver Nuggets")
    result = normalize(output(sel("intent", "postseason_summary"), sel("season", season.id), sel("teams", den.id)),
                       b.lookup_result([season, den]))
    assert result.request.team.tricode == "DEN"


def test_specific_series_with_missing_details_clarifies_instead_of_widening_scope():
    season = b.season("2023-24", from_year=2024)
    cases = [
        (output(sel("intent", "playoff_series"), sel("season", season.id)), "round"),
        (output(sel("intent", "playoff_series"), sel("season", season.id), sel("teams", BOS.id)), "round"),
        (output(sel("intent", "playoff_series"), sel("season", season.id),
                sel("round", b.playoff_round("conference_finals").id)), "teams"),
    ]
    candidates = b.lookup_result([season, BOS, FINALS, b.playoff_round("conference_finals")])
    for interpreted, field in cases:
        result = normalize(interpreted, candidates)
        assert (result.status, result.clarify_field) == ("needs_clarification", field)


def test_single_game_stat_without_a_game_clarifies_the_date():
    jordan = b.player(893, "Michael Jordan")
    interpreted = output(sel("intent", "boxscore_stat"), sel("stat_scope", "player"),
                         sel("stat", "assists"), sel("player", jordan.id))
    result = normalize(interpreted, b.lookup_result([jordan]))
    assert (result.status, result.clarify_field, result.clarify_reason) == ("needs_clarification", "date", "missing")


def test_unsupported_and_unreliable_outputs():
    unsupported = InterpreterOutput(outcome="unsupported", unsupported_reason="career_stats", metadata=META)
    assert normalize(unsupported, b.lookup_result([])).unsupported_reason == "career_stats"
    unreliable = InterpreterOutput(outcome="unreliable", metadata=META)
    assert normalize(unreliable, b.lookup_result([])).status == "invalid"


@pytest.mark.parametrize(
    "parts, expected",
    [
        (dict(relative="today"), (TUESDAY, TUESDAY)),
        (dict(relative="last_night"), (dt.date(2026, 9, 28),) * 2),
        (dict(relative="last_week"), (dt.date(2026, 9, 21), dt.date(2026, 9, 27))),
        (dict(relative="this_week"), (dt.date(2026, 9, 28), dt.date(2026, 10, 4))),
        (dict(relative="last_weekday", weekday="tuesday"), (dt.date(2026, 9, 22),) * 2),
        (dict(relative="last_weekday", weekday="friday"), (dt.date(2026, 9, 25),) * 2),
        (dict(relative="past_days", count=3), (dt.date(2026, 9, 27), TUESDAY)),
    ],
)
def test_relative_dates_resolve_in_new_york(parts, expected):
    resolved = resolve_components(DateComponents(kind="relative", **parts), TUESDAY)
    assert (resolved.start, resolved.end) == expected


def test_calendar_resolution_edge_cases():
    rng = DateComponents(kind="calendar_range", year=2025, month=3, day=1, end_month=3, end_day=5)
    assert resolve_components(rng, TUESDAY) == DateRange(start=dt.date(2025, 3, 1), end=dt.date(2025, 3, 5))
    long = DateComponents(kind="calendar_range", year=2025, month=3, day=1, end_month=3, end_day=20)
    assert resolve_components(long, TUESDAY) == "range_too_long"
    impossible = DateComponents(kind="calendar_date", year=2025, month=2, day=30)
    assert resolve_components(impossible, TUESDAY) == "invalid_date"


def test_calendar_range_year_choice_rolls_end_year_at_new_year():
    rng = DateComponents(kind="calendar_range", year=2025, month=12, day=28, end_month=1, end_day=3)
    assert resolve_components(rng, TUESDAY) == DateRange(start=dt.date(2025, 12, 28), end=dt.date(2026, 1, 3))


def test_reference_time_is_converted_to_new_york():
    late_utc = AskContext(reference_time=dt.datetime(2026, 9, 30, 2, 0, tzinfo=dt.timezone.utc))
    result = Normalizer().normalize(
        output(sel("intent", "game_search"), extracted_date=DateComponents(kind="relative", relative="today")),
        b.lookup_result([]), late_utc,
    )
    assert result.request.dates.start == TUESDAY  # 22:00 on the 29th in New York


def test_canonical_request_ignores_team_order():
    candidates = b.lookup_result([CLE, BOS, LAST_WEEK])
    a = normalize(output(sel("intent", "game_search"), sel("date", "date:0"), sel("teams", CLE.id, BOS.id)), candidates)
    c = normalize(output(sel("intent", "game_search"), sel("date", "date:0"), sel("teams", BOS.id, CLE.id)), candidates)
    assert canonical_request(a.request) == canonical_request(c.request)


def ambiguous(field, *values):
    return FieldInterpretation(field=field, status="ambiguous", alternatives=list(values))


def test_field_unclear_under_every_intent_is_asked_before_the_intent():
    candidates = b.lookup_result([CLE, BOS, SEASON])
    result = normalize(output(
        ambiguous("intent", "playoff_series", "postseason_summary"), sel("season", SEASON.id),
        ambiguous("teams", CLE.id, BOS.id),
    ), candidates)
    assert (result.status, result.clarify_field, result.clarify_reason) == ("needs_clarification", "teams", "ambiguous")


def test_intent_is_asked_first_when_the_unclear_field_matters_to_only_one_reading():
    candidates = b.lookup_result([TATUM, SEASON], unmatched={"player": ["Tatumm"]})
    result = normalize(output(
        ambiguous("intent", "boxscore_stat", "postseason_summary"), sel("season", SEASON.id),
        FieldInterpretation(field="player", status="no_matching_candidate"),
    ), candidates)
    assert (result.clarify_field, result.clarify_reason) == ("intent", "ambiguous")


def _team_stat(*fields):
    game_day = b.date(2, "March 3, 2024", DateComponents(kind="calendar_date", year=2024, month=3, day=3),
                      start=dt.date(2024, 3, 3), end=dt.date(2024, 3, 3))
    candidates = b.lookup_result([CLE, BOS, game_day])
    return normalize(output(
        sel("intent", "boxscore_stat"), sel("stat_scope", "team"), sel("stat", "steals"),
        sel("date", game_day.id), *fields,
    ), candidates)


@pytest.mark.parametrize("target", [CLE, BOS])
def test_target_team_picks_the_stat_team_and_keeps_both_in_the_game(target):
    result = _team_stat(sel("teams", BOS.id, CLE.id), sel("target_team", target.id))
    assert result.status == "valid"
    assert result.request.team == target.value.team
    assert {t.tricode for t in result.request.game.teams} == {"CLE", "BOS"}


def test_target_team_alone_identifies_the_game_team():
    result = _team_stat(sel("target_team", BOS.id))
    assert result.status == "valid"
    assert result.request.team == BOS.value.team and result.request.game.teams == [BOS.value.team]


def test_target_team_outside_the_named_teams_is_clarified():
    result = _team_stat(sel("teams", CLE.id), sel("target_team", BOS.id))
    assert (result.clarify_field, result.clarify_reason) == ("teams", "ambiguous")


@pytest.mark.parametrize("status", ["ambiguous", "no_matching_candidate"])
def test_unclear_target_team_is_asked_as_teams(status):
    alternatives = [CLE.id, BOS.id] if status == "ambiguous" else []
    result = _team_stat(sel("teams", CLE.id, BOS.id),
                        FieldInterpretation(field="target_team", status=status, alternatives=alternatives))
    assert (result.clarify_field, result.clarify_reason) == ("teams", status)


def test_target_team_from_a_truncated_team_list_is_asked_as_teams():
    game_day = b.date(2, "March 3, 2024", DateComponents(kind="calendar_date", year=2024, month=3, day=3),
                      start=dt.date(2024, 3, 3), end=dt.date(2024, 3, 3))
    result = normalize(output(
        sel("intent", "boxscore_stat"), sel("stat_scope", "team"), sel("stat", "steals"),
        sel("date", game_day.id), sel("target_team", BOS.id),
    ), b.lookup_result([CLE, BOS, game_day], truncated=["team"]))
    assert (result.status, result.clarify_field, result.clarify_reason) == ("needs_clarification", "teams", "ambiguous")


def test_target_team_is_ignored_outside_team_scope():
    candidates = b.lookup_result([TATUM, CLE, BOS, LAST_WEEK])
    out = output(sel("intent", "boxscore_stat"), sel("stat_scope", "player"), sel("player", TATUM.id),
                 sel("teams", CLE.id, BOS.id), sel("target_team", CLE.id))
    assert "target_team" not in relevant_fields(out)
    assert "target_team" in relevant_fields(output(sel("intent", "boxscore_stat"), sel("stat_scope", "team")))
    assert normalize(out, candidates).clarify_field == "date"
