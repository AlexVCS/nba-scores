"""Release preparation and report creation (ADR 0009), fully offline."""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from server.ask.eval.runner import DriveResult, LabeledCase
from server.ask.interpreters.tiered import Tier, TieredAdapter
from server.ask.models.common import DateRange
from server.ask.models.request import GameSearchRequest
from server.ask.protocols import AcceptDecision

REPO = Path(__file__).resolve().parents[3]
HEAD = "a" * 40
REQUEST = GameSearchRequest(dates=DateRange(start=dt.date(2024, 1, 2), end=dt.date(2024, 1, 2)))


def load(name: str):
    spec = importlib.util.spec_from_file_location(f"release_{name}", REPO / f"scripts/ask/{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses resolve annotations through sys.modules
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def module(tmp_path, monkeypatch):
    module = load("release")
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "frozen_files", lambda: {})
    monkeypatch.setattr(module, "head_commit", lambda: HEAD)
    monkeypatch.chdir(tmp_path)
    return module


def accept_case(index: int) -> dict:
    return {"id": f"offline-{index}", "question": f"Offline runner check {index}",
            "reference_time": "2026-09-29T12:00:00-04:00",
            "expected": {"action": "accept", "request": REQUEST.model_dump(mode="json")}}


def family_cases(module, per_family: int = 10) -> list[dict]:
    """Clarify and unsupported cases that name their family in a tag."""
    rows = []
    for family in module.FAMILIES:
        for index in range(per_family):
            expected = ({"action": "clarify", "clarify_field": "season"} if index % 2
                        else {"action": "unsupported", "unsupported_reason": "prediction"})
            rows.append({"id": f"unseen-{family}-{index}", "question": f"{family} question {index}",
                         "reference_time": "2026-09-29T12:00:00-04:00", "tags": [family], "expected": expected})
    return rows


def write_cases(path: Path, rows: list[dict]) -> Path:
    path.write_text(json.dumps({"cases": rows}))
    return path


def prepare_args(tmp_path, **overrides):
    values = {"cases": str(tmp_path / "cases.json"), "manifest": str(tmp_path / "manifest.json"),
              "spend_cap": 0.25, "spend_estimate": None, "frozen_commit": None,
              "min_cases": 80, "min_per_family": 10, "min_per_outcome": 10}
    return SimpleNamespace(**{**values, **overrides})


def fake_git(status: str = "", resolves: dict | None = None):
    def git(*args):
        if args[0] == "status":
            return status
        return (resolves or {}).get(args[-1].removesuffix("^{commit}"), HEAD)
    return git


def test_load_cases_size_is_configurable_and_keeps_integrity_checks(module, tmp_path):
    path = write_cases(tmp_path / "cases.json", [accept_case(i) for i in range(120)])
    with pytest.raises(ValueError, match="at least 150"):
        module.load_cases(path)
    assert len(module.load_cases(path, 120)) == 120
    rows = [accept_case(i) for i in range(3)]
    write_cases(path, rows + [{**rows[0], "question": "different"}])
    with pytest.raises(ValueError, match="unique"):
        module.load_cases(path, 1)
    write_cases(path, rows + [{**accept_case(9), "question": "  offline RUNNER check 0"}])
    with pytest.raises(ValueError, match="duplicate question"):
        module.load_cases(path, 1)


def test_coverage_counts_every_tool_family_and_rejects_gaps(module):
    cases = [LabeledCase.from_json(row) for row in family_cases(module)]
    assert len(module.FAMILIES) == 8
    counts = module.coverage(cases, 10, 10)
    assert counts["career_stats"] == {"accept": 0, "clarify": 5, "unsupported": 5, "total": 10}
    with pytest.raises(ValueError, match="team_records: 9"):
        module.coverage([c for c in cases if c.id != "unseen-team_records-0"], 10, 10)
    with pytest.raises(ValueError, match="clarify: 40"):
        module.coverage(cases, 10, 41)
    untagged = LabeledCase.from_json({**family_cases(module)[0], "id": "no-family", "tags": []})
    with pytest.raises(ValueError, match="exactly one tool family"):
        module.family_of(untagged)


def test_prepare_records_commit_coverage_tier_gates_and_spend_cap(module, tmp_path, monkeypatch):
    write_cases(tmp_path / "cases.json", family_cases(module))
    monkeypatch.setattr(module, "git", fake_git())
    module.prepare(prepare_args(tmp_path))
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest["frozen_commit"] == HEAD
    assert manifest["spend_cap_usd"] == 0.25
    assert manifest["case_minimums"] == {"cases": 80, "per_family": 10, "per_outcome": 10}
    assert set(manifest["family_counts"]) == set(module.FAMILIES)
    assert manifest["tier_gates"]["accepted_field_precision_min"] == 0.98
    assert manifest["tier_gates"]["coverage_min"] == 0.30
    assert manifest["tier_gates"]["tiers"]["jev"] == {"accept_min": 0.85}
    assert "disabled" in manifest["tier_gates"]["tiers"]["laya"]
    assert "8 ADR 0004 tool families" in manifest["scope"]


@pytest.mark.parametrize("overrides, git, message", [
    ({"spend_cap": None}, fake_git(), "spend-cap"),
    ({"spend_cap": 0.0}, fake_git(), "spend-cap"),
    ({"min_per_family": 0}, fake_git(), "at least 1"),
    ({"min_cases": 81}, fake_git(), "at least 81"),
    ({"frozen_commit": "old"}, fake_git(resolves={"old": "b" * 40}), "HEAD"),
    ({}, fake_git(status=" M server/ask/tools.py"), "uncommitted"),
])
def test_prepare_refuses_invalid_runs(module, tmp_path, monkeypatch, overrides, git, message):
    write_cases(tmp_path / "cases.json", family_cases(module))
    monkeypatch.setattr(module, "git", git)
    with pytest.raises(ValueError, match=message):
        module.prepare(prepare_args(tmp_path, **overrides))
    assert not (tmp_path / "manifest.json").exists()


def offline_run(module, tmp_path, monkeypatch, manifest_overrides=None, tier_outputs=()):
    cli = tmp_path / "scripts/ask/evaluate.py"
    cli.parent.mkdir(parents=True, exist_ok=True)
    cli.write_text("def load_keys(path):\n"
                   "    return {'OPENAI_API_KEY': 'offline', 'TYPESAFE_API_KEY': 'offline'}\n")
    fixture = write_cases(tmp_path / "cases.json", [accept_case(i) for i in range(100)])
    cases = module.load_cases(fixture, 100)
    minimums = {"cases": 100, "per_family": 0, "per_outcome": 0}
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({
        "cases_file": "cases.json", "cases_sha256": module.digest(fixture), "files_sha256": {},
        "configuration": module.CONFIG, "gates": module.GATES, "tier_gates": module.TIER_GATES,
        "frozen_commit": HEAD, "spend_cap_usd": 0.1, "purpose": "offline regression",
        "case_minimums": minimums, "family_counts": module.coverage(cases, 0, 0),
        **(manifest_overrides or {})}))
    sinks: list = []

    def recorder(adapter, tier, sink):
        sinks.append(sink)
        return adapter

    class Fake:
        name = model = "fake"

        def interpret(self, request):
            raise AssertionError("no provider calls")

    adapter = TieredAdapter([Tier("jev", Fake(), 0.85)])
    monkeypatch.setattr(module, "build_cascade", lambda config: adapter)
    monkeypatch.setattr(module, "Recorder", recorder)
    result = DriveResult(decision=AcceptDecision(reason="offline regression"), request=REQUEST,
                         attempts=[], expanded_fields=[], latency_ms=0, cost_usd=0, fallback_used=False)

    def drive(*args, **kwargs):
        sinks[0].extend(tier_outputs)
        return result

    monkeypatch.setattr(module, "drive", drive)
    return SimpleNamespace(manifest="manifest.json", env_file=None, out="report.json")


def test_relative_manifest_writes_report_and_refuses_repeat(module, tmp_path, monkeypatch):
    args = offline_run(module, tmp_path, monkeypatch)
    module.live(args)
    report = json.loads((tmp_path / "report.json").read_text())
    assert report["manifest_file"] == "manifest.json"
    assert report["frozen_commit"] == HEAD
    assert len(report["cases"]) == 100
    assert report["summary"]["correct"] == 100
    assert report["spend"]["list_price_estimate_usd"] == 0
    assert report["spend"]["cap_usd"] == 0.1
    assert report["gate_results"]["all_cases_scored"] is True
    # No clarification cases: a computed gate failure is final even while checks are pending.
    assert report["gate_results"]["clarification_accuracy"] is False
    assert report["system_gate_passed"] is False and report["release_passed"] is False
    assert report["tier_gates"]["tiers"]["jev"]["status"] == "pending"
    assert report["tier_gates"]["tiers"]["jev"]["passed"] is None
    assert "tier_gate.py" in report["tier_gates"]["tiers"]["jev"]["command"]
    assert report["tier_gates"]["tiers"]["laya"]["status"] == "not_run"
    assert report["answer_accuracy"] == {"status": "pending", "check": "scripts/ask/answer_check.py", "result": None}
    assert "not rendered answers" in report["summary_notes"]["schema_valid_guesses"]
    assert len((tmp_path / "report.jsonl").read_text().splitlines()) == 100
    assert report["journal_sha256"] == module.digest(tmp_path / "report.jsonl")
    # A second run could spend again. It must be rejected before interpretation.
    with pytest.raises(FileExistsError):
        module.live(args)


def test_passing_interpretation_gates_leave_the_verdict_pending(module, tmp_path, monkeypatch):
    args = offline_run(module, tmp_path, monkeypatch)
    summarize = module.summarize

    def with_outcomes(cases, scores):
        summary = summarize(cases, scores)
        for kind in ("clarification", "unsupported"):
            summary[kind].update(expected=1, correct=1)
        return summary

    monkeypatch.setattr(module, "summarize", with_outcomes)
    module.live(args)
    report = json.loads((tmp_path / "report.json").read_text())
    assert report["interpretation_gates_passed"] is True
    # Tier gates and rendered answers are not computed, so no pass is claimed.
    assert report["system_gate_passed"] is None and report["release_passed"] is None
    assert report["pending_checks"] == ["tier gate: jev", "rendered answer accuracy: scripts/ask/answer_check.py"]


@pytest.mark.parametrize("overrides, message", [
    ({"frozen_commit": "b" * 40}, "frozen commit"),
    ({"spend_cap_usd": None}, "spend_cap_usd"),
    ({"spend_cap_usd": 0}, "spend_cap_usd"),
    ({"tier_gates": {}}, "gates differ"),
    ({"family_counts": {}}, "family counts"),
])
def test_live_refuses_a_changed_or_incomplete_manifest(module, tmp_path, monkeypatch, overrides, message):
    args = offline_run(module, tmp_path, monkeypatch, overrides)
    with pytest.raises(ValueError, match=message):
        module.live(args)
    assert not (tmp_path / "report.jsonl").exists()


def test_tier_readings_count_accepted_fields_without_claiming_a_gate(module):
    output = {"outcome": "interpreted", "fields": [
        {"field": "intent", "confidence": 0.9}, {"field": "date", "confidence": 0.5},
        {"field": "teams", "confidence": None}]}
    rows = [{"case_id": f"c{i}", "tier_outputs": [{"tier": "jev", "output": output},
                                                  {"tier": "luna", "output": output}]} for i in range(60)]
    rows.append({"case_id": "u", "tier_outputs": [{"tier": "jev", "output": {"outcome": "unsupported"}}]})
    families = {row["case_id"]: "game_search" for row in rows} | {"u": "team_records"}
    tiers = module.tier_readings(module.TIER_GATES["tiers"], rows, families)
    jev = tiers["jev"]
    assert (jev["readings"], jev["accepted_readings"]) == (181, 61)
    assert jev["by_field"]["date"] == {"read": 60, "accepted": 0}
    assert jev["by_family"]["team_records"] == {"read": 1, "accepted": 1}
    assert jev["tolerated_accepted_errors"] == 1 and jev["small_sample"] is True
    assert jev["status"] == "pending" and jev["passed"] is None


def test_tier_thresholds_match_the_offline_tier_gate():
    release, tier_gate = load("release"), load("tier_gate")
    assert release.TIER_GATES["accepted_field_precision_min"] == tier_gate.PRECISION_MIN
    assert release.TIER_GATES["coverage_min"] == tier_gate.COVERAGE_MIN
    assert release.PROVISIONAL_COVERAGE == tier_gate.PROVISIONAL_COVERAGE
