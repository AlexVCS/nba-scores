"""Offline tier gate scorer (scripts/ask/tier_gate.py), on synthetic cases and traces only."""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
from pathlib import Path
import sys

import pytest

from server.ask.eval.runner import LabeledCase

REPO = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location("tier_gate", REPO / "scripts/ask/tier_gate.py")
tg = importlib.util.module_from_spec(_spec)
sys.modules["tier_gate"] = tg  # dataclasses resolve annotations through sys.modules
_spec.loader.exec_module(tg)

REF_TIME = "2024-07-10T12:00:00-04:00"
BOS = {"team_id": 1610612738, "tricode": "BOS", "name": "Boston Celtics"}
MIA = {"team_id": 1610612748, "tricode": "MIA", "name": "Miami Heat"}
REFERENCE = tg.Reference(players=frozenset({2544, 201939}), teams=frozenset({BOS["team_id"], MIA["team_id"]}))


def case(case_id, expected, context=None):
    return LabeledCase.from_json({"id": case_id, "question": f"synthetic {case_id}", "reference_time": REF_TIME,
                                  "context": context or {}, "expected": expected})


def game_search(case_id="syn-game_search-01", teams=(BOS,)):
    return case(case_id, {"action": "accept", "request": {
        "intent": "game_search", "dates": {"start": "2024-01-02", "end": "2024-01-02"}, "teams": list(teams)}})


def cand(cid, field, value, source="team_catalog"):
    return {"id": cid, "field": field, "label": cid, "source": source, "match_score": 1.0, "value": value}


def candidates(**sets):
    out = {}
    for name in ("player", "team", "date", "season", "round", "game_number", "location"):
        items = sets.get(name, [])
        out[name] = {"field": name, "status": "candidates" if items else "not_mentioned", "candidates": items}
    return {"sets": out, "alias_version": "test", "latency_ms": 0}


TEAM_BOS = cand("team:bos", "team", {"kind": "team", "team": BOS})
TEAM_MIA = cand("team:mia", "team", {"kind": "team", "team": MIA})
DATE_0 = cand("date:0", "date", {"kind": "date", "components": {"kind": "calendar_date", "year": 2024, "month": 1,
                                                                   "day": 2},
                                 "resolved": {"start": "2024-01-02", "end": "2024-01-02"}}, "date_parser")


def read(field, status="selected", selected=(), confidence=1.0, alternatives=()):
    return {"field": field, "status": status, "selected": list(selected), "alternatives": list(alternatives),
            "confidence": confidence, "mention": None}


def output(*fields, outcome="interpreted", reason=None, model="jev-1.13.0"):
    return {"outcome": outcome, "fields": list(fields), "unsupported_reason": reason, "extracted_date": None,
            "error_code": "boom" if outcome == "unavailable" else None,
            "metadata": {"adapter": "jev", "provider": "typesafe", "model": model, "latency_ms": 1}}


def row(case_id, cands, jev, luna=None, field_tiers=None):
    tiers = [{"tier": "jev", "output": jev}] + ([{"tier": "luna", "output": luna}] if luna else [])
    return {"case_id": case_id, "candidates": cands, "tier_outputs": tiers,
            "attempts": [{"output": {"outcome": "interpreted", "metadata": {"field_tiers": field_tiers or {}}}}]}


def run(cases, rows, labels=None):
    cases = {c.id: c for c in cases}
    plans = {cid: tg.plan(c) for cid, c in cases.items()}
    if labels is not None:
        tg.apply_labels(plans, labels, REFERENCE)
    return plans, tg.score_tier("jev", 0.85, cases, plans, {r["case_id"]: r for r in rows})


# -- gold derivation ----------------------------------------------------------------------------


def test_accept_labels_pin_fields_except_player_outside_player_scope():
    c = case("syn-boxscore_stat-01", {"action": "accept", "request": {
        "intent": "boxscore_stat", "scope": "team", "stat": {"stat": "points"},
        "game": {"date": "2024-01-02", "teams": [BOS]}, "team": BOS}})
    p = tg.plan(c)
    assert p.label_scope == "player" and "player" not in p.gold
    assert p.gold["teams"] == [tg.Gold("value", frozenset({BOS["team_id"]}))]
    assert p.gold["season"] == [tg.ABSENT] and p.gold["round"] == [tg.ABSENT]


def test_unsupported_intent_is_mechanical_only_for_interpreter_reasons():
    standings = tg.plan(case("syn-game_search-02", {"action": "unsupported", "unsupported_reason": "standings"}))
    assert standings.label_scope is None and standings.scored_intent == "unsupported"
    average = tg.plan(case("syn-playoff_series-01",
                           {"action": "unsupported", "unsupported_reason": "multi_game_average"}))
    clarify = tg.plan(case("syn-game_search-03", {"action": "clarify", "clarify_field": "date",
                                                  "clarify_reason": "missing"}))
    assert average.label_scope == clarify.label_scope == "all"


# -- acceptance and correctness -------------------------------------------------------------------


def test_threshold_accepts_any_status_and_escalates_the_rest():
    c = game_search()
    r = row(c.id, candidates(team=[TEAM_BOS], date=[DATE_0]),
            output(read("intent", selected=["game_search"]), read("date", selected=["date:0"], confidence=0.85),
                   read("teams", selected=["team:mia"], confidence=0.84)),
            luna=output(read("teams", selected=["team:bos"], confidence=None), model="gpt-6-luna"))
    _, scored = run([c], [r])
    by = {s.field: s for s in scored}
    assert set(by) == {"intent", "date", "teams"}  # location not mentioned: lookup decides it
    assert by["date"].disposition == "accepted" and by["date"].correct
    assert by["teams"].disposition == "escalated"
    gate = tg.gate(scored)
    assert (gate["accepted"], gate["eligible"], gate["precision"]) == (2, 3, 1.0)


def test_wrong_confident_team_is_an_accepted_error():
    c = game_search()
    r = row(c.id, candidates(team=[TEAM_BOS, TEAM_MIA], date=[DATE_0]),
            output(read("intent", selected=["game_search"]), read("date", selected=["date:0"]),
                   read("teams", selected=["team:mia"], confidence=0.9)))
    _, scored = run([c], [r])
    errors = tg.error_rows(scored)
    assert [(e["field"], e["error_kind"]) for e in errors] == [("teams", "value_vs_value")]


def test_absent_read_takes_lone_page_candidate_like_the_normalizer():
    c = game_search(teams=())
    page_date = {**DATE_0, "source": "app_context"}
    r = row(c.id, candidates(date=[page_date]),
            output(read("intent", selected=["game_search"]), read("date", status="absent"),
                   read("teams", status="absent")))
    _, scored = run([c], [r])
    assert all(s.correct for s in scored)


def test_no_matching_candidate_is_correct_only_when_gold_is_not_offered():
    c = game_search()
    miss = row(c.id, candidates(date=[DATE_0]),
               output(read("intent", selected=["game_search"]), read("date", selected=["date:0"]),
                      read("teams", status="no_matching_candidate")))
    offered = row(c.id, candidates(team=[TEAM_BOS], date=[DATE_0]), miss["tier_outputs"][0]["output"])
    assert next(s for s in run([c], [miss])[1] if s.field == "teams").correct
    assert not next(s for s in run([c], [offered])[1] if s.field == "teams").correct


def test_unsupported_outcome_is_an_accepted_intent_and_unavailable_is_escalated():
    standings = case("syn-game_search-02", {"action": "unsupported", "unsupported_reason": "standings"})
    other = case("syn-game_search-03", {"action": "unsupported", "unsupported_reason": "prediction"})
    down = game_search("syn-game_search-04")
    rows = [row(standings.id, candidates(), output(outcome="unsupported", reason="standings")),
            row(other.id, candidates(), output(outcome="unsupported", reason="other")),
            row(down.id, candidates(), output(outcome="unavailable"),
                luna=output(read("intent", selected=["game_search"], confidence=None), model="gpt-6-luna"))]
    _, scored = run([standings, other, down], rows)
    intents = {s.case_id: s for s in scored if s.field == "intent"}
    assert intents[standings.id].disposition == "accepted" and intents[standings.id].correct
    assert intents[other.id].disposition == "accepted" and not intents[other.id].correct
    assert {s.disposition for s in scored if s.case_id == down.id} == {"escalated"}


def test_normalizer_defaults_for_stat_and_aggregation():
    c = case("syn-boxscore_stat-02", {"action": "accept", "request": {
        "intent": "boxscore_stat", "scope": "player", "stat": {"stat": "stat_line"},
        "game": {"date": "2024-01-02"}, "player": {"player_id": 2544, "name": "LeBron James"}}})
    player = cand("player:2544", "player", {"kind": "player", "player": {"player_id": 2544, "name": "LeBron James"}},
                  "player_catalog")
    r = row(c.id, candidates(player=[player], date=[DATE_0]),
            output(read("intent", selected=["boxscore_stat"]), read("stat_scope", selected=["player"]),
                   read("stat", status="absent"), read("aggregation", status="absent"),
                   read("player", selected=["player:2544"]), read("teams", status="absent"),
                   read("date", selected=["date:0"]), read("season", status="absent"),
                   read("round", status="absent"), read("game_number", status="absent")))
    _, scored = run([c], [r])
    assert len(scored) == 10 and all(s.correct for s in scored)


def test_labeled_ambiguity_and_any_of():
    c = case("syn-postseason_summary-01", {"action": "clarify", "clarify_field": "teams",
                                           "clarify_reason": "ambiguous"})
    labels = {"schema": tg.LABEL_SCHEMA, "cases": [{
        "case_id": c.id, "intent": {"status": "value", "value": "postseason_summary"},
        "scored_intent": "postseason_summary",
        "fields": {"teams": {"status": "ambiguous", "alternatives": [BOS["team_id"], MIA["team_id"]]},
                   "season": {"any_of": [{"status": "value", "value": "2011-12"}, {"status": "absent"}],
                              "note": "synthetic"}}}]}
    r = row(c.id, candidates(team=[TEAM_BOS, TEAM_MIA]),
            output(read("intent", selected=["postseason_summary"]),
                   read("teams", status="ambiguous", alternatives=["team:bos", "team:mia"]),
                   read("season", status="absent")))
    plans, scored = run([c], [r], labels)
    assert all(s.correct and s.source == "labeled" for s in scored)
    assert plans[c.id].notes == {"season": "synthetic"}
    guess = row(c.id, r["candidates"], output(read("intent", selected=["postseason_summary"]),
                                              read("teams", selected=["team:bos"]), read("season", status="absent")))
    _, scored = run([c], [guess], labels)
    assert not next(s for s in scored if s.field == "teams").correct


@pytest.mark.parametrize("mutate, message", [
    (lambda row: row.update(case_id="other"), "exactly"),
    (lambda row: row["fields"].pop("season"), "needs exactly fields"),
    (lambda row: row["fields"].update(teams={"status": "value", "value": [1]}), "franchise_history"),
    (lambda row: row["fields"].update(season={"any_of": [{"status": "absent"}, {"status": "absent"}]}), "note"),
    (lambda row: row.update(scored_intent="game_search"), "acceptable intents"),
    (lambda row: row["fields"].update(season=None), "not labeled"),
])
def test_invalid_labels_are_rejected(mutate, message):
    c = case("syn-postseason_summary-01", {"action": "clarify", "clarify_field": "season",
                                           "clarify_reason": "missing"})
    label = {"case_id": c.id, "intent": {"status": "value", "value": "postseason_summary"},
             "scored_intent": "postseason_summary",
             "fields": {"teams": {"status": "value", "value": [BOS["team_id"]]}, "season": {"status": "absent"}}}
    mutate(label)
    with pytest.raises(ValueError, match=message):
        tg.apply_labels({c.id: tg.plan(c)}, {"schema": tg.LABEL_SCHEMA, "cases": [label]}, REFERENCE)


def test_label_warnings_flag_disagreement_with_clarify_label():
    c = case("syn-postseason_summary-01", {"action": "clarify", "clarify_field": "season",
                                           "clarify_reason": "missing"})
    plans = {c.id: tg.plan(c)}
    tg.apply_labels(plans, {"schema": tg.LABEL_SCHEMA, "cases": [{
        "case_id": c.id, "intent": {"status": "value", "value": "postseason_summary"},
        "scored_intent": "postseason_summary",
        "fields": {"teams": {"status": "absent"}, "season": {"status": "value", "value": "2011-12"}}}]}, REFERENCE)
    assert tg.label_warnings({c.id: c}, plans) == [f"{c.id}: clarify season/missing labeled ['value']"]


# -- gate arithmetic -----------------------------------------------------------------------------


def items(accepted_correct, accepted_wrong, escalated):
    make = lambda disposition, correct: tg.Scored("c", "game_search", "teams", "mechanical", disposition, None,
                                                  0.9, correct)
    return ([make("accepted", True)] * accepted_correct + [make("accepted", False)] * accepted_wrong
            + [make("escalated", None)] * escalated)


def test_gate_pass_fail_and_provisional():
    solid = tg.gate(items(196, 2, 200))  # 98.99% precision, 49.7% coverage, slack 1
    assert solid["passed"] and not solid["provisional"] and solid["error_slack"] == 1
    edge = tg.gate(items(147, 3, 350))  # exactly 98%, 30% coverage
    assert edge["passed"] and edge["provisional"] and edge["error_slack"] == 0
    assert not tg.gate(items(146, 4, 350))["precision_passed"]
    assert not tg.gate(items(100, 0, 301))["coverage_passed"]


def test_cascade_crosscheck_rejects_a_rule_disagreement():
    c = game_search()
    jev = output(read("intent", selected=["game_search"]), read("date", selected=["date:0"], confidence=0.8),
                 read("teams", selected=["team:bos"]))
    good = row(c.id, candidates(team=[TEAM_BOS], date=[DATE_0]), jev,
               field_tiers={"intent": "jev", "date": "luna", "teams": "jev", "location": "lookup"})
    _, scored = run([c], [good])
    tg.check_cascade("jev", 0.85, {c.id: good}, scored)
    bad = {**good, "attempts": [{"output": {"outcome": "interpreted", "metadata": {"field_tiers": {"date": "jev"}}}}]}
    with pytest.raises(tg.IntegrityError, match="below the threshold"):
        tg.check_cascade("jev", 0.85, {c.id: bad}, scored)
    # A later unsupported outcome replaces Jev's accepted intent; that is cascade behavior.
    overridden = {**good, "attempts": [{"output": {"outcome": "unsupported",
                                                   "metadata": {"field_tiers": {"intent": "luna"}}}}]}
    tg.check_cascade("jev", 0.85, {c.id: overridden}, scored)
    credited = {**good, "attempts": [{"output": {"outcome": "interpreted",
                                                 "metadata": {"field_tiers": {"intent": "luna"}}}}]}
    with pytest.raises(tg.IntegrityError, match="credited to luna"):
        tg.check_cascade("jev", 0.85, {c.id: credited}, scored)


# -- frozen inputs and outputs ------------------------------------------------------------------------


def test_verify_rejects_changed_inputs(tmp_path):
    paths = frozen_set(tmp_path)
    with pytest.raises(tg.IntegrityError, match="frozen inputs changed"):
        tg.verify(paths, tmp_path, {paths.journal: "0" * 64})


def test_score_refuses_to_overwrite(tmp_path):
    out = tmp_path / "report.json"
    out.write_text("{}")
    with pytest.raises(FileExistsError):
        tg.main(["score", "--report", str(tmp_path / "report.json"), "--labels", str(tmp_path / "labels.json"),
                 "--out", str(out)])
    with pytest.raises(FileExistsError):
        tg.write_exclusive(out, {})


def test_template_carries_no_trace_content():
    cases = {c.id: c for c in (
        game_search(),
        case("syn-game_search-05", {"action": "clarify", "clarify_field": "date", "clarify_reason": "missing"},
             context={"route": "scores", "view_date": "2024-01-02"}),
    )}
    doc = tg.template(cases)
    assert [c["case_id"] for c in doc["cases"]] == ["syn-game_search-05"]
    assert doc["cases"][0]["context"] == {"route": "scores", "view_date": "2024-01-02"}
    text = json.dumps(doc)
    for leaked in ("confidence", "candidates", "tier_outputs", "expected", "jev", "luna"):
        assert leaked not in text
    assert dt.date.fromisoformat(doc["cases"][0]["context"]["view_date"])


def test_report_assembles_and_serializes():
    c = game_search()
    r = row(c.id, candidates(team=[TEAM_BOS], date=[DATE_0]),
            output(read("intent", selected=["game_search"]), read("date", selected=["date:0"]),
                   read("teams", selected=["team:bos"], confidence=0.5)),
            luna=output(read("teams", selected=["team:bos"], confidence=None), model="gpt-6-luna"),
            field_tiers={"intent": "jev", "date": "jev", "teams": "luna", "location": "lookup"})
    doc = tg.build_report({c.id: c}, {c.id: tg.plan(c)}, {c.id: r}, {"synthetic": "0"})
    gate = doc["tiers"]["jev"]["gate"]
    assert (gate["eligible"], gate["accepted"], gate["escalated"]) == (3, 2, 1)
    assert doc["tiers"]["luna"]["correct"] == 1
    assert doc["gold_inventory"]["totals"] == {"mechanical": 3, "labeled": 0, "lookup_decided": 1,
                                               "question_decided": 0}
    json.dumps(doc)


# -- the eight-tool field definition (label schema 2) -----------------------------------------------

CURRY = {"player_id": 201939, "name": "Stephen Curry"}
PLAYER_CURRY = cand("player:201939", "player", {"kind": "player", "player": CURRY}, "player_catalog")
SEASON_15 = cand("season:0", "season", {"kind": "season", "season": "2015-16"}, "pattern")


def accept(case_id, request):
    return case(case_id, {"action": "accept", "request": request})


def player_season(case_id="syn-player_season_stats-01"):
    return accept(case_id, {"intent": "player_season_stats", "player": CURRY, "season": "2015-16",
                            "stat": {"stat": "three_pointers", "aggregation": "per_game"}})


def test_season_family_accept_gold_excludes_python_decided_fields():
    pss = tg.plan(player_season())
    assert pss.label_scope is None
    assert pss.fields() == ["intent", "stat", "season_type", "player", "teams", "season"]
    assert pss.gold["season_type"] == [tg.Gold("value", "regular_season")] and pss.gold["teams"] == [tg.ABSENT]
    assert "aggregation" not in pss.gold  # measure.py decides it (QUESTION_TIER)

    records = tg.plan(accept("syn-team_records-01", {"intent": "team_records", "season": "2023-24",
                                                    "standings_scope": "east"}))
    assert records.fields() == ["intent", "season_type", "standings_scope", "teams", "season"]
    assert records.gold["standings_scope"] == [tg.Gold("value", "east")] and records.gold["teams"] == [tg.ABSENT]

    leaders = tg.plan(accept("syn-season_leaders-01", {
        "intent": "season_leaders", "season": "2019-20", "season_type": "playoffs",
        "stat": {"stat": "assists", "aggregation": "per_game"}, "limit": 5}))
    assert leaders.fields() == ["intent", "stat", "season_type", "season"]  # limit is not a field
    assert leaders.gold["season_type"] == [tg.Gold("value", "playoffs")] and tg.stat_default(leaders) == tg.NO_STAT

    all_time = tg.plan(accept("syn-career_stats-01", {"intent": "career_stats", "view": "leaders",
                                                     "stat": {"stat": "assists"}}))
    assert all_time.fields() == ["intent", "stat", "season_type", "player"]  # view is not a field
    assert all_time.gold["player"] == [tg.ABSENT] and tg.stat_default(all_time) == tg.NO_STAT
    rank = tg.plan(accept("syn-career_stats-02", {"intent": "career_stats", "view": "player_rank", "player": CURRY,
                                                 "stat": {"stat": "three_pointers"}}))
    assert rank.gold["player"] == [tg.Gold("value", 201939)] and tg.stat_default(rank) == "stat_line"


def test_team_scope_boxscore_gold_has_target_team():
    def team_scope(case_id, target, named):
        return accept(case_id, {"intent": "boxscore_stat", "scope": "team", "stat": {"stat": "points"},
                                "game": {"date": "2024-01-02", "teams": named}, "team": target})

    one = tg.plan(team_scope("syn-boxscore_stat-03", BOS, [BOS]))
    assert one.gold["target_team"] == [tg.Gold("value", BOS["team_id"]), tg.ABSENT]  # lone team fills it
    assert "target_team" in one.fields() and one.label_scope == "player"
    two = tg.plan(team_scope("syn-boxscore_stat-04", MIA, [BOS, MIA]))
    assert two.gold["target_team"] == [tg.Gold("value", MIA["team_id"])]
    leaders = tg.plan(accept("syn-boxscore_stat-05", {"intent": "boxscore_stat", "scope": "leaders",
                                                     "stat": {"stat": "points"}, "game": {"date": "2024-01-02"}}))
    assert "target_team" not in leaders.fields()
    legacy = tg.plan(team_scope("syn-boxscore_stat-03", BOS, [BOS]), tg.V1)
    assert "target_team" not in legacy.gold and "target_team" not in legacy.fields()


def test_python_produced_unsupported_reasons_need_a_labeled_intent():
    other = case("syn-season_leaders-02", {"action": "unsupported", "unsupported_reason": "other"})
    assert tg.plan(other).label_scope == "all"  # season-scope guards produce `other`
    assert tg.plan(case("syn-game_search-06", {"action": "unsupported", "unsupported_reason": "other"}),
                   tg.V1).label_scope is None
    biography = tg.plan(case("syn-career_stats-03", {"action": "unsupported",
                                                     "unsupported_reason": "reference_question"}))
    assert biography.label_scope is None and biography.gold["intent"] == [
        tg.Gold("value", "unsupported:reference_question")]


def test_measured_aggregation_is_not_scored_and_season_defaults_apply():
    c = player_season()
    r = row(c.id, candidates(player=[PLAYER_CURRY], season=[SEASON_15]),
            output(read("intent", selected=["player_season_stats"]), read("player", selected=["player:201939"]),
                   read("season", selected=["season:0"]), read("stat", selected=["three_pointers"]),
                   read("aggregation", selected=["total"]),  # wrong, but Python replaces it
                   read("season_type", status="absent"), read("teams", status="absent")),
            field_tiers={"intent": "jev", "player": "jev", "season": "jev", "stat": "jev", "season_type": "jev",
                         "teams": "jev", "aggregation": "question"})
    _, scored = run([c], [r])
    assert {s.field for s in scored} == {"intent", "player", "season", "stat", "season_type", "teams"}
    assert all(s.correct and s.disposition == "accepted" for s in scored)
    tg.check_cascade("jev", 0.85, {c.id: r}, scored)


def test_absent_reads_against_normalizer_defaults():
    cands = tg.CandidateLookupResult.model_validate(candidates())
    league, east = [tg.Gold("value", "league")], [tg.Gold("value", "east")]
    assert tg.judge("standings_scope", "absent", None, league, cands, None)[0]
    assert not tg.judge("standings_scope", "absent", None, east, cands, None)[0]
    assert tg.judge("season_type", "absent", None, [tg.ABSENT], cands, None)[0]
    assert tg.judge("season_type", "value", "regular_season", [tg.ABSENT], cands, None)[0]
    assert not tg.judge("season_type", "absent", None, [tg.Gold("value", "playoffs")], cands, None)[0]
    stat_line = [tg.Gold("value", "stat_line")]
    assert tg.judge("stat", "absent", None, stat_line, cands, "stat_line")[0]  # a career with a player
    assert not tg.judge("stat", "absent", None, [tg.Gold("value", "assists")], cands, None)[0]  # leaders


def test_lookup_decided_target_team_is_excluded_and_cross_checked():
    c = accept("syn-boxscore_stat-06", {"intent": "boxscore_stat", "scope": "team", "stat": {"stat": "points"},
                                        "game": {"date": "2024-01-02", "teams": [BOS]}, "team": BOS})
    plans = {c.id: tg.plan(c)}
    plans[c.id].gold["player"], plans[c.id].sources["player"] = [tg.ABSENT], "labeled"
    r = row(c.id, candidates(date=[DATE_0]), output(read("intent", selected=["boxscore_stat"])),
            field_tiers={"intent": "jev", "target_team": "lookup"})
    scored = tg.score_tier("jev", 0.85, {c.id: c}, plans, {c.id: r})
    assert "target_team" not in {s.field for s in scored}
    tg.check_cascade("jev", 0.85, {c.id: r}, scored)
    named = row(c.id, candidates(team=[TEAM_BOS], date=[DATE_0]), r["tier_outputs"][0]["output"],
                field_tiers={"target_team": "lookup"})
    with pytest.raises(tg.IntegrityError, match="lookup-decided with candidates"):
        tg.check_cascade("jev", 0.85, {c.id: named}, scored)


def test_a_later_absent_read_may_replace_an_unfounded_no_match():
    c = game_search(teams=())
    jev = output(read("intent", selected=["game_search"]), read("date", selected=["date:0"]),
                 read("teams", status="no_matching_candidate", confidence=0.92))
    r = row(c.id, candidates(date=[DATE_0]), jev, luna=output(read("teams", status="absent")),
            field_tiers={"intent": "jev", "date": "jev", "teams": "luna", "location": "lookup"})
    _, scored = run([c], [r])
    tg.check_cascade("jev", 0.85, {c.id: r}, scored)  # TieredAdapter._unfounded_no_match
    teams = next(s for s in scored if s.field == "teams")
    assert teams.disposition == "accepted" and not teams.correct  # still Jev's own accepted reading
    named = {**r, "candidates": candidates(team=[TEAM_MIA], date=[DATE_0])}
    with pytest.raises(tg.IntegrityError, match="credited to luna"):
        tg.check_cascade("jev", 0.85, {c.id: named}, scored)


def test_expanded_rows_are_scored_on_the_last_attempt_and_its_candidates():
    c = game_search()
    narrow, wide = candidates(team=[TEAM_MIA], date=[DATE_0]), candidates(team=[TEAM_MIA, TEAM_BOS], date=[DATE_0])
    first = output(read("intent", selected=["game_search"]), read("date", selected=["date:0"]),
                   read("teams", status="no_matching_candidate"))
    second = output(read("intent", selected=["game_search"]), read("date", selected=["date:0"]),
                    read("teams", selected=["team:bos"]))
    r = row(c.id, narrow, first, field_tiers={"intent": "jev", "date": "jev", "teams": "jev", "location": "lookup"})
    r["tier_outputs"] = [{"tier": "jev", "output": first, "candidates": narrow},
                         {"tier": "jev", "output": second, "candidates": wide}]
    _, scored = run([c], [r])
    teams = next(s for s in scored if s.field == "teams")
    assert teams.correct and teams.reading["selected"] == ["team:bos"]
    tg.check_cascade("jev", 0.85, {c.id: r}, scored)
    r["tier_outputs"] = [{"tier": "jev", "output": first}, {"tier": "jev", "output": second}]
    with pytest.raises(tg.IntegrityError, match="without per-attempt candidates"):
        run([c], [r])


def test_a_shorter_later_attempt_is_not_mixed_with_the_earlier_one():
    narrow, wide = candidates(team=[TEAM_MIA], date=[DATE_0]), candidates(team=[TEAM_MIA, TEAM_BOS], date=[DATE_0])
    first = output(read("intent", selected=["game_search"]), read("date", selected=["date:0"]),
                   read("teams", status="no_matching_candidate", confidence=0.4))
    luna = output(read("teams", status="no_matching_candidate"))
    second = output(read("intent", selected=["game_search"]), read("date", selected=["date:0"]),
                    read("teams", selected=["team:bos"]))
    r = {"case_id": "x", "candidates": narrow,
         "tier_outputs": [{"tier": "jev", "output": first, "candidates": narrow},
                          {"tier": "luna", "output": luna, "candidates": narrow},
                          {"tier": "jev", "output": second, "candidates": wide}]}
    records, cands = tg.final_attempt(r)
    assert [(x["tier"], x["output"]) for x in records] == [("jev", second)] and cands == wide
    assert tg._tier_record(r, "luna") is None


def test_absent_teams_is_correct_when_the_target_names_the_lone_team():
    c = accept("syn-boxscore_stat-07", {"intent": "boxscore_stat", "scope": "team", "stat": {"stat": "points"},
                                        "game": {"date": "2024-01-02", "teams": [BOS]}, "team": BOS})
    plans = {c.id: tg.plan(c)}
    plans[c.id].gold["player"], plans[c.id].sources["player"] = [tg.ABSENT], "labeled"

    def teams_correct(target):
        r = row(c.id, candidates(team=[TEAM_BOS, TEAM_MIA], date=[DATE_0]),
                output(read("intent", selected=["boxscore_stat"]), read("teams", status="absent"), target))
        scored = tg.score_tier("jev", 0.85, {c.id: c}, plans, {c.id: r})
        return next(s for s in scored if s.field == "teams").correct

    assert teams_correct(read("target_team", selected=["team:bos"]))
    assert not teams_correct(read("target_team", selected=["team:mia"]))
    assert not teams_correct(read("target_team", status="absent"))  # the normalizer asks which team


def test_stat_line_equals_absent_on_leaders_lists_only():
    cands = tg.CandidateLookupResult.model_validate(candidates())
    assert tg.judge("stat", "value", "stat_line", [tg.ABSENT], cands, tg.NO_STAT)[0]
    assert tg.judge("stat", "absent", None, [tg.ABSENT], cands, tg.NO_STAT)[0]
    assert not tg.judge("stat", "value", "points", [tg.ABSENT], cands, tg.NO_STAT)[0]
    assert not tg.judge("stat", "value", "stat_line", [tg.ABSENT], cands, None)[0]  # boxscore leaders


def test_target_team_clarification_is_not_a_label_warning():
    c = case("syn-boxscore_stat-08", {"action": "clarify", "clarify_field": "teams", "clarify_reason": "ambiguous"})
    plans = {c.id: tg.plan(c)}
    both = [BOS["team_id"], MIA["team_id"]]
    tg.apply_labels(plans, {"schema": tg.LABEL_SCHEMA, "cases": [boxscore_label(
        c.id, stat_scope={"status": "value", "value": "team"}, teams={"status": "value", "value": both},
        target_team={"status": "ambiguous", "alternatives": both})]}, REFERENCE)
    assert tg.label_warnings({c.id: c}, plans) == []


def boxscore_label(case_id, **fields):
    base = {"stat_scope": {"status": "value", "value": "team"}, "stat": {"status": "value", "value": "points"},
            "aggregation": {"status": "value", "value": "total"}, "player": {"status": "absent"},
            "teams": {"status": "value", "value": [BOS["team_id"], MIA["team_id"]]},
            "date": {"status": "value", "value": {"start": "2024-01-02", "end": "2024-01-02"}},
            "season": {"status": "absent"}, "round": {"status": "absent"}, "game_number": {"status": "absent"}}
    return {"case_id": case_id, "intent": {"status": "value", "value": "boxscore_stat"},
            "scored_intent": "boxscore_stat", "fields": {**base, **fields}}


def test_labels_need_target_team_only_for_team_scope():
    c = case("syn-boxscore_stat-07", {"action": "clarify", "clarify_field": "teams", "clarify_reason": "ambiguous"})
    labels = lambda row: {"schema": tg.LABEL_SCHEMA, "cases": [row]}
    with pytest.raises(ValueError, match="needs exactly fields"):
        tg.apply_labels({c.id: tg.plan(c)}, labels(boxscore_label(c.id)), REFERENCE)
    plans = {c.id: tg.plan(c)}
    tg.apply_labels(plans, labels(boxscore_label(c.id, target_team={
        "status": "ambiguous", "alternatives": [BOS["team_id"], MIA["team_id"]]})), REFERENCE)
    assert "target_team" in plans[c.id].fields()
    player_scope = boxscore_label(c.id, stat_scope={"status": "value", "value": "player"},
                                  target_team={"status": "absent"})
    with pytest.raises(ValueError, match="needs exactly fields"):
        tg.apply_labels({c.id: tg.plan(c)}, labels(player_scope), REFERENCE)


def test_labels_never_carry_python_decided_aggregation():
    c = case("syn-season_leaders-03", {"action": "clarify", "clarify_field": "aggregation",
                                       "clarify_reason": "ambiguous"})
    fields = {"stat": {"status": "value", "value": "steals"}, "season_type": {"status": "absent"},
              "season": {"status": "value", "value": "2016-17"}}
    row_ = {"case_id": c.id, "intent": {"status": "value", "value": "season_leaders"},
            "scored_intent": "season_leaders", "fields": {**fields, "aggregation": {"status": "absent"}}}
    with pytest.raises(ValueError, match="needs exactly fields"):
        tg.apply_labels({c.id: tg.plan(c)}, {"schema": tg.LABEL_SCHEMA, "cases": [row_]}, REFERENCE)
    plans = {c.id: tg.plan(c)}
    tg.apply_labels(plans, {"schema": tg.LABEL_SCHEMA, "cases": [{**row_, "fields": fields}]}, REFERENCE)
    assert tg.label_warnings({c.id: c}, plans) == []  # aggregation is Python's, so nothing to disagree with
    with pytest.raises(ValueError, match="schema must be"):
        legacy = game_search()
        tg.apply_labels({legacy.id: tg.plan(legacy, tg.V1)}, {"schema": tg.LABEL_SCHEMA, "cases": []}, REFERENCE)


def test_intent_clarification_wants_two_intents():
    c = case("syn-career_stats-04", {"action": "clarify", "clarify_field": "intent", "clarify_reason": "ambiguous"})
    fields = {"stat": {"status": "value", "value": "blocks"}, "season_type": {"status": "absent"},
              "player": {"status": "value", "value": 201939}}
    one = {"case_id": c.id, "intent": {"status": "value", "value": "career_stats"}, "scored_intent": "career_stats",
           "fields": fields}
    plans = {c.id: tg.plan(c)}
    tg.apply_labels(plans, {"schema": tg.LABEL_SCHEMA, "cases": [one]}, REFERENCE)
    assert tg.label_warnings({c.id: c}, plans) == [f"{c.id}: clarify intent/ambiguous labeled with one intent"]
    both = {**one, "intent": {"any_of": [{"status": "value", "value": "career_stats"},
                                         {"status": "value", "value": "player_season_stats"}], "note": "synthetic"}}
    plans = {c.id: tg.plan(c)}
    tg.apply_labels(plans, {"schema": tg.LABEL_SCHEMA, "cases": [both]}, REFERENCE)
    assert tg.label_warnings({c.id: c}, plans) == []


# -- gated tiers -----------------------------------------------------------------------------------------

JEV_ONLY = {"jev_model": "jev-1.13.0", "jev_accept_min": 0.85, "laya_base_url": None}


def test_gated_tiers_come_from_the_frozen_configuration():
    assert [t.name for t in tg.gated_tiers(JEV_ONLY)] == ["jev"]
    with_laya = {**JEV_ONLY, "laya_base_url": "http://laya", "laya_accept_min": 0.9}
    assert [(t.name, t.accept_min) for t in tg.gated_tiers(with_laya)] == [("laya", 0.9), ("jev", 0.85)]
    with pytest.raises(tg.IntegrityError, match="laya_accept_min"):
        tg.gated_tiers({**JEV_ONLY, "laya_base_url": "http://laya"})


def test_laya_is_gated_first_and_jev_on_fields_laya_escalated():
    c = game_search()
    laya = output(read("intent", selected=["game_search"]), read("date", selected=["date:0"], confidence=0.95),
                  read("teams", selected=["team:bos"], confidence=0.5), model="laya")
    jev = output(read("intent", selected=["game_search"]), read("date", selected=["date:0"]),
                 read("teams", selected=["team:bos"], confidence=0.9))
    r = {"case_id": c.id, "candidates": candidates(team=[TEAM_BOS], date=[DATE_0]),
         "tier_outputs": [{"tier": "laya", "output": laya}, {"tier": "jev", "output": jev}],
         "attempts": [{"output": {"outcome": "interpreted", "metadata": {"field_tiers": {
             "intent": "laya", "date": "laya", "teams": "jev", "location": "lookup"}}}}]}
    tiers = tg.gated_tiers({**JEV_ONLY, "laya_base_url": "http://laya", "laya_accept_min": 0.9})
    doc = tg.build_report({c.id: c}, {c.id: tg.plan(c)}, {c.id: r}, {}, tiers)
    assert (doc["tiers"]["laya"]["gate"]["eligible"], doc["tiers"]["laya"]["gate"]["accepted"]) == (3, 2)
    assert (doc["tiers"]["jev"]["gate"]["eligible"], doc["tiers"]["jev"]["gate"]["accepted"]) == (1, 1)
    assert [t["name"] for t in doc["tier"]] == ["laya", "jev"]
    assert not any("Laya is disabled" in s for s in doc["scope_limits"])


# -- set paths and the command line --------------------------------------------------------------------------


def raw_case(case_id="syn-game_search-01"):
    return {"id": case_id, "question": f"synthetic {case_id}", "reference_time": REF_TIME, "context": {},
            "expected": {"action": "accept", "request": {
                "intent": "game_search", "dates": {"start": "2024-01-02", "end": "2024-01-02"}, "teams": [BOS]}}}


def frozen_set(root, journal_hash=True):
    """A synthetic release run laid out as scripts/ask/release.py writes it."""
    raw = raw_case()
    (root / "cases.json").write_text(json.dumps({"cases": [raw]}))
    jev = output(read("intent", selected=["game_search"]), read("date", selected=["date:0"]),
                 read("teams", selected=["team:bos"]))
    journal_row = row(raw["id"], candidates(team=[TEAM_BOS], date=[DATE_0]), jev,
                      field_tiers={"intent": "jev", "date": "jev", "teams": "jev", "location": "lookup"})
    (root / "run.jsonl").write_text(json.dumps(journal_row) + "\n")
    cases_sha = tg.digest(root / "cases.json")
    (root / "manifest.json").write_text(json.dumps({"cases_file": "cases.json", "cases_sha256": cases_sha,
                                                   "configuration": JEV_ONLY}))
    report = {"manifest_file": "manifest.json", "manifest_sha256": tg.digest(root / "manifest.json"),
              "cases_sha256": cases_sha, "configuration": JEV_ONLY, "cases": [{"case_id": raw["id"]}]}
    if journal_hash:
        report.update(journal_file="run.jsonl", journal_sha256=tg.digest(root / "run.jsonl"))
    (root / "run.json").write_text(json.dumps(report))
    return tg.resolve_paths(str(root / "run.json"), root=root)


def test_paths_come_from_the_report_and_are_verified(tmp_path):
    paths = frozen_set(tmp_path)
    assert paths == tg.SetPaths("cases.json", "manifest.json", "run.jsonl", "run.json")
    hashes, tiers = tg.verify(paths, tmp_path, {})
    assert set(hashes) == {"cases.json", "manifest.json", "run.jsonl", "run.json"} and tiers[0].name == "jev"
    (tmp_path / "run.jsonl").write_text((tmp_path / "run.jsonl").read_text() + "\n")
    with pytest.raises(tg.IntegrityError, match="journal hash differs"):
        tg.verify(paths, tmp_path, {})


def test_unrecorded_journal_needs_a_pin_and_paths_can_be_overridden(tmp_path):
    paths = frozen_set(tmp_path, journal_hash=False)
    assert paths.journal == "run.jsonl"  # the report path with .jsonl, as release.py names it
    with pytest.raises(tg.IntegrityError, match="no journal hash"):
        tg.verify(paths, tmp_path, {})
    tg.verify(paths, tmp_path, {"run.jsonl": tg.digest(tmp_path / "run.jsonl")})
    other = tg.resolve_paths(str(tmp_path / "run.json"), journal=str(tmp_path / "other.jsonl"),
                             fixture=str(tmp_path / "cases.json"), root=tmp_path)
    assert (other.journal, other.fixture) == ("other.jsonl", "cases.json")


def test_score_picks_the_profile_from_the_label_schema(tmp_path):
    paths = frozen_set(tmp_path)
    labels = tmp_path / "labels.json"
    labels.write_text(json.dumps({"schema": "nope"}))
    with pytest.raises(ValueError, match="unknown labels schema"):
        tg.score(labels, paths, tmp_path)
    sha = tg.digest(tmp_path / "cases.json")
    for schema, inventory_buckets in ((tg.V1.label_schema, 3), (tg.V2.label_schema, 4)):
        labels.write_text(json.dumps({"schema": schema, "fixture_sha256": sha, "cases": []}))
        doc = tg.score(labels, paths, tmp_path)
        assert len(doc["gold_inventory"]["totals"]) == inventory_buckets
        assert set(doc["inputs_sha256"]) == {"cases.json", "manifest.json", "run.jsonl", "run.json", "labels.json"}
        assert doc["tiers"]["jev"]["gate"]["accepted"] == 3
    labels.write_text(json.dumps({"schema": tg.LABEL_SCHEMA, "fixture_sha256": "0" * 64, "cases": []}))
    with pytest.raises(tg.IntegrityError, match="different fixture"):
        tg.score(labels, paths, tmp_path)


def test_cli_inventory_and_template_from_a_fixture(tmp_path, capsys):
    fixture = tmp_path / "cases.json"
    clarify = {"id": "syn-season_leaders-04", "question": "synthetic leaders", "reference_time": REF_TIME,
               "context": {}, "expected": {"action": "clarify", "clarify_field": "season",
                                           "clarify_reason": "missing"}}
    fixture.write_text(json.dumps({"cases": [raw_case(), clarify]}))
    tg.main(["inventory", "--fixture", str(fixture)])
    inv = json.loads(capsys.readouterr().out)
    assert inv["labeled_cases"] == ["syn-season_leaders-04"]
    assert inv["totals"] == {"mechanical": 4, "labeled": 4, "lookup_decided": 0, "question_decided": 1}
    tg.main(["template", "--fixture", str(fixture), "--out", str(tmp_path / "template.json")])
    doc = json.loads((tmp_path / "template.json").read_text())
    assert doc["schema"] == tg.LABEL_SCHEMA and doc["fixture_sha256"] == tg.digest(fixture)
    assert doc["fields_by_intent"]["season_leaders"] == ["stat", "season_type", "season"]
    assert doc["not_labeled"]["aggregation"] == ["career_stats", "player_season_stats", "season_leaders"]
    assert [c["case_id"] for c in doc["cases"]] == ["syn-season_leaders-04"]
    with pytest.raises(FileExistsError):
        tg.main(["template", "--fixture", str(fixture), "--out", str(tmp_path / "template.json")])
    with pytest.raises(SystemExit):
        tg.main(["inventory"])


def test_cli_schema_1_template_keeps_the_four_family_definition(tmp_path):
    fixture = tmp_path / "cases.json"
    fixture.write_text(json.dumps({"cases": [raw_case()]}))
    tg.main(["template", "--label-schema", "1", "--fixture", str(fixture), "--out", str(tmp_path / "t.json")])
    doc = json.loads((tmp_path / "t.json").read_text())
    assert doc["schema"] == tg.V1.label_schema and list(doc["fields_by_intent"]) == [*tg.V1.intents, "unsupported"]
    assert "target_team" not in doc["fields_by_intent"]["boxscore_stat"] and "not_labeled" not in doc


UNSEEN_TWO_GATE = REPO / "docs/verification/ask-unseen-two-2026-09-29-tier-gate.json"
UNSEEN_TWO_LABELS = "docs/verification/ask-unseen-two-2026-09-29-field-labels.json"


@pytest.mark.skipif(not UNSEEN_TWO_GATE.exists(), reason="recorded unseen-two tier gate report not present")
def test_recorded_unseen_two_report_reproduces(monkeypatch):
    monkeypatch.chdir(REPO)
    paths = tg.resolve_paths(tg.UNSEEN_TWO["report"])
    assert paths == tg.SetPaths(**tg.UNSEEN_TWO)
    doc = json.loads(json.dumps(tg.score(Path(UNSEEN_TWO_LABELS), paths)))
    recorded = json.loads(UNSEEN_TWO_GATE.read_text())
    doc.pop("generated_at"), recorded.pop("generated_at")
    assert doc == recorded
