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
    (tmp_path / "frozen.json").write_text("{}")
    with pytest.raises(tg.IntegrityError, match="frozen inputs changed"):
        tg.verify(tmp_path, {"frozen.json": "0" * 64})


def test_score_refuses_to_overwrite(tmp_path):
    out = tmp_path / "report.json"
    out.write_text("{}")
    with pytest.raises(FileExistsError):
        tg.main(["score", "--labels", str(tmp_path / "labels.json"), "--out", str(out)])
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
    assert doc["gold_inventory"]["totals"] == {"mechanical": 3, "labeled": 0, "lookup_decided": 1}
    json.dumps(doc)
