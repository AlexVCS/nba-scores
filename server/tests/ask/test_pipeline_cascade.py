"""The live pipeline over the Jev -> Luna cascade: dev-only details and safe logs."""

from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from server.ask import router
from server.ask.cache import AskCache
from server.ask.config import AskConfig
from server.ask.interpreters.tiered import Tier, TieredAdapter
from server.ask.models.response import AskQuery
from server.ask.pipeline import AskPipeline
from server.ask.resolution import ResolutionStore
from server.main import app
from server.tests.ask.test_pipeline import NOW, Lookup
from server.tests.ask.test_tiered import CANDIDATES, Fake, sel

QUESTION = "How many career points does a distinctive-question-marker have?"
SECRET = "sk-test-secret-never-logged"


def build(tmp_path, *, dev: bool, jev: Fake | None = None):
    jev = jev or Fake("jev", sel("intent", "boxscore_stat", confidence=0.4))
    luna = Fake("luna", outcome="unsupported", reason="career_stats")
    # Priced model names, so the real daily budget accepts the reservation.
    jev.model, luna.model = "jev-1.13.0", "gpt-6-luna"
    adapter = TieredAdapter([Tier("jev", jev, 0.85), Tier("luna", luna, None)], veto_min=0.5)
    config = AskConfig(enabled=True, dev=dev, state_dir=tmp_path, api_key=SECRET, typesafe_api_key=SECRET)
    pipeline = AskPipeline(config, lookup=Lookup(CANDIDATES), adapter=adapter, cache=AskCache(),
                           resolutions=ResolutionStore(tmp_path / "resolutions.sqlite3"), clock=lambda: NOW)
    return pipeline, jev, luna


def test_dev_response_carries_per_field_decisions(tmp_path):
    pipeline, _, _ = build(tmp_path, dev=True)
    info = pipeline.answer(AskQuery(question=QUESTION)).interpreter
    assert info.field_tiers == {"intent": "luna"}
    (intent,) = info.field_decisions
    assert (intent.field, intent.decided_by, intent.outcome) == ("intent", "luna", "escalated")
    assert [(r.tier, r.status, r.confidence, r.action) for r in intent.reads] == [
        ("jev", "selected", 0.4, "escalated"), ("luna", "unsupported", None, "accepted")]
    assert info.fallback_used is True


def test_production_response_carries_no_details(tmp_path):
    pipeline, _, _ = build(tmp_path, dev=False)
    response = pipeline.answer(AskQuery(question=QUESTION))
    assert response.outcome == "unsupported"
    body = response.model_dump(mode="json")["interpreter"]
    assert body["field_tiers"] == {}
    assert "field_decisions" not in body
    # Source-aware copy keeps working without details.
    assert body["model_called"] is True and body["fallback_used"] is True


@pytest.mark.parametrize("dev", [False, True])
def test_http_response_matches_the_dev_rule(tmp_path, monkeypatch, dev):
    pipeline, _, _ = build(tmp_path, dev=dev)

    class Limits:
        def check_rate(self, client_id):
            pass

        def run_bounded(self, work, timeout_seconds):
            return work()

    monkeypatch.setattr(router, "_config", pipeline.config)
    monkeypatch.setattr(router, "_pipeline", pipeline)
    monkeypatch.setattr(router, "_limits", Limits())
    body = TestClient(app).post("/ask", json={"question": QUESTION}).json()["interpreter"]
    assert ("field_decisions" in body) is dev
    assert bool(body["field_tiers"]) is dev


def test_jev_unavailable_falls_through_to_luna(tmp_path):
    pipeline, jev, luna = build(tmp_path, dev=True, jev=Fake("jev", outcome="unavailable"))
    response = pipeline.answer(AskQuery(question=QUESTION))
    assert response.outcome == "unsupported"
    assert (jev.calls, luna.calls) == (1, 1)
    (intent,) = response.interpreter.field_decisions
    assert [(r.tier, r.action) for r in intent.reads] == [("luna", "accepted")]


def test_decisions_are_logged_without_question_or_keys(tmp_path, caplog):
    caplog.set_level(logging.INFO, logger="server.ask.pipeline")
    pipeline, _, _ = build(tmp_path, dev=False)
    pipeline.answer(AskQuery(question=QUESTION))
    pipeline.answer(AskQuery(question=QUESTION))
    lines = [record.getMessage() for record in caplog.records if record.name == "server.ask.pipeline"]
    assert len(lines) == 2
    assert '"decided_by":"luna"' in lines[0] and '"outcome":"escalated"' in lines[0]
    assert "cache_hit=False" in lines[0] and "cache_hit=True" in lines[1]
    assert all("distinctive-question-marker" not in line and SECRET not in line for line in lines)


@pytest.mark.parametrize("tiers, fallback", [
    ({"intent": "jev", "location": "lookup"}, False),
    ({"intent": "jev", "location": "lookup", "player": "luna"}, True),
])
def test_lookup_decided_fields_are_not_a_fallback(tmp_path, tiers, fallback):
    # The candidate lookup settles fields such as a location the question never names.
    pipeline, _, _ = build(tmp_path, dev=True)
    metadata = SimpleNamespace(field_tiers=tiers, field_decisions=[], adapter="cascade", model="jev-1.13.0",
                               resolved_model=None)
    info = pipeline._info(called=True, adapter=pipeline.adapter, output=SimpleNamespace(metadata=metadata))
    assert info.fallback_used is fallback
