#!/usr/bin/env python3
"""Check Ask's retrieved answers against source-cited gold values (ADR 0009).

The release evaluation scores interpretation only. This check starts from a fully
specified, already interpreted request, so it makes no interpreter or paid model
call. It runs the production execution path (``AskPipeline._execute``: answer
cache, resolver tools, stats.nba primary and Basketball-Reference fallback,
response validation), then compares the response to gold values read from a
cited source. It also records the wall time from request to answer ready.

A case is ``wrong`` when the response states something false: an answer whose
checked values differ from gold, an answer where gold expects none, or a
``not_found`` where gold has a value. ``unavailable`` and clarifications state
nothing and count as ``no_answer``. Unverified gold (``verified: false``) is run
and timed but never scored. Any wrong answer or error exits nonzero.

    python scripts/ask/answer_check.py --gold server/tests/ask/fixtures/answers/answer-gold-draft.json \
        --out answer-check.json
"""

from __future__ import annotations

import argparse
from collections import Counter
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
from typing import Callable

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from server.ask.budget import DailyBudget  # noqa: E402
from server.ask.cache import AskCache  # noqa: E402
from server.ask.config import AskConfig  # noqa: E402
from server.ask.eval.runner import percentile  # noqa: E402
from server.ask.models.request import ASK_REQUEST_ADAPTER, AskContext  # noqa: E402
from server.ask.pipeline import AskPipeline  # noqa: E402
from server.ask.present import interpretation  # noqa: E402
from server.ask.resolution import ResolutionStore  # noqa: E402
from server.ask.resolvers import seasons  # noqa: E402
from server.ask.tools import REGISTRY  # noqa: E402

GATES = {"wrong_answers_max": 0, "errors_max": 0, "p95_latency_ms_max": 4000}
OUTCOMES = {"answer", "not_found", "unsupported", "needs_clarification", "unavailable"}
MATCHES = {"exact", "round", "unordered", "length", "one_of"}
# Outcomes that render a claim. Any other outcome renders no fact, right or wrong.
CLAIMS = {"answer", "not_found"}
_SEGMENT = re.compile(r"([A-Za-z_]\w*)((?:\[[^\]]*\])*)")


# -- gold --------------------------------------------------------------------------------------


class GoldCase:
    def __init__(self, row: dict):
        self.id = row["id"]
        self.family = row["family"]
        self.tags = list(row.get("tags", []))
        self.question = row.get("question", "")
        self.request = ASK_REQUEST_ADAPTER.validate_python(row["request"])
        self.verified = row["verified"]
        self.expected_outcome = row.get("expected_outcome")
        self.checks = row.get("checks")
        self.source = row.get("source")
        if self.request.intent != self.family:
            raise ValueError(f"{self.id}: family {self.family!r} differs from request intent {self.request.intent!r}")
        if self.verified is not True and self.verified is not False:
            raise ValueError(f"{self.id}: verified must be true or false")
        if not self.verified:
            # Unverified gold is never scored, so it must not carry values to mislead a reviewer.
            if self.checks is not None or self.expected_outcome is not None:
                raise ValueError(f"{self.id}: unverified cases leave expected_outcome and checks null")
            return
        if self.expected_outcome not in OUTCOMES:
            raise ValueError(f"{self.id}: expected_outcome must be one of {sorted(OUTCOMES)}")
        sources = self.source if isinstance(self.source, list) else [self.source]
        if not sources or any(not isinstance(s, dict) or not str(s.get("url", "")).startswith("https://")
                              or not s.get("read") or not s.get("checked_at") for s in sources):
            raise ValueError(f"{self.id}: verified gold needs a source with url, read and checked_at")
        if not isinstance(self.checks, list) or not self.checks:
            raise ValueError(f"{self.id}: verified gold needs at least one check")
        for check in self.checks:
            if not isinstance(check.get("path"), str) or "value" not in check or check.get("match", "exact") not in MATCHES:
                raise ValueError(f"{self.id}: invalid check {check!r}")
            if check.get("match") == "round" and not isinstance(check.get("digits"), int):
                raise ValueError(f"{self.id}: round checks need integer digits")
            parse_path(check["path"])


def load_gold(path: Path) -> tuple[dict, list[GoldCase]]:
    doc = json.loads(path.read_text())
    cases = [GoldCase(row) for row in doc["cases"]]
    if not cases:
        raise ValueError("gold has no cases")
    if len({c.id for c in cases}) != len(cases):
        raise ValueError("duplicate case id")
    unknown = {c.family for c in cases} - set(REGISTRY)
    if unknown:
        raise ValueError(f"unknown tool families: {sorted(unknown)}")
    AskContext(reference_time=dt.datetime.fromisoformat(doc["reference_time"]))
    return doc, cases


# -- paths and comparison ----------------------------------------------------------------------


def parse_path(path: str) -> list[tuple[str, str]]:
    """``result.rows[team.tricode=BOS].wins`` -> keys and selectors, in order.

    A selector is ``[n]`` (index), ``[*]`` (the rest of the path maps over the
    list) or ``[dotted.key=value]`` (the one item whose value matches)."""
    # Selectors may contain dots, so split on dots outside brackets only.
    depth, start, pieces = 0, 0, []
    for i, ch in enumerate(path):
        depth += (ch == "[") - (ch == "]")
        if ch == "." and depth == 0:
            pieces.append(path[start:i])
            start = i + 1
    pieces.append(path[start:])
    tokens = []
    for piece in pieces:
        match = _SEGMENT.fullmatch(piece)
        if match is None:
            raise ValueError(f"invalid path segment {piece!r} in {path!r}")
        tokens.append(("key", match[1]))
        tokens += [("select", s) for s in re.findall(r"\[([^\]]*)\]", match[2])]
    return tokens


class PathError(LookupError):
    pass


def _dig(value, dotted: str):
    for key in dotted.split("."):
        if not isinstance(value, dict) or key not in value:
            raise PathError(f"missing {key!r}")
        value = value[key]
    return value


def _walk(value, tokens):
    for i, (kind, text) in enumerate(tokens):
        if kind == "key":
            value = _dig(value, text)
            continue
        if not isinstance(value, list):
            raise PathError(f"[{text}] applied to a non-list")
        if text == "*":
            return [_walk(item, tokens[i + 1:]) for item in value]
        if re.fullmatch(r"-?\d+", text):
            index = int(text)
            if not -len(value) <= index < len(value):
                raise PathError(f"index {index} out of range ({len(value)} items)")
            value = value[index]
            continue
        key, sep, wanted = text.partition("=")
        if not sep:
            raise PathError(f"invalid selector [{text}]")
        found = []
        for item in value:
            try:
                if str(_dig(item, key)) == wanted:
                    found.append(item)
            except PathError:
                continue
        if len(found) != 1:
            raise PathError(f"[{text}] matched {len(found)} items")
        value = found[0]
    return value


def resolve_path(doc, path: str):
    """The value at ``path`` in a response document (``AskResponse`` as JSON)."""
    return _walk(doc, parse_path(path))


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def compare(actual, check: dict) -> str | None:
    """None when ``actual`` satisfies the check, else a short reason."""
    expected, match = check["value"], check.get("match", "exact")
    if match == "length":
        if not isinstance(actual, list):
            return "not a list"
        return None if len(actual) == expected else f"length {len(actual)} != {expected}"
    if match == "one_of":
        return None if actual in expected else f"{actual!r} not in {expected!r}"
    if match == "unordered":
        if not isinstance(actual, list):
            return "not a list"
        key = lambda v: json.dumps(v, sort_keys=True)
        return None if sorted(map(key, actual)) == sorted(map(key, expected)) else "different members"
    if match == "round":
        # Gold is the source's displayed value; the answer's unrounded value must
        # round to it (half a unit in the last shown digit either way).
        values = actual if isinstance(expected, list) else [actual]
        wanted = expected if isinstance(expected, list) else [expected]
        if not isinstance(values, list) or len(values) != len(wanted):
            return "different number of values"
        slack = 0.5 * 10 ** -check["digits"] + 1e-9
        for got, want in zip(values, wanted):
            if want is None:
                if got is not None:
                    return f"{got!r} where the source has no value"
                continue
            if not _number(got) or not math.isfinite(got) or abs(got - want) > slack:
                return f"{got!r} does not round to {want!r} at {check['digits']} digits"
        return None
    # Exact: counts, ids, names and flags. 81 == 81.0, but True is not 1.
    if isinstance(actual, bool) != isinstance(expected, bool):
        return f"{actual!r} != {expected!r}"
    return None if actual == expected else f"{actual!r} != {expected!r}"


def score(case: GoldCase, response: dict | None, error: str | None) -> tuple[str, list[dict]]:
    """(status, diffs). Status: pass, wrong, no_answer, error or unverified."""
    if error is not None:
        return "error", [{"path": None, "reason": error}]
    outcome = response["outcome"]
    if not case.verified:
        return "unverified", []
    if outcome != case.expected_outcome:
        diff = [{"path": "outcome", "expected": case.expected_outcome, "actual": outcome,
                 "notice": (response.get("notice") or {}).get("code")}]
        return ("wrong" if outcome in CLAIMS else "no_answer"), diff
    diffs = []
    for check in case.checks:
        try:
            actual = resolve_path(response, check["path"])
            reason = compare(actual, check)
        except PathError as exc:
            actual, reason = None, f"path: {exc}"
        if reason is not None:
            diffs.append({"path": check["path"], "expected": check["value"], "actual": actual,
                          "match": check.get("match", "exact"), "reason": reason})
    return ("wrong" if diffs else "pass"), diffs


# -- execution ---------------------------------------------------------------------------------


class _NoModel:
    """Stands in for the interpreter: an answer check never interprets a question."""

    name, model = "openai_responses", "none"

    def estimate_cost(self, request):
        raise AssertionError("answer check must not estimate model cost")

    def interpret(self, request):
        raise AssertionError("answer check must not call a model")


class _NoPolicy:
    def decide(self, state):
        raise AssertionError("answer check must not run the cascade policy")


class _NoLookup:
    alias_version = "answer-check"

    def lookup(self, question, context):
        raise AssertionError("answer check must not look up candidates")

    def expand(self, question, context, field, previous):
        raise AssertionError("answer check must not look up candidates")


def build_pipeline(state_dir: Path) -> AskPipeline:
    """The production pipeline with every model-side component disabled."""
    config = AskConfig(enabled=True, state_dir=state_dir)
    return AskPipeline(config, lookup=_NoLookup(), adapter=_NoModel(), policy=_NoPolicy(),
                       cache=AskCache(max_entries=config.cache_max_entries, version=config.cache_version),
                       budget=DailyBudget(state_dir, 0.0), resolutions=ResolutionStore(state_dir / "resolution.sqlite3"))


def run_case(pipeline: AskPipeline, case: GoldCase, reference_time: dt.datetime, *,
             clock: Callable[[], float] = time.perf_counter, cold: bool = False) -> dict:
    """Execute one request as the pipeline does after accepting an interpretation."""
    # A fresh answer cache per case: repeated requests in one run never hit each other.
    pipeline.cache = AskCache(max_entries=pipeline.config.cache_max_entries, version=pipeline.config.cache_version)
    if cold:
        seasons._cache.clear()
    context = AskContext(reference_time=reference_time)
    readout = interpretation(None, None, context, case.request)
    response, error = None, None
    started = clock()
    try:
        deadline = pipeline._retrieval_deadline(time.monotonic())
        answer = pipeline._execute(case.question or case.id, case.request, readout, pipeline._info(), deadline)
        response = answer.model_dump(mode="json")
    except Exception as exc:  # noqa: BLE001 - recorded as an error case, never a pass
        error = f"{type(exc).__name__}: {str(exc)[:200]}"
    latency_ms = round((clock() - started) * 1000, 1)
    status, diffs = score(case, response, error)
    return {"case_id": case.id, "family": case.family, "tags": case.tags, "verified": case.verified,
            "status": status, "latency_ms": latency_ms, "outcome": response["outcome"] if response else None,
            "sources": [s["name"] for s in response["sources"]] if response else [],
            "notice": (response.get("notice") or {}).get("code") if response else None,
            "diffs": diffs, "response": response}


def summarize(rows: list[dict]) -> dict:
    latencies = [r["latency_ms"] for r in rows]
    statuses = Counter(r["status"] for r in rows)
    families: dict[str, Counter] = {}
    for row in rows:
        families.setdefault(row["family"], Counter())[row["status"]] += 1
    tags: dict[str, Counter] = {}
    for row in rows:
        for tag in row["tags"]:
            tags.setdefault(tag, Counter())[row["status"]] += 1
    return {"cases": len(rows), "scored": sum(1 for r in rows if r["verified"]),
            "statuses": {k: statuses.get(k, 0) for k in ("pass", "wrong", "no_answer", "error", "unverified")},
            "latency_ms": {"p50": percentile(latencies, 50), "p95": percentile(latencies, 95),
                           "max": max(latencies) if latencies else None},
            "by_family": {k: dict(v) for k, v in sorted(families.items())},
            "by_tag": {k: dict(v) for k, v in sorted(tags.items())},
            "sources_used": dict(Counter(s for r in rows for s in r["sources"]))}


def gate_results(summary: dict) -> dict:
    p95 = summary["latency_ms"]["p95"]
    return {"zero_wrong_answers": summary["statuses"]["wrong"] <= GATES["wrong_answers_max"],
            "zero_errors": summary["statuses"]["error"] <= GATES["errors_max"],
            "p95_latency": p95 is not None and p95 <= GATES["p95_latency_ms_max"]}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _commit() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
                                       stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def check(args) -> int:
    gold_path = Path(args.gold).resolve()
    doc, cases = load_gold(gold_path)
    if args.case:
        wanted = set(args.case)
        cases = [c for c in cases if c.id in wanted]
        if {c.id for c in cases} != wanted:
            raise ValueError(f"unknown case ids: {sorted(wanted - {c.id for c in cases})}")
    out_path = Path(args.out)
    journal_path = out_path.with_suffix(".jsonl")
    if out_path.exists():
        raise FileExistsError("report already exists; refusing to overwrite")
    reference_time = dt.datetime.fromisoformat(doc["reference_time"])
    rows = []
    started = time.perf_counter()
    # Exclusive creation also protects against simultaneous or repeated starts.
    with journal_path.open("x") as journal, tempfile.TemporaryDirectory(prefix="ask-answer-check-") as state:
        pipeline = build_pipeline(Path(state))
        for index, case in enumerate(cases, 1):
            row = run_case(pipeline, case, reference_time, cold=args.cold)
            journal.write(json.dumps(row) + "\n")
            journal.flush()
            rows.append(row)
            print(f"{index}/{len(cases)} {case.id}: {row['status']} {row['outcome']} "
                  f"{row['latency_ms']:.0f} ms {','.join(row['sources'])}", flush=True)
    summary = summarize(rows)
    gates = gate_results(summary)
    report = {"purpose": "Answer accuracy and time-to-answer for interpreted Ask requests (ADR 0009)",
              "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(), "commit": _commit(),
              "gold_file": str(gold_path.relative_to(ROOT)) if gold_path.is_relative_to(ROOT) else str(gold_path),
              "gold_sha256": digest(gold_path), "gold_draft": bool(doc.get("draft")),
              "cold": args.cold, "gates": GATES, "gate_results": gates,
              "passed": gates["zero_wrong_answers"] and gates["zero_errors"]
              and (gates["p95_latency"] or not args.enforce_latency),
              "summary": summary, "elapsed_seconds": round(time.perf_counter() - started, 3),
              "cases": rows}
    with out_path.open("x") as out:
        out.write(json.dumps(report, indent=1) + "\n")
    failures = [{"case_id": r["case_id"], "status": r["status"], "diffs": r["diffs"]}
                for r in rows if r["status"] in {"wrong", "error"}]
    print(json.dumps({"summary": summary, "gate_results": gates, "failures": failures, "out": str(out_path)}), flush=True)
    return 0 if report["passed"] else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--gold", required=True)
    parser.add_argument("--out", required=True, help="report JSON; a .jsonl journal is written beside it")
    parser.add_argument("--case", action="append", help="run only this case id (repeatable)")
    parser.add_argument("--cold", action="store_true", help="clear the Ask season-data cache before each case")
    parser.add_argument("--enforce-latency", action="store_true", help="also fail when p95 latency exceeds the gate")
    return check(parser.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
