import datetime as dt

from server.ask.eval import builders as b
from server.ask.candidates import CandidateLookupService
from server.ask.models.common import DateComponents
from server.ask.models.interpreter import FieldInterpretation, InterpreterMetadata, InterpreterOutput
from server.ask.models.request import AskContext
from server.ask.normalize import Normalizer
from server.ask.present import clarification, notice
from server.ask.resolution import PendingResolution, ResolutionStore, choose

CONTEXT = AskContext(reference_time=dt.datetime.fromisoformat("2026-09-29T12:00:00-04:00"))
META = InterpreterMetadata(adapter="jev", provider="typesafe", model="jev-1.13.0", latency_ms=1)


def output(*fields):
    return InterpreterOutput(outcome="interpreted", fields=list(fields), metadata=META)


def selected(field, *values):
    return FieldInterpretation(field=field, status="selected", selected=list(values), confidence=1)


def team(team_id, tricode, name, matched, span):
    return b.team(team_id, tricode, name, matched=matched, score=1.0).model_copy(update={"span": span})


def test_multi_mention_team_ambiguity_requires_edit_instead_of_dropping_a_constraint(tmp_path):
    knicks = team(1610612752, "NYK", "New York Knicks", "Knicks", (0, 6))
    lakers = team(1610612747, "LAL", "Los Angeles Lakers", "LA", (10, 12))
    clippers = team(1610612746, "LAC", "Los Angeles Clippers", "LA", (10, 12))
    day = b.date(0, "March 1, 2025", DateComponents(kind="calendar_date", year=2025, month=3, day=1),
                 start=dt.date(2025, 3, 1), matched="March 1, 2025")
    candidates = b.lookup_result([knicks, lakers, clippers, day])
    ambiguous = FieldInterpretation(field="teams", status="ambiguous", alternatives=[lakers.id, clippers.id])
    pending = PendingResolution(
        output=output(selected("intent", "game_search"), ambiguous, selected("date", day.id)),
        candidates=candidates, context=CONTEXT,
    )
    store = ResolutionStore(tmp_path / "resolution.sqlite3")
    for question in ("Knicks vs LA games March 1, 2025", "LA games, not Knicks, March 1, 2025"):
        presented = clarification("teams", "ambiguous", question, pending, store)
        assert presented.options == []
        assert "Edit your question" in presented.hint


def test_single_span_team_ambiguity_can_offer_token_choices(tmp_path):
    lakers = team(1610612747, "LAL", "Los Angeles Lakers", "LA", (0, 2))
    clippers = team(1610612746, "LAC", "Los Angeles Clippers", "LA", (0, 2))
    day = b.date(0, "March 1, 2025", DateComponents(kind="calendar_date", year=2025, month=3, day=1),
                 start=dt.date(2025, 3, 1), matched="March 1, 2025")
    candidates = b.lookup_result([lakers, clippers, day])
    ambiguous = FieldInterpretation(field="teams", status="ambiguous", alternatives=[lakers.id, clippers.id])
    pending = PendingResolution(
        output=output(selected("intent", "game_search"), ambiguous, selected("date", day.id)),
        candidates=candidates, context=CONTEXT,
    )
    store = ResolutionStore(tmp_path / "resolution.sqlite3")

    presented = clarification("teams", "ambiguous", "LA games March 1, 2025", pending, store)
    assert {option.id for option in presented.options} == {lakers.id, clippers.id}
    chosen = choose(pending, "teams", candidate_id=lakers.id)
    result = Normalizer().normalize(chosen.output, chosen.candidates, CONTEXT)
    assert result.status == "valid"
    assert [t.team_id for t in result.request.teams] == [lakers.value.team.team_id]


def test_selected_two_team_focus_clarification_requires_edit(tmp_path):
    knicks = team(1610612752, "NYK", "New York Knicks", "Knicks", (0, 6))
    lakers = team(1610612747, "LAL", "Los Angeles Lakers", "Lakers", (10, 16))
    day = b.date(0, "March 1, 2025", DateComponents(kind="calendar_date", year=2025, month=3, day=1),
                 start=dt.date(2025, 3, 1), matched="March 1, 2025")
    pending = PendingResolution(
        output=output(selected("intent", "boxscore_stat"), selected("stat_scope", "team"),
                      selected("stat", "points"), selected("teams", knicks.id, lakers.id),
                      selected("date", day.id)),
        candidates=b.lookup_result([knicks, lakers, day]), context=CONTEXT,
    )
    presented = clarification("teams", "ambiguous", "Knicks vs Lakers points March 1, 2025", pending,
                             ResolutionStore(tmp_path / "resolution.sqlite3"))
    assert presented.options == []
    assert presented.hint == "Edit your question to name the team whose stat you want."


def test_unusable_date_choices_are_replaced_with_an_edit_hint(tmp_path):
    long_month = b.date(0, "March", DateComponents(kind="calendar_range", month=3, day=1,
                    end_month=3, end_day=31), unresolved="year_required", matched="March")
    pending = PendingResolution(
        output=output(selected("intent", "game_search"), selected("date", long_month.id)),
        candidates=b.lookup_result([long_month]), context=CONTEXT,
    )
    result = clarification("date", "year_required", "games in March", pending,
                          ResolutionStore(tmp_path / "resolution.sqlite3"))
    assert result.options == []
    assert result.prompt == "Choose a specific game date"
    assert result.hint == "Edit your question to name one date or a range of up to seven days."


def test_selected_unusable_date_is_not_offered_again(tmp_path):
    impossible = b.date(0, "February 30, 2025", DateComponents(kind="calendar_date", year=2025, month=2, day=30),
                        unresolved="invalid_date", matched="February 30, 2025")
    pending = PendingResolution(
        output=output(selected("intent", "game_search"), selected("date", impossible.id)),
        candidates=b.lookup_result([impossible]), context=CONTEXT,
    )
    result = clarification("date", "missing", "games on February 30, 2025", pending,
                          ResolutionStore(tmp_path / "resolution.sqlite3"))
    assert result.options == []
    assert result.hint


def test_cross_year_date_choice_rewrites_and_replays_the_exact_range(tmp_path):
    question = "Knicks games between December 28 and January 3"
    lookup = CandidateLookupService()
    initial = lookup.lookup(question, CONTEXT)
    candidate = initial.sets["date"].candidates[0]
    pending = PendingResolution(
        output=output(selected("intent", "game_search"), selected("date", candidate.id)),
        candidates=initial, context=CONTEXT,
    )
    store = ResolutionStore(tmp_path / "resolution.sqlite3")

    result = clarification("date", "year_required", question, pending, store)
    choice = next(option for option in result.options if option.id == "year:2025")
    assert "2025-12-28 to 2026-01-03" in choice.question
    assert choice.question.startswith("Knicks games ")

    reparsed = lookup.lookup(choice.question, CONTEXT).sets["date"].candidates
    [fresh_range] = [item.value.resolved for item in reparsed if item.value.resolved is not None]
    replayed = store.read(choice.resolution, choice.question, CONTEXT)
    assert replayed is not None
    selected_id = replayed.output.get_field("date").selected[0]
    token_range = replayed.candidates.by_id(selected_id).value.resolved
    assert fresh_range == token_range
    assert (fresh_range.start, fresh_range.end) == (dt.date(2025, 12, 28), dt.date(2026, 1, 3))


def test_year_choice_without_a_date_span_requires_edit_instead_of_dropping_constraints(tmp_path):
    question = "Knicks games for the range"
    components = DateComponents(kind="calendar_range", month=12, day=28, end_month=1, end_day=3)
    pending = PendingResolution(
        output=InterpreterOutput(outcome="interpreted", fields=[selected("intent", "game_search")],
                                 extracted_date=components, metadata=META),
        candidates=b.lookup_result([]), context=CONTEXT,
    )
    result = clarification("date", "year_required", question, pending,
                          ResolutionStore(tmp_path / "resolution.sqlite3"))
    assert result.options == []
    assert "Edit your question" in result.hint


def test_recent_player_record_notice_does_not_claim_permanent_absence():
    result = notice("no_record", reason="recent_player_record_unverified")
    assert result.message == "No verified player record is available for that date yet."
