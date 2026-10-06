"""Regressions from the CodeRabbit review of PR #218."""
import datetime as dt
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from server.ask import router
from server.ask.config import AskConfig
from server.ask.eval.runner import embedded_candidates, run
from server.ask.interpreters.pricing import SpendGuard
from server.ask.limits import AskRateLimited
from server.ask.models.common import DateComponents, DateRange
from server.ask.normalize import resolve_components
from server.main import app
from server.tests.ask.test_interpreters_eval import BY_ID, GOOD, PRIMARY, FakeAdapter, configs

REPO = Path(__file__).resolve().parents[3]


def load_evaluate():
    spec = importlib.util.spec_from_file_location("review_evaluate", REPO / "scripts/ask/evaluate.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_evaluate_rejects_configs_without_keys_before_running(monkeypatch, capsys):
    module = load_evaluate()
    for name in module.KEY_NAMES:
        monkeypatch.delenv(name, raising=False)
    args = SimpleNamespace(env_file=None, timeout=1.0, luna_models=[], luna_effort="low",
                           configs=["jev", "luna", "jev+luna"], cases="missing.json")
    assert module.run_command(args) == 2
    assert "jev, luna, jev+luna" in capsys.readouterr().err
    assert module.unavailable_configs(["jev+luna", "luna"], {"jev": 1, "gpt-6-luna": 2}, ["gpt-6-luna"]) == []
    assert module.unavailable_configs(["jev+luna"], {"gpt-6-luna": 2}, ["gpt-6-luna"]) == ["jev+luna"]


def test_empty_reasoning_effort_is_omitted(monkeypatch):
    monkeypatch.setenv("ASK_REASONING_EFFORT", "")
    assert AskConfig.from_env().primary_reasoning_effort is None
    monkeypatch.setenv("ASK_REASONING_EFFORT", " medium ")
    assert AskConfig.from_env().primary_reasoning_effort == "medium"
    monkeypatch.setenv("ASK_PARSER_MODEL", "gpt-4.1-mini-2025-04-14")  # takes no reasoning parameter
    assert AskConfig.from_env().primary_reasoning_effort is None


def test_budget_block_on_fallback_leaves_configs_on_the_same_cases():
    primary = FakeAdapter("jev", "jev-1.13.0", PRIMARY, cost=0.4)
    luna = FakeAdapter("openai_responses", "gpt-6-luna", GOOD, cost=0.7)
    games, finals = BY_ID["smoke-games-last-week"], BY_ID["smoke-series-finals"]
    result = run([games, finals], embedded_candidates, configs(primary, luna), SpendGuard(1.0))
    assert result.stopped_reason == "spend cap reached"
    assert {name: [s.case_id for s in scores] for name, scores in result.scores.items()} == {
        "jev": [games.id], "jev->luna": [games.id]}
    assert result.not_run == {"jev": [finals.id], "jev->luna": [finals.id]}
    assert primary.calls == 2 and luna.calls == 0


def test_cross_year_range_with_only_end_year_starts_the_year_before():
    parts = DateComponents(kind="calendar_range", month=12, day=28, end_year=2025, end_month=1, end_day=3)
    assert resolve_components(parts, dt.date(2026, 3, 1)) == DateRange(start=dt.date(2024, 12, 28), end=dt.date(2025, 1, 3))
    same_year = DateComponents(kind="calendar_range", month=1, day=3, end_year=2025, end_month=1, end_day=9)
    assert resolve_components(same_year, dt.date(2026, 3, 1)) == DateRange(start=dt.date(2025, 1, 3), end=dt.date(2025, 1, 9))


def test_suggest_uses_its_own_rate_limited_pool(monkeypatch):
    assert router._suggest_limits is not router._limits

    class AskPoolFull:
        def check_rate(self, client_id):
            raise AssertionError("suggest must not use the /ask limits")

        run_bounded = check_rate

    class SuggestLimits:
        clients: list = []

        def check_rate(self, client_id):
            self.clients.append(client_id)
            raise AskRateLimited("slow down")

    class Suggester:
        def suggest(self, q, hidden):
            raise AssertionError("rate-limited suggest must not do work")

    limits = SuggestLimits()
    monkeypatch.setattr(router, "_config", AskConfig(enabled=True))
    monkeypatch.setattr(router, "_limits", AskPoolFull())
    monkeypatch.setattr(router, "_suggest_limits", limits)
    monkeypatch.setattr(router, "_suggester", Suggester())
    response = TestClient(app).get("/ask/suggest", params={"q": "Knicks"})
    assert response.json() == {"query": "Knicks", "games": [], "entities": [], "questions": []}
    assert limits.clients == ["testclient"]


def test_exposed_release_fixtures_warn_against_reuse():
    for path in (REPO / "server/tests/ask/fixtures/eval").glob("*exposed.json"):
        comment = json.loads(path.read_text())["comment"]
        assert comment.startswith("EXPOSED") and "never reuse" in comment, path.name
