#!/usr/bin/env python3
"""Offline analysis of the 2026-10-06 calibration run. No provider calls.

Reads report.json / report.jsonl (scripts/ask/release.py) and cases.json, and reuses the
scorers in scripts/ask/tier_gate.py and server/ask/eval/trace.py:

* tier: Jev accepted-field precision and coverage for accept_min 0.50-0.99 (tier_gate.score_tier).
  Gold is mechanical (accept labels, interpreter-only unsupported reasons) for every case, plus
  the isolated labeler's file for the unseen-two cases. Clarify cases outside unseen-two have no
  field gold and are not scored.
* system: the dev gate preview by tool family, and every failing case.
* no_match: fields a gated tier accepted that the later tier read as no_matching_candidate.
* replay: the journal replayed through TieredAdapter for other accept_min and veto_min values
  (trace.sweep). Luna was recorded only where Jev escalated at 0.85, so a higher accept_min
  has replay misses and is not a valid system measurement.

Usage: server/venv/bin/python docs/verification/ask-calibration-2026-10-06/analyze.py
"""

from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts/ask"))

import tier_gate as tg  # noqa: E402
from server.ask.candidates.lookup import CandidateLookupService  # noqa: E402
from server.ask.config import FROZEN_CASCADE  # noqa: E402
from server.ask.eval import trace as tr  # noqa: E402
from server.ask.eval.runner import LabeledCase, percentile  # noqa: E402
from server.ask.models.candidates import CandidateLookupResult  # noqa: E402
from server.ask.models.interpreter import InterpreterInput  # noqa: E402

ACCEPT_MIN = FROZEN_CASCADE["jev_accept_min"]
UNSEEN_TWO_LABELS = ROOT / "docs/verification/ask-unseen-two-2026-09-29-field-labels.json"
GRID = [x / 100 for x in range(50, 100)]
# Unsupported reasons for tools that now exist (models/interpreter.py: "historical reports only").
# Four-family sets labeled these questions unsupported; today's eight-tool code answers them.
STALE_REASONS = {"season_stats", "regular_season_record", "standings", "career_stats", "season_leaders"}


def stale(case) -> bool:
    return case.action == "unsupported" and case.unsupported_reason in STALE_REASONS


def load():
    raw = json.loads((HERE / "cases.json").read_text())["cases"]
    cases = {c["id"]: LabeledCase.from_json(c) for c in raw}
    rows = {r["case_id"]: r for r in map(json.loads, (HERE / "report.jsonl").read_text().splitlines())
            # The spend cap blocked the last journal row before any provider call; it is not a measurement.
            if "budget_exceeded" not in r["score"]["error_codes"]}
    return {cid: c for cid, c in cases.items() if cid in rows}, rows


def build_plans(cases, rows):
    """Mechanical gold for every case; the unseen-two labeler's gold on top (schema 1)."""
    plans, unlabeled = {}, []
    family_of = tg.family_of
    for cid, case in cases.items():
        two = cid.startswith("unseen-two-")
        tg.family_of = lambda _id, _profile=None, f=rows[cid]["family"]: f  # ids of older sets name no family
        plans[cid] = tg.plan(case, tg.V1 if two else tg.V2)
    tg.family_of = family_of
    two = {cid: p for cid, p in plans.items() if cid.startswith("unseen-two-")}
    if two:
        labels = json.loads(UNSEEN_TWO_LABELS.read_text())
        labels["cases"] = [row for row in labels["cases"] if row["case_id"] in two]  # a capped run may stop early
        tg.apply_labels(two, labels, tg.Reference.load())
    for cid, p in list(plans.items()):
        if cid in two or p.label_scope is None:
            continue
        if p.label_scope == "all":
            unlabeled.append(cid)
            del plans[cid]
        else:  # non-player boxscore scope: every field but `player` is mechanical
            p.gold["player"], p.sources["player"] = [], "unlabeled"
    return plans, unlabeled


def score_jev(threshold, cases, plans, rows):
    return [s for s in tg.score_tier("jev", threshold, cases, plans, rows) if s.source != "unlabeled"]


def tier_section(cases, plans, rows):
    def curve(subset):
        out = []
        for t in GRID:
            items = [s for s in score_jev(t, cases, plans, rows) if subset(s.case_id)]
            m = tg.metrics(items)
            out.append({"threshold": t, **{k: m[k] for k in ("eligible", "accepted", "accepted_errors", "precision",
                                                              "coverage")}})
        return out

    def chosen(rows_):
        """Lowest threshold at and above which precision holds (trace.calibrate_tier's rule)."""
        pick = None
        for row in reversed(rows_):
            if row["precision"] is not None and row["precision"] < tg.PRECISION_MIN:
                break
            if row["accepted"]:
                pick = row
        return pick

    scored = score_jev(ACCEPT_MIN, cases, plans, rows)
    try:
        tg.check_cascade("jev", ACCEPT_MIN, {cid: rows[cid] for cid in plans}, scored)
        cascade_check = "ok"
    except tg.IntegrityError as exc:
        cascade_check = str(exc)
    subsets = {"all_gold": lambda cid: True,
               "all_gold_without_stale_scope_labels": lambda cid: not stale(cases[cid]),
               "unseen_two_without_stale_scope_labels":
                   lambda cid: cid.startswith("unseen-two-") and not stale(cases[cid]),
               "unseen_two_full_gold": lambda cid: cid.startswith("unseen-two-"),
               "eight_tool_mechanical": lambda cid: cid.startswith(("stage2-", "stage3-", "unseen-three-")),
               "unseen_one_mechanical": lambda cid: cid.startswith("unseen-2026-")}
    out = {"accept_min_current": ACCEPT_MIN, "cascade_check": cascade_check, "subsets": {}}
    for name, subset in subsets.items():
        rows_ = curve(subset)
        current = next(r for r in rows_ if r["threshold"] == ACCEPT_MIN)
        items = [s for s in scored if subset(s.case_id)]
        out["subsets"][name] = {
            "current": tg.gate(items), "recommended": chosen(rows_), "curve": rows_,
            "by_field": tg.breakdown(items, "field"), "by_family": tg.breakdown(items, "family"),
            "accepted_field_errors": tg.error_rows(items)}
        print(f"{name}: at {ACCEPT_MIN} precision={current['precision']} coverage={current['coverage']} "
              f"errors={current['accepted_errors']}/{current['accepted']}; lowest passing={chosen(rows_)}")
    return out


def system_section(cases, rows):
    def stats(items):
        scores = [r["score"] for r in items]
        exp = lambda a: [s for s in scores if cases[s["case_id"]].action == a]  # noqa: E731
        lat = [s["latency_ms"] for s in scores]
        n = len(scores)
        return {"cases": n, "correct": sum(s["correct"] for s in scores),
                "share_correct": round(sum(s["correct"] for s in scores) / n, 4) if n else None,
                "clarify_correct": f"{sum(s['correct'] for s in exp('clarify'))}/{len(exp('clarify'))}",
                "unsupported_correct": f"{sum(s['correct'] for s in exp('unsupported'))}/{len(exp('unsupported'))}",
                "guesses": sum(s["guess"] for s in scores),
                "service_failures": sum(s["failure"] == "service_failure" for s in scores),
                "latency_p50_ms": percentile(lat, 50), "latency_p95_ms": percentile(lat, 95),
                "luna_called": sum(any(t["tier"] == "luna" for t in r["tier_outputs"]) for r in items),
                "failures": dict(Counter(s["failure"] for s in scores if s["failure"]))}

    by_family, by_source = defaultdict(list), defaultdict(list)
    for cid, row in rows.items():
        by_family[row["family"]].append(row)
        by_source[cid.rsplit("-", 2)[0] if cid.startswith(("stage", "unseen-three")) else
                  ("unseen-two" if cid.startswith("unseen-two") else "unseen-2026-09-29")].append(row)
    current = [r for cid, r in rows.items() if not stale(cases[cid])]
    out = {"overall": stats(list(rows.values())),
           "stale_scope_label_cases": sorted(cid for cid in rows if stale(cases[cid])),
           "overall_without_stale_scope_labels": stats(current),
           "by_family_without_stale_scope_labels": {
               f: stats([r for r in current if r["family"] == f]) for f in by_family},
           "by_family": {f: stats(v) for f, v in by_family.items()},
           "by_source": {f: stats(v) for f, v in sorted(by_source.items())}}
    errors = Counter(f"{t['tier']}:{t['output']['error_code']}" for r in rows.values() for t in r["tier_outputs"]
                     if t["output"].get("error_code"))
    out["provider_errors"] = dict(errors)
    out["attempts_per_question"] = dict(Counter(len(r["attempts"]) for r in rows.values()))
    usage = defaultdict(lambda: Counter())
    for r in rows.values():
        for t in r["tier_outputs"]:
            u = t["output"]["metadata"]["usage"]
            usage[t["tier"]].update(calls=u["provider_calls"], input_tokens=u["input_tokens"] or 0,
                                    output_tokens=u.get("output_tokens") or 0,
                                    cached_input_tokens=u.get("cached_input_tokens") or 0)
            usage[t["tier"]]["cost_micro_usd"] += round((u["cost_usd"] or 0) * 1e6)
    out["usage"] = {k: dict(v) for k, v in usage.items()}
    failures = []
    for cid, row in rows.items():
        s, case = row["score"], cases[cid]
        if s["correct"]:
            continue
        meta = row["attempts"][-1]["output"]["metadata"]
        failures.append({
            "case_id": cid, "family": row["family"], "question": case.question, "failure": s["failure"],
            "guess": s["guess"],
            "label": {"action": case.action, "clarify_field": case.clarify_field,
                      "clarify_reason": case.clarify_reason, "unsupported_reason": case.unsupported_reason,
                      "request": case.request.model_dump(mode="json") if case.request else None},
            "actual": {"action": s["action"], "clarify_field": s["clarify_field"],
                       "clarify_reason": row["decision"].get("reason"),
                       "unsupported_reason": s["unsupported_reason"], "request": s["actual_request"]},
            "latency_ms": s["latency_ms"], "error_codes": s["error_codes"],
            "field_tiers": meta.get("field_tiers"),
            "reads": {d["field"]: [f"{r['tier']}:{r['status']}@{r['confidence']}:{r['action']}" for r in d["reads"]]
                      for d in meta.get("field_decisions", [])},
            "tier_outcomes": [f"{t['tier']}:{t['output']['outcome']}:{t['output'].get('unsupported_reason')}"
                              for t in row["tier_outputs"]]})
    out["failing_cases"] = failures
    for name, group in (("overall", {"all": out["overall"]}), ("family", out["by_family"]),
                        ("adjusted", {"all": out["overall_without_stale_scope_labels"]}),
                        ("adjusted-family", out["by_family_without_stale_scope_labels"])):
        for key, v in group.items():
            print(f"{name}:{key} {v['correct']}/{v['cases']} clarify {v['clarify_correct']} unsupported "
                  f"{v['unsupported_correct']} guesses {v['guesses']} p50 {v['latency_p50_ms']} p95 {v['latency_p95_ms']}")
    return out


def no_match_section(cases, plans, rows):
    """A later tier read no_matching_candidate on a field an earlier tier accepted (not a veto)."""
    events, denominators, luna_no_match, overrides = [], Counter(), [], []
    for cid, row in rows.items():
        records, raw = tg.final_attempt(row)
        by_tier = {r["tier"]: r["output"] for r in records}
        jev, luna = by_tier.get("jev"), by_tier.get("luna")
        denominators["questions"] += 1
        if not jev or not luna or jev["outcome"] != "interpreted":
            continue
        denominators["questions_luna_called_after_jev_interpreted"] += 1
        intent = next((f for f in jev["fields"] if f["field"] == "intent"), None)
        if luna["outcome"] == "unsupported" and intent and (intent["confidence"] or 0) >= ACCEPT_MIN:
            # Related, also not a veto: a later unsupported outcome replaces an accepted intent.
            overrides.append({"case_id": cid, "question": cases[cid].question, "jev_intent": intent["selected"],
                              "jev_confidence": intent["confidence"], "luna_reason": luna["unsupported_reason"],
                              "label_action": cases[cid].action,
                              "label_reason": cases[cid].unsupported_reason,
                              "label_intent": cases[cid].request.intent if cases[cid].request else None,
                              "case_correct": row["score"]["correct"], "failure": row["score"]["failure"]})
        if luna["outcome"] != "interpreted":
            continue
        jev_fields = {f["field"]: f for f in jev["fields"]}
        for f in luna["fields"]:
            if f["status"] == "no_matching_candidate":
                earlier = jev_fields.get(f["field"])
                luna_no_match.append({"case_id": cid, "field": f["field"],
                                      "jev": f"{earlier['status']}@{earlier['confidence']}" if earlier else None})
        cands = CandidateLookupResult.model_validate(raw)
        luna_fields = {f["field"]: f for f in luna["fields"]}
        final = row["attempts"][-1]["output"]["metadata"].get("field_tiers", {})
        plan = plans.get(cid)
        for read in jev["fields"]:
            name = read["field"]
            if read["confidence"] is None or read["confidence"] < ACCEPT_MIN:
                continue
            later = luna_fields.get(name)
            if later is None:
                continue
            denominators["jev_accepted_fields_luna_also_read"] += 1
            denominators[f"jev_accepted_{read['status']}_luna_also_read"] += 1
            if later["status"] != "no_matching_candidate":
                continue
            correct = None
            if plan is not None and name in plan.gold and plan.gold[name] and name in plan.fields():
                kind, payload = tg.effective(name, read, cands, None)
                correct = kind != "invalid" and tg.judge(name, kind, payload, plan.gold[name], cands,
                                                         tg.stat_default(plan))[0]
            events.append({"case_id": cid, "question": cases[cid].question, "field": name,
                           "jev_status": read["status"], "jev_selected": read["selected"],
                           "jev_confidence": read["confidence"], "used_by_final_request": name in final,
                           "final_decided_by": final.get(name),
                           "jev_read_correct_vs_gold": correct,
                           "gold": [g.show() for g in plan.gold.get(name, [])] if plan else None,
                           "case_correct": row["score"]["correct"], "case_action": row["score"]["action"],
                           "label_action": cases[cid].action})
    out = {"denominators": dict(denominators), "events": events,
           "luna_no_match_reads_any_field": luna_no_match,
           "luna_unsupported_after_jev_accepted_intent": overrides,
           "summary": dict(Counter(f"jev_{e['jev_status']}|relevant={e['used_by_final_request']}|"
                                   f"jev_correct={e['jev_read_correct_vs_gold']}" for e in events))}
    print("no_match:", json.dumps(out["denominators"]), json.dumps(out["summary"], indent=1))
    print("luna no-match reads:", json.dumps(luna_no_match))
    print("luna unsupported after accepted jev intent:", json.dumps(overrides, indent=1))
    return out


def replay_section(cases, rows):
    """Replay the journal at other thresholds. Valid only where replay_misses is 0."""
    stores = {"jev": {}, "luna": {}}
    models = {}
    for cid, row in rows.items():
        case = cases[cid]
        for record in row["tier_outputs"]:
            cands = CandidateLookupResult.model_validate(record["candidates"])
            request = InterpreterInput(question=case.question, context=case.context, candidates=cands,
                                       deadline_ms=0, max_cost_usd=0)
            stores[record["tier"]][tr.trace_key(request)] = record["output"]
            models[record["tier"]] = record["output"]["metadata"]["model"]
    trace = {"tiers": {t: {"model": models[t], "outputs": stores[t]} for t in ("jev", "luna")},
             "candidates": {cid: row["candidates"] for cid, row in rows.items()}}
    lookup = CandidateLookupService()
    case_list = list(cases.values())
    keep = ("thresholds", "veto_min", "cases", "correct", "complete_request_accuracy", "schema_valid_guesses",
            "service_failures", "clarification", "unsupported", "failures", "replay_misses", "tier_share")
    out = {"accept_min_sweep": [], "veto_min_sweep": []}
    live = {cid: row["score"]["correct"] for cid, row in rows.items()}
    run, summary = tr.evaluate(case_list, trace, {"jev": ACCEPT_MIN, "luna": None},
                               veto_min=FROZEN_CASCADE["veto_min"], expand=lookup.expand)
    replayed = {s.case_id: s.correct for s in next(iter(run.scores.values()))}
    out["replay_matches_live"] = {"differing_cases": sorted(c for c in live if live[c] != replayed.get(c)),
                                  "replay_misses": summary["replay_misses"]}
    print("replay vs live:", out["replay_matches_live"])
    for row in tr.sweep(case_list, trace, {"jev": [0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95], "luna": [None]},
                        veto_mins=[FROZEN_CASCADE["veto_min"]], expand=lookup.expand):
        out["accept_min_sweep"].append({k: row[k] for k in keep})
        print(f"accept {row['thresholds']['jev']}: correct {row['correct']} guesses {row['schema_valid_guesses']} "
              f"misses {row['replay_misses']} share {row['tier_share']}")
    for row in tr.sweep(case_list, trace, {"jev": [ACCEPT_MIN], "luna": [None]},
                        veto_mins=[0.0, 0.3, 0.5, 0.6, 0.7, 0.8, 0.85], expand=lookup.expand):
        out["veto_min_sweep"].append({k: row[k] for k in keep})
        print(f"veto {row['veto_min']}: correct {row['correct']} guesses {row['schema_valid_guesses']} "
              f"misses {row['replay_misses']} failures {row['failures']}")
    return out


def main() -> None:
    cases, rows = load()
    plans, unlabeled = build_plans(cases, rows)
    doc = {"purpose": "Offline analysis of the 2026-10-06 exposed-data calibration run. Not release evidence.",
           "inputs": {"report": "report.json", "journal": "report.jsonl", "cases": "cases.json",
                      "field_labels": str(UNSEEN_TWO_LABELS.relative_to(ROOT))},
           "questions": len(rows),
           "tier_gold": {"cases_with_gold": len(plans), "cases_without_field_gold": unlabeled,
                         "note": "clarify and normalizer-unsupported cases outside unseen-two have no field gold"},
           "tier": tier_section(cases, plans, rows),
           "system": system_section(cases, rows),
           "no_matching_candidate_after_accept": no_match_section(cases, plans, rows),
           "replay": replay_section(cases, rows)}
    (HERE / "analysis.json").write_text(json.dumps(doc, indent=1, default=str) + "\n")
    print("wrote", HERE / "analysis.json")


if __name__ == "__main__":
    main()
