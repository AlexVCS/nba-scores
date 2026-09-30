"""Measure candidate lookup against a labeled question file.

Reports, per #200:
- recall per field: share of gold values present in the candidate set
- candidate-set size (all fields together): median and max
- lookup latency: median and p95 (warm), plus the one-time index load
- correct abstention: share of labeled "no valid match" fields that got no candidates

Labels format: see server/tests/ask/fixtures/candidates_dev_questions.json.
"""
from __future__ import annotations

import datetime as dt
import json
import statistics
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from server.ask.candidates.lookup import CandidateLookupService
from server.ask.models.candidates import CANDIDATE_FIELDS, Candidate, CandidateLookupResult
from server.ask.models.request import AskContext

DEV_SET = Path(__file__).resolve().parents[2] / "tests" / "ask" / "fixtures" / "candidates_dev_questions.json"


def load_questions(path: Path = DEV_SET) -> tuple[dict, list[dict]]:
    data = json.loads(Path(path).read_text())
    return data, data["questions"]


def context_for(question: dict, default_reference_time: str) -> AskContext:
    ctx = question.get("context", {})
    return AskContext(
        reference_time=dt.datetime.fromisoformat(question.get("reference_time", default_reference_time)),
        route=ctx.get("route"),
        view_date=dt.date.fromisoformat(ctx["view_date"]) if ctx.get("view_date") else None,
        game_id=ctx.get("game_id"),
        playoff_season=ctx.get("playoff_season"),
    )


def candidate_key(candidate: Candidate) -> Any:
    """Comparable form of a candidate's value, matching the label format."""
    v = candidate.value
    if v.kind == "player":
        return v.player.player_id
    if v.kind == "team":
        return v.team.team_id
    if v.kind == "season":
        return v.season
    if v.kind == "round":
        return v.round + (f".{v.conference}" if v.conference else "")
    if v.kind == "game_number":
        return v.game_number
    if v.kind == "location":
        return v.location.city
    return v  # dates are matched by date_matches


def date_matches(gold: dict, candidate: Candidate) -> bool:
    v = candidate.value
    c = v.components
    if "start" in gold:
        start, end = dt.date.fromisoformat(gold["start"]), dt.date.fromisoformat(gold.get("end", gold["start"]))
        if v.resolved is not None:
            return v.resolved.start == start and v.resolved.end == end
        if c.kind == "calendar_date" and c.year is not None:
            return start == end == dt.date(c.year, c.month, c.day)
        if c.kind == "calendar_range" and c.year is not None and c.end_year is not None:
            return (dt.date(c.year, c.month, c.day), dt.date(c.end_year, c.end_month, c.end_day)) == (start, end)
        return False
    # {"month": m, "day": d, "year": null}: a calendar date that needs a year
    return (
        c.kind == "calendar_date" and c.year is None and v.unresolved_reason == "year_required"
        and c.month == gold["month"] and c.day == gold["day"]
    )


def contains(result: CandidateLookupResult, field_name: str, gold: Any) -> bool:
    candidates = result.sets[field_name].candidates
    if field_name == "date":
        return any(date_matches(gold, c) for c in candidates)
    return any(candidate_key(c) == gold for c in candidates)


@dataclass
class Report:
    questions: int = 0
    gold: dict[str, int] = field(default_factory=lambda: {f: 0 for f in CANDIDATE_FIELDS})
    found: dict[str, int] = field(default_factory=lambda: {f: 0 for f in CANDIDATE_FIELDS})
    questions_all_gold: int = 0
    questions_with_gold: int = 0
    abstain_total: int = 0
    abstain_correct: int = 0
    ambiguous_total: int = 0
    ambiguous_correct: int = 0
    forbidden_leaks: int = 0
    sizes: list[int] = field(default_factory=list)
    latencies_ms: list[float] = field(default_factory=list)
    load_ms: float = 0.0
    misses: list[str] = field(default_factory=list)

    def recall(self, field_name: str | None = None) -> float | None:
        gold = sum(self.gold.values()) if field_name is None else self.gold[field_name]
        found = sum(self.found.values()) if field_name is None else self.found[field_name]
        return None if gold == 0 else found / gold

    def as_dict(self) -> dict:
        lat = sorted(self.latencies_ms)
        return {
            "questions": self.questions,
            "recall": {f: self.recall(f) for f in CANDIDATE_FIELDS},
            "recall_counts": {f: [self.found[f], self.gold[f]] for f in CANDIDATE_FIELDS},
            "recall_overall": self.recall(),
            "questions_with_every_gold_value": [self.questions_all_gold, self.questions_with_gold],
            "correct_abstention": [self.abstain_correct, self.abstain_total],
            "ambiguity_kept_open": [self.ambiguous_correct, self.ambiguous_total],
            "forbidden_candidates_offered": self.forbidden_leaks,
            "candidate_set_size": {"median": statistics.median(self.sizes), "max": max(self.sizes)},
            "latency_ms": {
                "median": round(statistics.median(lat), 3),
                "p95": round(lat[min(len(lat) - 1, int(round(0.95 * (len(lat) - 1))))], 3),
                "max": round(lat[-1], 3),
                "index_load": round(self.load_ms, 1),
            },
            "misses": self.misses,
        }


def evaluate(path: Path = DEV_SET, repeats: int = 5, service: CandidateLookupService | None = None) -> Report:
    meta, questions = load_questions(path)
    report = Report(questions=len(questions))
    started = time.perf_counter()
    service = service or CandidateLookupService()
    service.lookup("warm up", context_for({}, meta["default_reference_time"]))
    report.load_ms = (time.perf_counter() - started) * 1000

    for q in questions:
        context = context_for(q, meta["default_reference_time"])
        result = None
        for _ in range(repeats):
            t0 = time.perf_counter()
            result = service.lookup(q["question"], context)
            report.latencies_ms.append((time.perf_counter() - t0) * 1000)
        assert result is not None
        report.sizes.append(sum(len(s.candidates) for s in result.sets.values()))

        gold = q.get("gold", {})
        has_gold, all_found = False, True
        for field_name, values in gold.items():
            for value in values:
                has_gold = True
                report.gold[field_name] += 1
                if contains(result, field_name, value):
                    report.found[field_name] += 1
                else:
                    all_found = False
                    report.misses.append(f"{q['id']} {field_name} missing {value!r}")
        if has_gold:
            report.questions_with_gold += 1
            report.questions_all_gold += all_found

        abstain_fields = list(CANDIDATE_FIELDS) if q.get("expect_nothing") else q.get("expect_no_candidates", [])
        for field_name in abstain_fields:
            report.abstain_total += 1
            if result.sets[field_name].status != "candidates":
                report.abstain_correct += 1
            else:
                labels = [c.label for c in result.sets[field_name].candidates][:3]
                report.misses.append(f"{q['id']} {field_name} should abstain, offered {labels}")

        for field_name in q.get("expect_ambiguous", []):
            report.ambiguous_total += 1
            s = result.sets[field_name]
            if len(s.candidates) > 1 or s.truncated:
                report.ambiguous_correct += 1
            else:
                report.misses.append(f"{q['id']} {field_name} should stay ambiguous, got {[c.label for c in s.candidates]}")

        for field_name, values in q.get("forbid", {}).items():
            for value in values:
                if contains(result, field_name, value):
                    report.forbidden_leaks += 1
                    report.misses.append(f"{q['id']} {field_name} offered forbidden {value!r}")
    return report


def format_report(report: Report) -> str:
    d = report.as_dict()
    lines = [f"questions: {d['questions']}", "recall per field:"]
    for f in CANDIDATE_FIELDS:
        found, gold = d["recall_counts"][f]
        if gold:
            lines.append(f"  {f:<12} {found:>3}/{gold:<3} {found / gold:6.1%}")
    lines.append(f"  {'overall':<12} {sum(report.found.values()):>3}/{sum(report.gold.values()):<3} {d['recall_overall']:6.1%}")
    a, b = d["questions_with_every_gold_value"]
    lines.append(f"questions with every gold value: {a}/{b}")
    a, b = d["correct_abstention"]
    lines.append(f"correct abstention: {a}/{b}" + (f" ({a / b:.1%})" if b else ""))
    a, b = d["ambiguity_kept_open"]
    lines.append(f"ambiguity kept open: {a}/{b}")
    lines.append(f"forbidden candidates offered: {d['forbidden_candidates_offered']}")
    s = d["candidate_set_size"]
    lines.append(f"candidate-set size: median {s['median']}, max {s['max']}")
    lat = d["latency_ms"]
    lines.append(f"latency (warm): median {lat['median']} ms, p95 {lat['p95']} ms, max {lat['max']} ms; index load {lat['index_load']} ms")
    if d["misses"]:
        lines.append("misses:")
        lines.extend(f"  {m}" for m in d["misses"])
    return "\n".join(lines)
