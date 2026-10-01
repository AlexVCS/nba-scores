"""Live-testing feedback (2026-09-30): stated measures, top N above 25, "LeBron's career
points" and the per-game/totals toggle. Fakes only; no provider or NBA calls."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest

from server.ask.cache import AskCache
from server.ask.candidates.lookup import CandidateLookupService
from server.ask.config import AskConfig
from server.ask.eval import builders as b
from server.ask.eval.runner import LabeledCase
from server.ask.interpreters.tiered import Tier, TieredAdapter
from server.ask.measure import stated_measure, with_stated_measure
from server.ask.models.interpreter import FieldInterpretation, InterpreterMetadata, InterpreterOutput
from server.ask.models.request import AskContext, CareerStatsRequest, PlayerSeasonStatsRequest, SeasonLeadersRequest
from server.ask.models.response import AskQuery, AskResponse
from server.ask.normalize import Normalizer
from server.ask.pipeline import AskPipeline
from server.ask.present import clarification
from server.ask.resolution import PendingResolution, ResolutionStore
from server.ask.resolvers import career, seasons
from server.ask.resolvers.leaders import LIMIT_NOTE
from server.ask.resolvers.output import ResolverOutput
from server.ask.season_scope import normalize_question
from server.tests.ask.test_tiered import Fake, absent, sel

NOW = dt.datetime(2026, 9, 30, 12, tzinfo=dt.timezone(dt.timedelta(hours=-4)))
CONTEXT = AskContext(reference_time=NOW)
FIXTURES = Path(__file__).parent / "fixtures"
RESPONSES = Path(__file__).resolve().parents[3] / "src/services/ask/fixtures/responses"


def jev_output(intent, *fields):
    return InterpreterOutput(outcome="interpreted", fields=[sel("intent", intent, confidence=1.0), *fields],
                             metadata=InterpreterMetadata(adapter="jev", provider="typesafe", model="jev", latency_ms=1))


def guard(question, output, candidates=None):
    candidates = candidates or CandidateLookupService().lookup(question, CONTEXT)
    return normalize_question(Normalizer(), output, candidates, CONTEXT, question)


# -- 1. the measure comes from the question text -------------------------------------------


@pytest.mark.parametrize("question,measure", [
    ("Who led the league in assists in 2019-20?", None),
    ("Who made the most three-pointers in 2015-16?", None),
    ("Kevin Durant stats 2015-16", None),
    ("Who led the league in assists per game in 2019-20?", "per_game"),
    ("Jokic points per-game 2023-24", "per_game"),
    ("Jokic points a game in 2023-24", "per_game"),
    ("Who averaged the most rebounds in 2023-24?", "per_game"),
    ("Curry ppg 2015-16", "per_game"),
    ("LeBron James career average points", "per_game"),
    ("How many points did Kobe average in 2005-06?", "per_game"),
    ("Top 5 in total rebounds in 2023-24", "total"),
    ("Jokic season totals 2023-24", "total"),
    ("How many assists did Jokic have in 2023-24?", "total"),
    ("Jokic assists in total in 2023-24", "total"),
    ("Jokic total points and points per game in 2023-24", "both"),
    ("Who scored the most points in a game in 2023-24?", None),
    ("Who won the scoring title in 2013-14?", "per_game"),
    ("Who won the scoring crown in 1986-87?", "per_game"),
])
def test_stated_measure_is_read_from_the_question(question, measure):
    assert stated_measure(question) == measure


def test_leader_measure_the_model_chose_is_never_accepted():
    # The live read: Jev accepted intent 1.0, stat 1.0 and aggregation "total" 0.96.
    q = "Who led the league in assists in 2019-20?"
    output = jev_output("season_leaders", sel("season", "season:2019-20", confidence=1.0),
                        sel("stat", "assists", confidence=1.0), sel("aggregation", "total", confidence=0.96),
                        absent("season_type", confidence=0.93))
    n = guard(q, output)
    assert (n.status, n.clarify_field, n.clarify_reason) == ("needs_clarification", "aggregation", "ambiguous")
    stated = with_stated_measure(output, q)
    assert stated.get_field("aggregation").status == "absent"
    assert with_stated_measure(stated, q) is stated  # idempotent


def test_a_stated_measure_overrides_a_different_model_read():
    q = "Who led the league in assists per game in 2019-20?"
    output = jev_output("season_leaders", sel("season", "season:2019-20"), sel("stat", "assists"),
                        sel("aggregation", "total", confidence=0.99))
    n = guard(q, output)
    assert n.status == "valid" and n.request.stat.aggregation == "per_game"


def test_career_with_no_measure_is_totals_and_both_measures_clarify():
    fields = (sel("player", "player:2544"), sel("stat", "points"), sel("aggregation", "per_game", confidence=0.99))
    n = guard("LeBron James career points", jev_output("career_stats", *fields))
    assert n.status == "valid" and n.request.stat.aggregation == "total"  # ADR 0013 default, not the model's read
    n = guard("LeBron James career total points and average", jev_output("career_stats", *fields))
    assert (n.status, n.clarify_field) == ("needs_clarification", "aggregation")


# -- the whole pipeline: clarification options answer with no model call --------------------


class Budget:
    def remaining_usd(self):
        return 1.0

    def reserve(self, model, amount):
        return object()

    def settle(self, reservation, amount):
        pass


def pipeline(tmp_path, jev, monkeypatch, *, dev=True):
    luna = Fake("luna", outcome="unavailable")
    adapter = TieredAdapter([Tier("jev", jev, 0.85), Tier("luna", luna, None)], veto_min=0.5)
    calls = []

    def resolve(request, deadline=None):
        calls.append(request)
        return fixture_output(request)

    monkeypatch.setattr("server.ask.pipeline.resolve", resolve)
    ask = AskPipeline(AskConfig(enabled=True, dev=dev, state_dir=tmp_path, api_key="fake", deadline_seconds=20),
                      lookup=CandidateLookupService(), adapter=adapter, budget=Budget(), cache=AskCache(),
                      resolutions=ResolutionStore(tmp_path / "resolutions.sqlite3"), clock=lambda: NOW)
    return ask, calls, luna


def fixture_output(request):
    name = {"season_leaders": "answer-season-leaders", "career_stats": "answer-career-totals",
            "player_season_stats": "answer-player-season-line"}[request.intent]
    known = AskResponse.model_validate_json((RESPONSES / f"{name}.json").read_text())
    return ResolverOutput(known.result, tuple(known.links), tuple(known.sources))


def jev_fake(intent, *fields):
    return Fake("jev", sel("intent", intent, confidence=1.0), *fields)


def test_leaders_without_a_measure_ask_then_the_choice_answers_without_a_model(tmp_path, monkeypatch):
    jev = jev_fake("season_leaders", sel("season", "season:2019-20", confidence=1.0),
                   sel("stat", "assists", confidence=1.0), sel("aggregation", "total", confidence=0.96),
                   absent("season_type", confidence=0.93))
    ask, calls, luna = pipeline(tmp_path, jev, monkeypatch)
    question = "Who led the league in assists in 2019-20?"
    first = ask.answer(AskQuery(question=question))
    assert first.outcome == "needs_clarification" and not calls
    assert first.clarification.field == "aggregation"
    assert [o.label for o in first.clarification.options] == ["Season totals", "Per game"]
    assert first.interpreter.field_tiers["aggregation"] == "question"
    assert first.interpreter.fallback_used is False
    for option, measure in zip(first.clarification.options, ["total", "per_game"]):
        answer = ask.answer(AskQuery(question=option.question, resolution=option.resolution))
        assert answer.outcome == "answer"
        assert calls[-1].stat.aggregation == measure and calls[-1].season == "2019-20"
    assert (jev.calls, luna.calls) == (1, 0)


# -- 2. top N above 25 is shown as the top 25 with a note ------------------------------------


def test_top_30_asks_the_measure_then_keeps_the_clamp_through_the_continuation(tmp_path, monkeypatch):
    jev = jev_fake("season_leaders", sel("season", "season:2023-24", confidence=1.0),
                   sel("stat", "points", confidence=1.0), absent("aggregation", confidence=0.9),
                   absent("season_type", confidence=0.93))
    ask, calls, _ = pipeline(tmp_path, jev, monkeypatch)
    first = ask.answer(AskQuery(question="Top 30 scorers 2023-24"))
    assert first.outcome == "needs_clarification" and first.clarification.field == "aggregation"
    option = first.clarification.options[1]
    assert option.question == "Top 30 scorers 2023-24 per game?"
    answer = ask.answer(AskQuery(question=option.question, resolution=option.resolution))
    assert answer.outcome == "answer"
    request = calls[-1]
    assert (request.limit, request.requested_limit, request.stat.aggregation) == (25, 30, "per_game")
    assert jev.calls == 1


@pytest.mark.parametrize("question,limit,requested", [
    ("Top 25 in total points in 2023-24", 25, None), ("Top 26 in total points in 2023-24", 25, 26),
    ("Top 100 in total points in 2023-24", 25, 100), ("Top 1 in total points in 2023-24", 1, None),
])
def test_top_n_above_the_maximum_is_clamped(question, limit, requested):
    output = jev_output("season_leaders", sel("season", "season:2023-24"), sel("stat", "points"))
    n = guard(question, output)
    assert n.status == "valid" and (n.request.limit, n.request.requested_limit) == (limit, requested)


def test_top_zero_stays_unsupported_and_career_top_n_clamps():
    output = jev_output("season_leaders", sel("season", "season:2023-24"), sel("stat", "points"))
    assert guard("Top 0 in total points in 2023-24", output).status == "unsupported"
    n = guard("Top 40 all-time in total blocks", jev_output("career_stats", sel("stat", "blocks")))
    assert n.status == "valid" and (n.request.view, n.request.limit, n.request.requested_limit) == ("leaders", 25, 40)


def test_clamped_leaderboards_carry_the_note(monkeypatch):
    from server.ask.resolvers import leaders
    from server.tests.ask.test_leader_tools import PROBE, install
    seasons._cache.clear()
    install(monkeypatch, PROBE["PerGame-RegularSeason-PTS-2023-24"])
    monkeypatch.setattr(leaders, "_bref_board", lambda *a: pytest.fail("no fallback"))
    base = dict(season="2023-24", stat={"stat": "points", "aggregation": "per_game"}, limit=25)
    clamped = leaders.season_leaders(SeasonLeadersRequest(**base, requested_limit=30)).result
    plain = leaders.season_leaders(SeasonLeadersRequest(**base)).result
    assert clamped.limit_note == LIMIT_NOTE == "Showing the top 25, the most Ask lists."
    assert plain.limit_note is None and [r.player for r in plain.rows] == [r.player for r in clamped.rows]
    seasons._cache.clear()


# -- 3. "LeBron's career points" --------------------------------------------------------------


def test_root_cause_loose_player_match_spanning_career_no_longer_erases_the_career_wording():
    """Before the lookup fix, "LeBron's career" was one unknown full name. The cascade
    expanded it into partial matches whose matched text covered "career"; the guard then
    masked that text and, with no career wording left, asked "Which kind of question?"."""
    q = "LeBron's career points"
    lebron = b.player(2544, "LeBron James", matched="LeBron's career", score=0.3).model_copy(update={"span": (0, 15)})
    candidates = b.lookup_result([lebron])
    output = jev_output("career_stats", sel("player", "player:2544", confidence=1.0), sel("stat", "points", confidence=1.0),
                        sel("aggregation", "total", confidence=1.0), absent("season_type", confidence=0.93))
    n = guard(q, output, candidates)
    assert n.status == "valid"
    assert (n.request.view, n.request.player.player_id, n.request.stat.stat, n.request.stat.aggregation) == (
        "player_totals", 2544, "points", "total")


@pytest.mark.parametrize("question", ["LeBron's career points", "LeBron’s career points", "lebron's career points"])
def test_possessive_name_at_the_start_is_found_without_expansion(question):
    players = CandidateLookupService().lookup(question, CONTEXT).sets["player"]
    assert [c.value.player.player_id for c in players.candidates] == [2544]
    assert players.candidates[0].matched_text.lower().startswith("lebron")
    assert "career" not in players.candidates[0].matched_text.lower()


def test_lebrons_career_points_answers_through_the_pipeline(tmp_path, monkeypatch):
    jev = jev_fake("career_stats", sel("player", "player:2544", confidence=1.0), sel("stat", "points", confidence=1.0),
                   sel("aggregation", "total", confidence=1.0), absent("season_type", confidence=0.93))
    ask, calls, _ = pipeline(tmp_path, jev, monkeypatch)
    response = ask.answer(AskQuery(question="LeBron's career points"))
    assert response.outcome == "answer"
    assert isinstance(calls[-1], CareerStatsRequest)
    assert (calls[-1].view, calls[-1].stat.aggregation) == ("player_totals", "total")


def test_intent_clarification_offers_career_and_never_the_name_or_date_hint(tmp_path):
    q = "How many points does LeBron James have?"
    candidates = CandidateLookupService().lookup(q, CONTEXT)
    output = jev_output("career_stats", sel("player", "player:2544"), sel("stat", "points"))
    n = guard(q, output, candidates)
    assert (n.status, n.clarify_field) == ("needs_clarification", "intent")
    store = ResolutionStore(tmp_path / "r.sqlite3")
    c = clarification("intent", "ambiguous", q, PendingResolution(output, candidates, CONTEXT), store)
    assert c.prompt == "Career or one season?"
    assert [o.label for o in c.options] == ["Career totals"]
    assert "name or date" not in (c.hint or "")
    chosen = store.read(c.options[0].resolution, c.options[0].question, CONTEXT)
    n = normalize_question(Normalizer(), chosen.output, chosen.candidates, CONTEXT, c.options[0].question)
    assert n.status == "valid" and n.request.view == "player_totals" and n.request.stat.aggregation == "total"
    # An intent the interpreters could not settle gets a kind-of-question hint, not a name/date one.
    unsettled = output.model_copy(update={"fields": [FieldInterpretation(
        field="intent", status="ambiguous", alternatives=["career_stats", "player_season_stats"])]})
    c = clarification("intent", "ambiguous", q, PendingResolution(unsettled, candidates, CONTEXT), store)
    assert c.options == [] and "name or date" not in c.hint


# -- 4. player season stats: per game first, totals one toggle away ---------------------------


def test_unstated_measure_for_a_player_season_is_per_game_without_clarification():
    q = "Kevin Durant stats 2015-16"
    output = jev_output("player_season_stats", sel("player", "player:201142"), sel("season", "season:2015-16"),
                        sel("stat", "stat_line"), sel("aggregation", "total", confidence=0.97))
    n = guard(q, output)
    assert n.status == "valid" and n.request.stat.aggregation == "per_game"
    n = guard("Kevin Durant total stats 2015-16", output)
    assert n.status == "valid" and n.request.stat.aggregation == "total"
    n = guard("Kevin Durant total and per game stats 2015-16", output)
    assert n.status == "valid" and n.request.stat.aggregation == "per_game"


DURANT = {"PLAYER_ID": 201142, "SEASON_ID": "2015-16", "LEAGUE_ID": "00", "TEAM_ID": 1610612760, "GP": 72,
          "PTS": 2029, "REB": 589, "OREB": 38, "DREB": 551, "AST": 361, "STL": 69, "BLK": 85, "TOV": 250, "PF": 137,
          "MIN": 2578, "FGM": 698, "FGA": 1381, "FG3M": 186, "FG3A": 481, "FTM": 447, "FTA": 498,
          "FG_PCT": 0.505, "FG3_PCT": 0.387, "FT_PCT": 0.898}


def durant_request(stat="stat_line", aggregation="per_game"):
    return PlayerSeasonStatsRequest(player={"player_id": 201142, "name": "Kevin Durant"}, season="2015-16",
                                    stat={"stat": stat, "aggregation": aggregation})


def install_row(monkeypatch, row):
    data = seasons.SeasonData((row,), "nba_stats", "https://www.nba.com/stats/player/201142/traditional?Season=2015-16",
                              dt.datetime(2026, 9, 30, tzinfo=dt.timezone.utc), True)
    monkeypatch.setattr(seasons, "_nba_player", lambda *a, **k: data)
    monkeypatch.setattr(seasons, "_bref_player", lambda *a, **k: pytest.fail("no fallback"))
    monkeypatch.setattr(seasons, "_cache", AskCache(max_entries=8, version="test"))


def test_stat_line_returns_both_measures_from_one_row(monkeypatch):
    install_row(monkeypatch, DURANT)
    result = seasons.player_season(durant_request()).result
    shown = {v.stat: v.display for v in result.values}
    other = {v.stat: v.display for v in result.alternate.values}
    assert result.aggregation == "per_game" and result.alternate.aggregation == "total"
    assert shown["points"] == "28.2" and other["points"] == "2029"
    assert shown["field_goals"] == "9.7/19.2" and other["field_goals"] == "698/1381"
    assert shown["minutes"] == "35.8" and other["minutes"] == "2578"
    # Made/attempted counts are the season totals in both measures.
    assert all(v.made == w.made and v.attempted == w.attempted for v, w in zip(result.values, result.alternate.values))


def test_explicit_totals_keep_the_toggle_and_percentages_have_none(monkeypatch):
    install_row(monkeypatch, DURANT)
    totals = seasons.player_season(durant_request("points", "total")).result
    assert (totals.values[0].display, totals.alternate.values[0].display) == ("2029", "28.2")
    percentage = seasons.player_season(durant_request("field_goal_percentage", "total")).result
    assert percentage.values[0].display == "50.5%" and percentage.alternate is None


def test_career_line_gets_the_same_toggle(monkeypatch):
    row = {"PLAYER_ID": 2544, "LEAGUE_ID": "00", "GP": 1622, "PTS": 43440, "REB": 12000, "AST": 11500, "STL": 2400,
           "BLK": 1200, "TOV": 5500, "MIN": 60000, "FGM": 15900, "FGA": 31000, "FG3M": 2600, "FG3A": 7400,
           "FTM": 9000, "FTA": 12300, "FG_PCT": 0.506, "FG3_PCT": 0.35, "FT_PCT": 0.73}
    data = career.CareerData((row,), "https://www.nba.com/stats/player/2544/career", NOW, False)
    monkeypatch.setattr(career, "_cached", lambda *a, **k: data)
    request = CareerStatsRequest(view="player_totals", player={"player_id": 2544, "name": "LeBron James"},
                                 stat={"stat": "points", "aggregation": "total"})
    result = career.career_stats(request).result
    assert (result.values[0].display, result.alternate.aggregation, result.alternate.values[0].display) == (
        "43440", "per_game", "26.8")


# -- development labels ---------------------------------------------------------------------------


def test_feedback_development_cases_hold_with_python_owned_measures():
    stage2 = json.loads((FIXTURES / "eval/stage2-dev.json").read_text())["cases"]
    stage3 = json.loads((FIXTURES / "eval/stage3-dev.json").read_text())["cases"]
    cases = {c["id"]: LabeledCase.from_json(c) for c in stage2 + stage3 if "live-feedback-2026-09-30" in c["tags"]}
    assert set(cases) == {"stage2-player_season_stats-22", "stage3-season_leaders-39", "stage3-season_leaders-40",
                          "stage3-season_leaders-41", "stage3-career_stats-42"}
    # Every model read of the measure is "total"; Python must still reach each label.
    reads = {
        "stage2-player_season_stats-22": jev_output("player_season_stats", sel("player", "player:201142"),
                                                    sel("season", "season:2015-16"), sel("stat", "stat_line"),
                                                    sel("aggregation", "total")),
        "stage3-season_leaders-39": jev_output("season_leaders", sel("season", "season:2019-20"), sel("stat", "assists"),
                                               sel("aggregation", "total")),
        "stage3-season_leaders-40": jev_output("season_leaders", sel("season", "season:2023-24"), sel("stat", "points"),
                                               sel("aggregation", "total")),
        "stage3-season_leaders-41": jev_output("season_leaders", sel("season", "season:2023-24"), sel("stat", "points"),
                                               sel("aggregation", "total")),
        "stage3-career_stats-42": jev_output("career_stats", sel("player", "player:2544"), sel("stat", "points"),
                                             sel("aggregation", "total")),
    }
    from server.ask.eval.runner import scored_request
    for case_id, case in cases.items():
        n = guard(case.question, reads[case_id])
        if case.action == "accept":
            assert n.status == "valid", case_id
            assert scored_request(n.request) == scored_request(case.request), case_id
        else:
            assert (n.status, n.clarify_field) == ("needs_clarification", case.clarify_field), case_id

