#!/usr/bin/env python3
"""Prepare and run one frozen, independently labeled Ask release evaluation.

This uses the production cascade builder, not the legacy CLI's whole-request
fallback. Preparation validates labels and records hashes without provider calls.
The live command refuses changed inputs or an existing result journal.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, replace
import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from server.ask.candidates.lookup import CandidateLookupService  # noqa: E402
from server.ask.config import FROZEN_CASCADE  # noqa: E402
from server.ask.eval.runner import Configuration, drive, LabeledCase, score, summarize  # noqa: E402
from server.ask.interpreters.factory import build_cascade, build_policy, frozen_config  # noqa: E402
from server.ask.interpreters.pricing import SpendGuard  # noqa: E402

FROZEN_COMMIT = "6cdae70d2589e14c65f899555f8311b513c1c213"
# The production cascade settings; the live pipeline builds from the same values.
CONFIG = dict(FROZEN_CASCADE)
GATES = {"complete_request_accuracy_min": 0.9, "clarification_accuracy_min": 0.9,
         "unsupported_accuracy_min": 0.9, "schema_valid_guesses_max": 0,
         "p95_latency_ms_max": 4000}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_cases(path: Path) -> list[LabeledCase]:
    cases = [LabeledCase.from_json(row) for row in json.loads(path.read_text())["cases"]]
    if len(cases) != 100 or len({c.id for c in cases}) != 100:
        raise ValueError("release requires exactly 100 uniquely identified questions")
    if any(c.candidates is not None for c in cases):
        raise ValueError("hand-built candidates are forbidden")
    questions = [" ".join(c.question.casefold().split()) for c in cases]
    if len(set(questions)) != len(questions):
        raise ValueError("duplicate question")
    return cases


def frozen_files() -> dict[str, str]:
    paths = sorted(p for p in (ROOT / "server/ask").rglob("*")
                   if p.is_file() and p.suffix in {".py", ".json"})
    paths += [ROOT / "scripts/ask/release.py", ROOT / "server/services/nba_stats_client.py"]
    return {str(p.relative_to(ROOT)): digest(p) for p in paths}


def prepare(args) -> None:
    cases_path = Path(args.cases).resolve()
    cases = load_cases(cases_path)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if commit != FROZEN_COMMIT:
        raise ValueError("checkout is not the designated frozen commit")
    changed = subprocess.check_output(["git", "diff", "HEAD", "--", "server/ask"], cwd=ROOT)
    if changed:
        raise ValueError("production Ask files differ from the frozen commit")
    doc = {"purpose": "Independent Phase 1 unseen interpreter system gate; one production cascade run",
           "prepared_at": dt.datetime.now(dt.timezone.utc).isoformat(),
           "frozen_commit": commit, "cases_file": str(cases_path.relative_to(ROOT)),
           "cases_sha256": digest(cases_path), "files_sha256": frozen_files(),
           "configuration": CONFIG, "gates": GATES,
           "expected_actions": dict(Counter(c.action for c in cases)),
           "scope": "Four Phase 1 request types; no championships tool, retrieval, UI or tier precision gate",
           "prior_spend_estimate_usd": 0.232570, "spend_cap_usd": args.spend_cap,
           "actual_billed_cost_usd": None,
           "price_sources": ["https://docs.typesafe.ai/models",
                             "https://developers.openai.com/api/docs/models/gpt-6-luna"],
           "price_verified_at": "2026-09-29"}
    if not 0 < args.spend_cap <= 0.10:
        raise ValueError("this run is limited to at most $0.10 of the remaining budget")
    with Path(args.manifest).open("x") as out:
        out.write(json.dumps(doc, indent=2) + "\n")
    print(json.dumps({"prepared": args.manifest, "cases_sha256": doc["cases_sha256"],
                      "expected_actions": doc["expected_actions"], "spend_cap_usd": args.spend_cap}))


class Recorder:
    """Capture each provider adapter's typed output without changing its behavior."""

    def __init__(self, adapter, tier: str, records: list):
        self.adapter, self.tier, self.records = adapter, tier, records
        self.name, self.model = adapter.name, adapter.model

    def estimate_cost(self, request):
        return self.adapter.estimate_cost(request)

    def interpret(self, request):
        output = self.adapter.interpret(request)
        self.records.append({"tier": self.tier, "output": output.model_dump(mode="json")})
        return output


def live(args) -> None:
    manifest_path = Path(args.manifest).resolve()
    manifest = json.loads(manifest_path.read_text())
    cases_path = ROOT / manifest["cases_file"]
    if manifest["configuration"] != CONFIG or manifest["gates"] != GATES:
        raise ValueError("configuration or gates differ from the prepared run")
    if digest(cases_path) != manifest["cases_sha256"] or frozen_files() != manifest["files_sha256"]:
        raise ValueError("fixture or implementation changed after preparation")
    if not 0 < manifest["spend_cap_usd"] <= 0.10:
        raise ValueError("invalid spend cap")
    cases = load_cases(cases_path)
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
    config = Configuration("frozen-jev-0.85->gpt-6-luna-low", adapter,
                           build_policy(),
                           fallback_enabled=False)
    lookup = CandidateLookupService()
    guard = SpendGuard(manifest["spend_cap_usd"])
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
            row = {"case_id": case.id, "score": asdict(item),
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
                print(f"{index}/100 scored; estimated spend ${guard.spent_usd:.6f}", flush=True)
            if result.budget_blocked:
                stopped = f"spend cap reached at {case.id}"
                break
    summary = summarize({c.id: c for c in cases}, scores)
    def category_gate(kind):
        category = summary[kind]
        return category["correct"] / category["expected"] >= 0.9 if category["expected"] else False
    gates = {"all_100_scored": len(scores) == 100 and stopped is None,
             "complete_request_accuracy": summary["complete_request_accuracy"] >= 0.9,
             "clarification_accuracy": category_gate("clarification"),
             "unsupported_accuracy": category_gate("unsupported"),
             "zero_wrong_requests": summary["schema_valid_guesses"] == 0,
             "p95_latency": summary["latency_ms"]["p95"] <= 4000}
    doc = {"purpose": manifest["purpose"], "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
           "manifest_file": str(manifest_path.relative_to(ROOT)), "manifest_sha256": digest(manifest_path),
           "cases_sha256": manifest["cases_sha256"], "frozen_commit": FROZEN_COMMIT,
           "configuration": CONFIG, "gate_results": gates, "system_gate_passed": all(gates.values()),
           "tier_gate_status": "not established; existing field oracle is incomplete",
           "summary": summary, "stopped_reason": stopped,
           "elapsed_seconds": round(time.perf_counter() - started, 3),
           "spend": {"cap_usd": guard.cap_usd, "list_price_estimate_usd": round(guard.spent_usd, 6),
                     "actual_billed_cost_usd": None},
           "tier_calls_by_question": dict(Counter("luna" if any(r["tier"] == "luna" for r in row["tier_outputs"])
                                                 else "jev_only" for row in rows)),
           "cases": rows}
    with out_path.open("x") as out:
        out.write(json.dumps(doc, indent=1) + "\n")
    print(json.dumps({"summary": summary, "gate_results": gates, "out": str(out_path)}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare_parser = sub.add_parser("prepare")
    prepare_parser.add_argument("--cases", required=True)
    prepare_parser.add_argument("--manifest", required=True)
    prepare_parser.add_argument("--spend-cap", type=float, default=0.10)
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
