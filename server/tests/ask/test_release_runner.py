"""Release report creation must work with the CLI's relative manifest path."""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from server.ask.eval.runner import DriveResult
from server.ask.interpreters.tiered import Tier, TieredAdapter
from server.ask.models.common import DateRange
from server.ask.models.request import GameSearchRequest
from server.ask.protocols import AcceptDecision


def test_relative_manifest_writes_report_and_refuses_repeat(tmp_path, monkeypatch):
    repo = Path(__file__).resolve().parents[3]
    spec = importlib.util.spec_from_file_location("release_runner", repo / "scripts/ask/release.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "frozen_files", lambda: {})
    monkeypatch.chdir(tmp_path)
    cli = tmp_path / "scripts/ask/evaluate.py"
    cli.parent.mkdir(parents=True)
    cli.write_text("def load_keys(path):\n"
                   "    return {'OPENAI_API_KEY': 'offline', 'TYPESAFE_API_KEY': 'offline'}\n")
    request = GameSearchRequest(dates=DateRange(start=dt.date(2024, 1, 2), end=dt.date(2024, 1, 2)))
    fixture = tmp_path / "cases.json"
    fixture.write_text(json.dumps({"cases": [
        {"id": f"offline-{index}", "question": f"Offline runner check {index}",
         "reference_time": "2026-09-29T12:00:00-04:00",
         "expected": {"action": "accept", "request": request.model_dump(mode="json")}}
        for index in range(100)
    ]}))
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"cases_file": "cases.json", "cases_sha256": module.digest(fixture),
                                    "files_sha256": {}, "configuration": module.CONFIG,
                                    "gates": module.GATES, "spend_cap_usd": 0.1,
                                    "purpose": "offline regression"}))
    adapter = TieredAdapter([Tier("jev", SimpleNamespace(name="fake", model="fake"), 0.85)])
    monkeypatch.setattr(module, "build_cascade", lambda config: adapter)
    result = DriveResult(decision=AcceptDecision(reason="offline regression"), request=request,
                         attempts=[], expanded_fields=[], latency_ms=0, cost_usd=0, fallback_used=False)
    monkeypatch.setattr(module, "drive", lambda *args, **kwargs: result)
    args = SimpleNamespace(manifest="manifest.json", env_file=None, out="report.json")
    module.live(args)
    report = json.loads((tmp_path / "report.json").read_text())
    assert report["manifest_file"] == "manifest.json"
    assert len(report["cases"]) == 100
    assert report["summary"]["correct"] == 100
    assert report["spend"]["list_price_estimate_usd"] == 0
    assert len((tmp_path / "report.jsonl").read_text().splitlines()) == 100
    # A second run could spend again. It must be rejected before interpretation.
    with pytest.raises(FileExistsError):
        module.live(args)
