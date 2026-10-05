#!/usr/bin/env python3
"""Evaluate Ask interpreter configurations (#199).

Two subcommands:

  probe  Live access check: a few simple questions per provider/model with hand-built
         candidates, to confirm access, resolved model IDs, and response shapes.
         Writes a sanitized report (no keys, prompts, or raw provider text).

  run    Full comparison on labeled cases. Candidates must come from #200's lookup
         (`--lookup module:factory`); embedded hand-built candidates are allowed only
         with `--allow-hand-built` and are never valid for the #199 decision.

Keys are read from the environment, or from `--env-file` (e.g. the main checkout's
server/.env). Key values are never printed or written.

Examples (from the repo root):
  server/venv/bin/python scripts/ask/evaluate.py probe --env-file ../../server/.env
  server/venv/bin/python scripts/ask/evaluate.py run --cases server/tests/ask/fixtures/eval/dev.json \
      --lookup server.ask.candidates.lookup:build_lookup --configs jev gpt-4.1-mini luna jev+luna
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from server.ask.eval.runner import (  # noqa: E402
    Configuration,
    LabeledCase,
    drive,
    embedded_candidates,
    report,
    run,
)
from server.ask.interpreters.cascade import ThresholdCascadePolicy  # noqa: E402
from server.ask.interpreters.jev import JEV_MODEL, JevAdapter  # noqa: E402
from server.ask.interpreters.openai_responses import (  # noqa: E402
    BASELINE_MODEL,
    OpenAIConfig,
    OpenAIResponsesAdapter,
)
from server.ask.interpreters.pricing import SpendGuard  # noqa: E402

KEY_NAMES = ("TYPESAFE_API_KEY", "OPENAI_API_KEY")
SMOKE_FIXTURE = REPO_ROOT / "server" / "tests" / "ask" / "fixtures" / "eval" /"smoke_hand_built.json"
PROBE_CASES = ("smoke-games-last-week", "smoke-player-stat-finals", "smoke-year-required")
DEFAULT_PROBE_OUT = REPO_ROOT / "docs" / "verification" / "ask-interpreter-probe.json"


def load_keys(env_file: str | None) -> dict[str, str]:
    keys = {name: os.environ[name] for name in KEY_NAMES if os.environ.get(name)}
    if env_file:
        for line in Path(env_file).read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            name = name.removeprefix("export ").strip()
            if name in KEY_NAMES and name not in keys:
                keys[name] = value.strip().strip("'\"")
    return keys


def build_adapters(keys, args):
    adapters = {}
    if keys.get("TYPESAFE_API_KEY"):
        adapters["jev"] = JevAdapter(keys["TYPESAFE_API_KEY"], timeout_s=args.timeout)
    if keys.get("OPENAI_API_KEY"):
        adapters["gpt-4.1-mini"] = OpenAIResponsesAdapter(
            keys["OPENAI_API_KEY"], OpenAIConfig(model=BASELINE_MODEL, timeout_s=args.timeout)
        )
        for model in args.luna_models:
            adapters[model] = OpenAIResponsesAdapter(
                keys["OPENAI_API_KEY"],
                OpenAIConfig(model=model, reasoning_effort=args.luna_effort, timeout_s=args.timeout),
            )
    return adapters


def single(name, adapter):
    return Configuration(name, adapter, ThresholdCascadePolicy(adapter.model))


def probe(args) -> int:
    keys = load_keys(args.env_file)
    print("keys present:", sorted(keys))  # names only
    adapters = build_adapters(keys, args)
    cases = {c["id"]: LabeledCase.from_json(c) for c in json.loads(SMOKE_FIXTURE.read_text())["cases"]}
    guard = SpendGuard(args.spend_cap)
    entries = []
    for name, adapter in adapters.items():
        for case_id in PROBE_CASES:
            case = cases[case_id]
            outcome = drive(single(name, adapter), case.question, case.context, case.candidates,
                            guard=guard, deadline_ms=args.deadline_ms)
            first = outcome.attempts[0]
            entry = {
                "config": name,
                "case_id": case_id,
                "question": case.question,
                "expected_action": case.action,
                "decision": outcome.decision.model_dump(mode="json"),
                "request": outcome.request.model_dump(mode="json") if outcome.request is not None else None,
                "output": first.output.model_dump(mode="json"),
                "normalization": first.normalization.model_dump(mode="json") if first.normalization else None,
            }
            entries.append(entry)
            md = first.output.metadata
            print(f"{name:14} {case_id:26} outcome={first.output.outcome:12} action={outcome.decision.action:10}"
                  f" resolved={md.resolved_model} {md.latency_ms}ms ${md.usage.cost_usd or 0:.6f}"
                  f" {first.output.error_code or ''}")
    doc = {
        "purpose": "Live access probe for #199: confirms provider access, resolved model IDs, and response "
                   "shapes. Hand-built candidates; not an accuracy measurement.",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "providers": {
            name: {"adapter": a.name, "model": a.model,
                   "reasoning_effort": getattr(getattr(a, "config", None), "reasoning_effort", None)}
            for name, a in adapters.items()
        },
        "spend": {"cap_usd": guard.cap_usd, "spent_usd": round(guard.spent_usd, 6),
                  "note": "List-price estimate from reported token usage, not a billing record."},
        "results": entries,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=1) + "\n")
    print(f"spent ${guard.spent_usd:.6f} of ${guard.cap_usd:.2f}; wrote {out}")
    return 0


def load_lookup(spec: str):
    module_name, _, attr = spec.partition(":")
    factory = getattr(importlib.import_module(module_name), attr)
    return factory()


def run_command(args) -> int:
    keys = load_keys(args.env_file)
    adapters = build_adapters(keys, args)
    cases = [LabeledCase.from_json(c) for c in json.loads(Path(args.cases).read_text())["cases"]]
    if args.lookup:
        lookup = load_lookup(args.lookup)
        provider = lambda case: lookup.lookup(case.question, case.context)  # noqa: E731
        expand = lookup.expand
        candidate_source = f"lookup:{args.lookup}:{getattr(lookup, 'alias_version', '?')}"
    elif args.allow_hand_built:
        provider, expand, candidate_source = embedded_candidates, None, "hand-built (not valid for #199 decision)"
    else:
        print("error: pass --lookup (candidate lookup from #200) or --allow-hand-built", file=sys.stderr)
        return 2

    luna = adapters.get(args.luna_models[0]) if args.luna_models else None
    configs = []
    for name in args.configs:
        if name == "jev+luna":
            configs.append(Configuration(
                f"jev->{luna.model}", adapters["jev"],
                ThresholdCascadePolicy(JEV_MODEL, fallback=("openai_responses", luna.model)), fallback=luna,
            ))
        elif name == "luna":
            configs.append(single(luna.model, luna))
        else:
            configs.append(single(name, adapters[name]))

    guard = SpendGuard(args.spend_cap)
    outcome = run(cases, provider, configs, guard, deadline_ms=args.deadline_ms, expand=expand)
    doc = report(cases, outcome, configs, guard, {
        "purpose": "#199 interpreter comparison",
        "cases_file": str(Path(args.cases)),
        "candidate_source": candidate_source,
        "thresholds": "uncalibrated defaults" if not args.thresholds_note else args.thresholds_note,
    })
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=1) + "\n")
    for name, summary in doc["configs"].items():
        print(f"{name:28} accuracy={summary['complete_request_accuracy']} guesses={summary['schema_valid_guesses']}"
              f" p50={summary['latency_ms']['median']}ms cost/success={summary['cost_per_successful_answer_usd']}")
    print(f"spent ${guard.spent_usd:.6f} of ${guard.cap_usd:.2f}; wrote {out}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--env-file", help="dotenv file to read API keys from (values are never printed)")
    parser.add_argument("--timeout", type=float, default=20.0, help="per-request provider timeout, seconds")
    parser.add_argument("--deadline-ms", type=int, default=30_000, help="per-question deadline across attempts")
    parser.add_argument("--luna-models", nargs="*", default=["gpt-6-luna"])
    parser.add_argument("--luna-effort", default="low", help="reasoning.effort for Luna models")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("probe", help="live access probe")
    p.add_argument("--spend-cap", type=float, default=0.50)
    p.add_argument("--out", default=str(DEFAULT_PROBE_OUT))
    p.set_defaults(func=probe)

    r = sub.add_parser("run", help="full labeled comparison")
    r.add_argument("--cases", required=True)
    r.add_argument("--lookup", help="module:factory returning a CandidateLookup (#200)")
    r.add_argument("--allow-hand-built", action="store_true")
    r.add_argument("--configs", nargs="+", default=["jev", "gpt-4.1-mini", "luna", "jev+luna"])
    r.add_argument("--spend-cap", type=float, default=3.00)
    r.add_argument("--thresholds-note", default=None)
    r.add_argument("--out", default=str(REPO_ROOT / "docs" / "verification" / "ask-interpreter-eval.json"))
    r.set_defaults(func=run_command)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
