#!/usr/bin/env python3
"""Prepare and run one frozen, independently labeled Ask release evaluation (ADR 0009).

This uses the production cascade builder, not the legacy CLI's whole-request
fallback. Preparation validates labels, size and tool-family coverage, and records
the frozen commit, hashes, gates and spend cap without provider calls. The live
command refuses a different HEAD, changed inputs or an existing result journal. It
computes the system gate's interpretation checks; tier gates (field gold) and
rendered-answer accuracy are scored offline and stay pending in the report.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, replace
import datetime as dt
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import time
from typing import Any, get_args

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from server.ask.candidates.lookup import CandidateLookupService  # noqa: E402
from server.ask.config import FROZEN_CASCADE  # noqa: E402
from server.ask.eval.runner import Configuration, drive, LabeledCase, score, summarize  # noqa: E402
from server.ask.interpreters.factory import build_cascade, build_policy, frozen_config  # noqa: E402
from server.ask.interpreters.pricing import SpendGuard  # noqa: E402
from server.ask.models.common import Intent  # noqa: E402

# The production cascade settings; the live pipeline builds from the same values.
CONFIG = dict(FROZEN_CASCADE)
GATES = {"complete_request_accuracy_min": 0.9, "clarification_accuracy_min": 0.9,
         "unsupported_accuracy_min": 0.9, "schema_valid_guesses_max": 0,
         "p95_latency_ms_max": 4000}
# ADR 0004: the router's eight tools. ADR 0009: the unseen set covers every one.
FAMILIES = get_args(Intent)
PROVISIONAL_COVERAGE = 0.35  # same rule as scripts/ask/tier_gate.py
# ADR 0009 gates the tiers with calibrated thresholds (Laya, Jev); Luna is the final tier.
TIER_GATES = {"accepted_field_precision_min": 0.98, "coverage_min": 0.30,
              "tiers": {"laya": {"accept_min": CONFIG["laya_accept_min"]} if CONFIG["laya_base_url"]
                        else {"disabled": "laya_base_url is unset in the frozen configuration"},
                        "jev": {"accept_min": CONFIG["jev_accept_min"]}},
              "provisional_rule": f"a pass is provisional when one more accepted-field error would fail precision "
                                  f"or coverage is below {PROVISIONAL_COVERAGE}; rerun with a larger set"}
TIER_GATE_COMMAND = ("write the isolated labeler's template with `python scripts/ask/tier_gate.py template "
                     "--fixture FIXTURE --out TEMPLATE`, have an isolated labeler fill it (field-label brief), "
                     "then run `python scripts/ask/tier_gate.py score --report REPORT --labels LABELS --out OUT` "
                     "(REPORT is this report; its manifest, fixture and journal are read from it)")
ANSWER_CHECK = "scripts/ask/answer_check.py"
DEFAULT_MIN_CASES = 150
DEFAULT_MIN_PER_FAMILY = 10
DEFAULT_MIN_PER_OUTCOME = 10  # clarification and unsupported cases
WATCHED = ("server/ask", "scripts/ask", "server/services/nba_stats_client.py")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def family_of(case: LabeledCase) -> str:
    """Accept labels name their tool; other labels name it in a tag or the id."""
    if case.action == "accept":
        return case.request.intent
    named = {f for f in FAMILIES if f in case.tags} or {f for f in FAMILIES if f"-{f}-" in f"-{case.id}-"}
    if len(named) != 1:
        raise ValueError(f"{case.id}: name exactly one tool family in tags or id, found {sorted(named)}")
    return named.pop()


def load_cases(path: Path, min_cases: int = DEFAULT_MIN_CASES) -> list[LabeledCase]:
    cases = [LabeledCase.from_json(row) for row in json.loads(path.read_text())["cases"]]
    if len(cases) < min_cases:
        raise ValueError(f"release requires at least {min_cases} questions, found {len(cases)}")
    if len({c.id for c in cases}) != len(cases):
        raise ValueError("case ids must be unique")
    if any(c.candidates is not None for c in cases):
        raise ValueError("hand-built candidates are forbidden")
    questions = [" ".join(c.question.casefold().split()) for c in cases]
    if len(set(questions)) != len(questions):
        raise ValueError("duplicate question")
    return cases


def coverage(cases: list[LabeledCase], min_per_family: int, min_per_outcome: int) -> dict[str, dict[str, int]]:
    """Cases per tool family and action; raises unless every family and outcome meets its minimum."""
    counts = {f: {"accept": 0, "clarify": 0, "unsupported": 0} for f in FAMILIES}
    for case in cases:
        counts[family_of(case)][case.action] += 1
    short = [f"{f}: {sum(c.values())}" for f, c in counts.items() if sum(c.values()) < min_per_family]
    short += [f"{a}: {n}" for a in ("clarify", "unsupported")
              if (n := sum(c[a] for c in counts.values())) < min_per_outcome]
    if short:
        raise ValueError(f"coverage below minimum (family {min_per_family}, outcome {min_per_outcome}): "
                         + ", ".join(short))
    return {f: {**c, "total": sum(c.values())} for f, c in counts.items()}


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def head_commit() -> str:
    return git("rev-parse", "HEAD")


def frozen_files() -> dict[str, str]:
    paths = sorted(p for p in (ROOT / "server/ask").rglob("*")
                   if p.is_file() and p.suffix in {".py", ".json"})
    paths += [ROOT / "scripts/ask/release.py", ROOT / "server/services/nba_stats_client.py"]
    return {str(p.relative_to(ROOT)): digest(p) for p in paths}


def prepare(args) -> None:
    if args.spend_cap is None or not args.spend_cap > 0:
        raise ValueError("an explicit positive --spend-cap is required")
    if min(args.min_cases, args.min_per_family, args.min_per_outcome) < 1:
        raise ValueError("case minimums must be at least 1")
    cases_path = Path(args.cases).resolve()
    cases = load_cases(cases_path, args.min_cases)
    counts = coverage(cases, args.min_per_family, args.min_per_outcome)
    commit = head_commit()
    if git("rev-parse", "--verify", f"{args.frozen_commit or commit}^{{commit}}") != commit:
        raise ValueError("the frozen commit must be checked out (HEAD)")
    if git("status", "--porcelain", "--untracked-files=all", "--", *WATCHED):
        raise ValueError(f"uncommitted changes under {', '.join(WATCHED)}; commit before freezing")
    doc = {"purpose": "ADR 0009 unseen evaluation: one production cascade run for the system gate, "
                      "with per-tier outputs recorded for the tier gates",
           "prepared_at": dt.datetime.now(dt.timezone.utc).isoformat(),
           "frozen_commit": commit, "cases_file": str(cases_path.relative_to(ROOT)),
           "cases_sha256": digest(cases_path), "files_sha256": frozen_files(),
           "configuration": CONFIG, "gates": GATES, "tier_gates": TIER_GATES,
           "case_minimums": {"cases": args.min_cases, "per_family": args.min_per_family,
                             "per_outcome": args.min_per_outcome},
           "cases": len(cases), "expected_actions": dict(Counter(c.action for c in cases)),
           "family_counts": counts,
           "scope": f"All {len(FAMILIES)} ADR 0004 tool families plus clarification and unsupported cases; "
                    "system gate computed live; tier gates and rendered-answer accuracy scored offline",
           "prior_spend_estimate_usd": args.spend_estimate, "spend_cap_usd": args.spend_cap,
           "actual_billed_cost_usd": None,
           "price_sources": ["https://docs.typesafe.ai/models",
                             "https://developers.openai.com/api/docs/models/gpt-6-luna"],
           "price_verified_at": "2026-09-29"}
    with Path(args.manifest).open("x") as out:
        out.write(json.dumps(doc, indent=2) + "\n")
    print(json.dumps({"prepared": args.manifest, "frozen_commit": commit, "cases": len(cases),
                      "cases_sha256": doc["cases_sha256"], "expected_actions": doc["expected_actions"],
                      "family_counts": counts, "spend_cap_usd": args.spend_cap}))


def tier_readings(tiers: dict[str, dict[str, Any]], rows: list[dict[str, Any]],
                  families: dict[str, str]) -> dict[str, Any]:
    """Per gated tier, readings accepted at its threshold, by field and family. Without field
    gold these give no precision or coverage, so every gate stays pending."""
    out: dict[str, Any] = {}
    precision_min = TIER_GATES["accepted_field_precision_min"]
    for name, spec in tiers.items():
        if "accept_min" not in spec:
            out[name] = {"status": "not_run", "reason": spec.get("disabled")}
            continue
        by_field: dict[str, Counter] = {}
        by_family: dict[str, Counter] = {}
        for row in rows:
            for record in row["tier_outputs"]:
                if record["tier"] != name:
                    continue
                output = record["output"]
                if output["outcome"] == "unsupported":
                    reads = [("intent", True)]  # the cascade accepts it (tier_gate.py RULES)
                else:
                    reads = [(f["field"], f["confidence"] is not None and f["confidence"] >= spec["accept_min"])
                             for f in output.get("fields", [])]
                for field_name, accepted in reads:
                    for group, key in ((by_field, field_name), (by_family, families[row["case_id"]])):
                        group.setdefault(key, Counter())["read"] += 1
                        group[key]["accepted"] += accepted
        accepted = sum(c["accepted"] for c in by_field.values())
        # Accepted-field errors the precision threshold would tolerate at this many acceptances.
        tolerated = math.floor((1 - precision_min) * accepted + 1e-9)
        out[name] = {"status": "pending", "passed": None, "accept_min": spec["accept_min"],
                     "readings": sum(c["read"] for c in by_field.values()), "accepted_readings": accepted,
                     "tolerated_accepted_errors": tolerated,
                     "small_sample": tolerated <= 1,
                     "by_field": {k: dict(v) for k, v in sorted(by_field.items())},
                     "by_family": {k: dict(v) for k, v in sorted(by_family.items())},
                     "command": TIER_GATE_COMMAND}
    return out


class Recorder:
    """Capture each provider adapter's typed output without changing its behavior."""

    def __init__(self, adapter, tier: str, records: list):
        self.adapter, self.tier, self.records = adapter, tier, records
        self.name, self.model = adapter.name, adapter.model

    def estimate_cost(self, request):
        return self.adapter.estimate_cost(request)

    def interpret(self, request):
        output = self.adapter.interpret(request)
        # Candidates differ per attempt once lookup expands them; tier_gate.py scores the last attempt.
        self.records.append({"tier": self.tier, "output": output.model_dump(mode="json"),
                             "candidates": request.candidates.model_dump(mode="json")})
        return output


def live(args) -> None:
    manifest_path = Path(args.manifest).resolve()
    manifest = json.loads(manifest_path.read_text())
    cases_path = ROOT / manifest["cases_file"]
    if (manifest["configuration"] != CONFIG or manifest["gates"] != GATES
            or manifest.get("tier_gates") != TIER_GATES):
        raise ValueError("configuration or gates differ from the prepared run")
    if head_commit() != manifest.get("frozen_commit"):
        raise ValueError("HEAD is not the manifest's frozen commit")
    if digest(cases_path) != manifest["cases_sha256"] or frozen_files() != manifest["files_sha256"]:
        raise ValueError("fixture or implementation changed after preparation")
    cap = manifest.get("spend_cap_usd")
    if not isinstance(cap, (int, float)) or isinstance(cap, bool) or not cap > 0:
        raise ValueError("manifest needs an explicit positive spend_cap_usd")
    minimums = manifest.get("case_minimums") or {}
    if not {"cases", "per_family", "per_outcome"} <= set(minimums):
        raise ValueError("manifest needs case_minimums")
    cases = load_cases(cases_path, minimums["cases"])
    if coverage(cases, minimums["per_family"], minimums["per_outcome"]) != manifest.get("family_counts"):
        raise ValueError("family counts differ from the prepared run")
    families = {c.id: family_of(c) for c in cases}
    spec = importlib.util.spec_from_file_location("ask_evaluate_cli", ROOT / "scripts/ask/evaluate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    keys = module.load_keys(args.env_file)
    if not all(keys.get(k) for k in ("TYPESAFE_API_KEY", "OPENAI_API_KEY")):
        raise ValueError("both provider keys are required")
    out_path = Path(args.out)
    journal_path = out_path.with_suffix(".jsonl")
    if out_path.exists():
        raise FileExistsError("report already exists; refusing a repeat run")
    # Exclusive journal creation also protects against simultaneous/repeated starts.
    journal = journal_path.open("x")
    tier_records: list = []
    # Same factory, settings, and policy as the live pipeline (production: no Laya).
    adapter = build_cascade(frozen_config(**CONFIG, api_key=keys["OPENAI_API_KEY"],
                                          typesafe_api_key=keys["TYPESAFE_API_KEY"]))
    adapter.tiers = [replace(t, adapter=Recorder(t.adapter, t.name, tier_records)) for t in adapter.tiers]
    config = Configuration(f"frozen-jev-{CONFIG['jev_accept_min']}->{CONFIG['primary_model']}-"
                           f"{CONFIG['primary_reasoning_effort']}", adapter, build_policy(), fallback_enabled=False)
    lookup = CandidateLookupService()
    guard = SpendGuard(cap)
    rows, scores = [], []
    started = time.perf_counter()
    stopped = None
    with journal:
        for index, case in enumerate(cases, 1):
            tier_records.clear()
            candidates = lookup.lookup(case.question, case.context)
            result = drive(config, case.question, case.context, candidates, guard=guard,
                           deadline_ms=int(CONFIG["deadline_seconds"] * 1000), expand=lookup.expand)
            item = score(case, config.name, result)
            # Existing runner fallback_used covers whole-request fallback only.
            item.fallback_used = any(record["tier"] == "luna" for record in tier_records)
            row = {"case_id": case.id, "family": families[case.id], "score": asdict(item),
                   "decision": result.decision.model_dump(mode="json"),
                   "candidates": candidates.model_dump(mode="json"),
                   "expanded_fields": result.expanded_fields,
                   "attempts": [attempt.model_dump(mode="json") for attempt in result.attempts],
                   "tier_outputs": list(tier_records)}
            journal.write(json.dumps(row) + "\n")
            journal.flush()
            rows.append(row)
            scores.append(item)
            if index % 10 == 0 or result.budget_blocked:
                print(f"{index}/{len(cases)} scored; estimated spend ${guard.spent_usd:.6f}", flush=True)
            if result.budget_blocked:
                stopped = f"spend cap reached at {case.id}"
                break
    summary = summarize({c.id: c for c in cases}, scores)
    def category_gate(kind):
        category = summary[kind]
        return category["correct"] / category["expected"] >= GATES[f"{kind}_accuracy_min"] if category["expected"] else False
    gates = {"all_cases_scored": len(scores) == len(cases) and stopped is None,
             "complete_request_accuracy": summary["complete_request_accuracy"] >= GATES["complete_request_accuracy_min"],
             "clarification_accuracy": category_gate("clarification"),
             "unsupported_accuracy": category_gate("unsupported"),
             "zero_wrong_requests": summary["schema_valid_guesses"] <= GATES["schema_valid_guesses_max"],
             "p95_latency": summary["latency_ms"]["p95"] <= GATES["p95_latency_ms_max"]}
    tiers = tier_readings(TIER_GATES["tiers"], rows, families)
    pending = [f"tier gate: {name}" for name, t in tiers.items() if t["status"] == "pending"]
    pending.append(f"rendered answer accuracy: {ANSWER_CHECK}")
    # A computed failure is final; a pass waits on every pending check (ADR 0009: no rendered wrong answer).
    verdict = False if not all(gates.values()) else None
    doc = {"purpose": manifest["purpose"], "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
           "manifest_file": str(manifest_path.relative_to(ROOT)), "manifest_sha256": digest(manifest_path),
           "cases_sha256": manifest["cases_sha256"], "frozen_commit": manifest["frozen_commit"],
           "journal_file": journal_path.name, "journal_sha256": digest(journal_path),
           "configuration": CONFIG, "gate_results": gates,
           "interpretation_gates_passed": all(gates.values()),
           "system_gate_passed": verdict, "release_passed": verdict, "pending_checks": pending,
           "tier_gates": {"thresholds": {k: v for k, v in TIER_GATES.items() if k != "tiers"}, "tiers": tiers},
           "answer_accuracy": {"status": "pending", "check": ANSWER_CHECK, "result": None},
           "summary_notes": {"schema_valid_guesses": "accepted requests that differ from the label or accept "
                             "a clarify/unsupported label: wrong interpretations, not rendered answers. "
                             f"Rendered-answer correctness is the separate {ANSWER_CHECK} check."},
           "family_counts": manifest["family_counts"],
           "summary": summary, "stopped_reason": stopped,
           "elapsed_seconds": round(time.perf_counter() - started, 3),
           "spend": {"cap_usd": guard.cap_usd, "list_price_estimate_usd": round(guard.spent_usd, 6),
                     "actual_billed_cost_usd": None},
           "tier_calls_by_question": dict(Counter("luna" if any(r["tier"] == "luna" for r in row["tier_outputs"])
                                                 else "jev_only" for row in rows)),
           "cases": rows}
    with out_path.open("x") as out:
        out.write(json.dumps(doc, indent=1) + "\n")
    print(json.dumps({"summary": summary, "gate_results": gates, "pending_checks": pending,
                      "out": str(out_path)}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare_parser = sub.add_parser("prepare")
    prepare_parser.add_argument("--cases", required=True)
    prepare_parser.add_argument("--manifest", required=True)
    prepare_parser.add_argument("--spend-cap", type=float, required=True,
                                help="hard maximum estimated spend in USD for the live run")
    prepare_parser.add_argument("--spend-estimate", type=float, default=None,
                                help="prior list-price estimate in USD, recorded only")
    prepare_parser.add_argument("--frozen-commit", default=None,
                                help="commit to freeze; must be HEAD (default HEAD)")
    prepare_parser.add_argument("--min-cases", type=int, default=DEFAULT_MIN_CASES)
    prepare_parser.add_argument("--min-per-family", type=int, default=DEFAULT_MIN_PER_FAMILY)
    prepare_parser.add_argument("--min-per-outcome", type=int, default=DEFAULT_MIN_PER_OUTCOME,
                                help="minimum clarification and minimum unsupported cases")
    prepare_parser.set_defaults(func=prepare)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--manifest", required=True)
    run_parser.add_argument("--env-file", required=True)
    run_parser.add_argument("--out", required=True)
    run_parser.set_defaults(func=live)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
