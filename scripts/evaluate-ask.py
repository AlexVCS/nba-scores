#!/usr/bin/env python3
"""Run the production parser on seed or held-out questions. Never fetch NBA data."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from server.models.ask import AskInterpretation
from server.services import ask_parser

# https://developers.openai.com/api/docs/models/gpt-4.1-mini
# https://developers.openai.com/api/docs/models/gpt-4.1-nano
PRICES = {
    "gpt-4.1-mini": (0.40, 1.60), "gpt-4.1-nano": (0.10, 0.40),
    "gpt-4.1-mini-2025-04-14": (0.40, 1.60),
    "gpt-4.1-nano-2025-04-14": (0.10, 0.40),
}
DEFAULT_MODELS = ["gpt-4.1-mini-2025-04-14", "gpt-4.1-nano-2025-04-14"]
FIELDS = ("intent", "operation", "mentions", "date_expressions", "round_mention", "game_number", "statistics")


def canonical(value):
    if isinstance(value, str):
        return " ".join(value.casefold().split())
    if isinstance(value, dict):
        return {key: canonical(item) for key, item in sorted(value.items())}
    if isinstance(value, list):
        return sorted((canonical(item) for item in value), key=lambda item: json.dumps(item, sort_keys=True))
    return value


def semantic_score(expected, actual):
    """All selectors count, including unexpected extras. Schema-valid guesses fail."""
    try:
        AskInterpretation.model_validate(actual)
    except (ValueError, TypeError):
        return False, {field: False for field in (*FIELDS, "clarification", "schema")}
    checks = {field: canonical(actual[field]) == canonical(expected[field]) for field in FIELDS}
    expected_ambiguities = {item["field"] for item in expected["ambiguities"]}
    actual_ambiguities = {item["field"] for item in actual["ambiguities"]}
    checks["clarification"] = expected_ambiguities == actual_ambiguities
    checks["schema"] = True
    checks["unsupported"] = bool(expected["unsupported_reason"]) == bool(actual["unsupported_reason"])
    return all(checks.values()), checks


def reservation(payload, model):
    # One token per UTF-8 byte of the WHOLE request plus framing allowance.
    # This deliberately overestimates tokenization rather than dividing chars by four.
    upper_input = len(json.dumps(payload, ensure_ascii=False).encode("utf-8")) + 2048
    inp, out = PRICES[model]
    return (upper_input * inp + payload["max_output_tokens"] * out) / 1_000_000


def run_case(case, model):
    started = time.perf_counter()
    try:
        parsed = ask_parser.parse_ask(case["utterance"])
        actual = parsed.interpretation.model_dump()
        usage = parsed.metadata.usage.model_dump()
        variants = [case["expected"], *case.get("alternatives", [])]
        scored = [semantic_score(expected, actual) for expected in variants]
        passed, checks = max(scored, key=lambda result: sum(result[1].values()))
        inp, out = PRICES[model]
        list_price_cost = ((usage["input_tokens"] * inp + usage["output_tokens"] * out) / 1_000_000
                    if usage["input_tokens"] is not None and usage["output_tokens"] is not None else None)
        return {"id": case["id"], "passed": passed, "checks": checks, "actual": actual,
                "usage": usage, "list_price_cost_usd": list_price_cost, "error": None,
                "latency_ms": round((time.perf_counter() - started) * 1000, 1)}
    except ask_parser.AskParserError as exc:
        return {"id": case["id"], "passed": False, "checks": {"schema": False}, "actual": None,
                "usage": None, "list_price_cost_usd": None, "error": type(exc).__name__, "provider_code": getattr(exc, "code", None),
                "latency_ms": round((time.perf_counter() - started) * 1000, 1)}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--split", choices=["seed", "holdout"], default="seed")
    cli.add_argument("--models", nargs="+", choices=list(PRICES), default=DEFAULT_MODELS)
    cli.add_argument("--max-cost", type=float, default=1.0)
    cli.add_argument("--repeat", type=int, default=1)
    cli.add_argument("--limit", type=int)
    cli.add_argument("--output", type=Path)
    cli.add_argument("--offline", action="store_true")
    args = cli.parse_args()
    if not math.isfinite(args.max_cost) or args.max_cost < 0 or not 1 <= args.repeat <= 5:
        cli.error("Cost must be finite and nonnegative; repeat must be 1 to 5")
    path = ROOT / "server/tests/fixtures" / ("ask_seed.json" if args.split == "seed" else "ask_heldout.json")
    cases = json.loads(path.read_text())
    assert len(cases) == (25 if args.split == "seed" else 75), "Wrong fixture count"
    assert len({case["id"] for case in cases}) == len(cases), "Duplicate case IDs"
    for case in cases:
        assert 0 < len(case["utterance"]) <= ask_parser.MAX_INPUT_CHARS
        for expected in [case["expected"], *case.get("alternatives", [])]:
            AskInterpretation.model_validate(expected)
    if args.limit:
        cases = cases[:args.limit]
    if args.offline:
        print(json.dumps({"fixture_schema_valid": True, "cases": len(cases), "live_calls": 0}))
        return 0
    if os.getenv("ASK_PARSER_PROVIDER", "openai") != "openai" or os.getenv("OPENAI_RESPONSES_URL", "https://api.openai.com/v1/responses") != "https://api.openai.com/v1/responses":
        cli.error("This priced comparison only supports the official OpenAI Responses endpoint")
    report = {"split": args.split, "fixture_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
              "prompt_sha256": hashlib.sha256(ask_parser._instructions().encode()).hexdigest(),
              "cost_basis": "regular token list prices; excludes discounts and complimentary tokens",
              "actual_billed_cost_usd": None,
              "reserved_or_list_price_usd": 0.0, "models": []}
    original_model = os.environ.get("ASK_PARSER_MODEL")
    try:
        for model in args.models:
            os.environ["ASK_PARSER_MODEL"] = model
            rows = []
            for repeat in range(args.repeat):
                for case in cases:
                    reserve = reservation(ask_parser.build_request(case["utterance"], model), model)
                    if report["reserved_or_list_price_usd"] + reserve > args.max_cost:
                        print("Budget exhausted before the next request", file=sys.stderr)
                        break
                    report["reserved_or_list_price_usd"] += reserve
                    row = run_case(case, model)
                    row["repeat"] = repeat + 1
                    if row["list_price_cost_usd"] is not None:
                        report["reserved_or_list_price_usd"] += row["list_price_cost_usd"] - reserve
                    rows.append(row)
                    print(json.dumps({"model": model, "id": row["id"], "passed": row["passed"], "error": row["error"]}), flush=True)
                    # Three transport/provider failures are sufficient evidence of unavailable access.
                    if len(rows) >= 3 and all(x["error"] == "AskParserUnavailable" for x in rows[-3:]):
                        break
                if len(rows) >= 3 and all(x["error"] == "AskParserUnavailable" for x in rows[-3:]):
                    break
            latencies = sorted(row["latency_ms"] for row in rows)
            summary = {"model": model, "attempted": len(rows), "passed": sum(x["passed"] for x in rows),
                       "median_ms": statistics.median(latencies) if latencies else None,
                       "p95_ms": latencies[math.ceil(len(latencies)*.95)-1] if latencies else None,
                       "list_price_cost_usd": sum(row["list_price_cost_usd"] or 0 for row in rows),
                       "unknown_usage_requests": sum(row["list_price_cost_usd"] is None for row in rows),
                       "field_pass_counts": {field: sum(row["checks"].get(field, False) for row in rows) for field in (*FIELDS, "clarification", "schema")},
                       "results": rows}
            report["models"].append(summary)
            print(json.dumps({key: value for key, value in summary.items() if key != "results"}), flush=True)
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(json.dumps(report, indent=2) + "\n")
    finally:
        if original_model is None:
            os.environ.pop("ASK_PARSER_MODEL", None)
        else:
            os.environ["ASK_PARSER_MODEL"] = original_model
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
