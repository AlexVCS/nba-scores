import datetime as dt
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from server.ask.budget import BudgetExhausted, BudgetUnavailable, DailyBudget
from server.ask.cache import AskCache, CacheValue, invalidate_ask_caches
from server.ask.config import AskConfig
from server.ask.diagnostics import AskDiagnostics, DiagnosticEvent
from server.ask.limits import AskBusy, AskLimits, AskRateLimited, AskTimeout


def test_config_defaults_disabled_and_uses_only_key_dotenv_fallback(monkeypatch, tmp_path):
    from server.ask import config as module
    monkeypatch.setattr(module, "_SERVER_DIR", tmp_path)
    (tmp_path / ".env").write_text("OPENAI_API_KEY=local-secret\nASK_ENABLED=1\nASK_DAILY_BUDGET_USD=40\n")
    for name in ("OPENAI_API_KEY", "ASK_ENABLED", "ASK_DAILY_BUDGET_USD", "ASK_PARSER_MODEL"):
        monkeypatch.delenv(name, raising=False)
    config = AskConfig.from_env()
    assert config.enabled is False
    assert config.primary_model == "gpt-6-luna"
    assert config.primary_reasoning_effort == "low"
    assert config.daily_budget_usd == 1
    assert config.api_key == "local-secret"
    assert "local-secret" not in repr(config)


def test_budget_unknown_cost_and_prior_day_reservation(tmp_path):
    now = [dt.datetime(2026, 9, 29, 23, 59, tzinfo=dt.timezone.utc)]
    budget = DailyBudget(tmp_path, 1, clock=lambda: now[0])
    first = budget.reserve("gpt-6-luna", 0.7)
    assert budget.remaining_usd() == pytest.approx(0.3)
    with pytest.raises(BudgetExhausted):
        budget.reserve("gpt-6-luna", 0.4)
    now[0] += dt.timedelta(minutes=2)
    assert budget.remaining_usd() == pytest.approx(1)
    second = budget.reserve("gpt-6-luna", 0.8)
    budget.settle(first, None)
    budget.settle(second, 0.5)
    assert budget.remaining_usd() == pytest.approx(0.5)
    data = json.loads((tmp_path / "budget.json").read_text())
    assert data["days"]["2026-09-29"]["spent_usd"] == pytest.approx(0.7)
    assert data["days"]["2026-09-30"]["spent_usd"] == pytest.approx(0.5)
    assert all(not entry["reservations"] for entry in data["days"].values())


def test_budget_concurrent_reservation_and_corrupt_ledger_fail_closed(tmp_path):
    budget = DailyBudget(tmp_path, 1)
    def reserve():
        try:
            return budget.reserve("gpt-6-luna", 0.6)
        except BudgetExhausted:
            return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: reserve(), range(2)))
    assert sum(result is not None for result in results) == 1
    (tmp_path / "budget.json").write_text("not json")
    with pytest.raises(BudgetUnavailable):
        budget.remaining_usd()
    with pytest.raises(BudgetUnavailable):
        budget.reserve("gpt-6-luna", 0.1)


def test_cache_singleflight_waiter_hit_ttl_and_failure_not_cached():
    cache = AskCache(max_entries=2)
    entered = threading.Event()
    release = threading.Event()
    calls = 0
    def loader():
        nonlocal calls
        calls += 1
        entered.set()
        release.wait(1)
        return CacheValue({"n": calls}, 0.05)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(cache.get_or_load, "parse", "same", loader)
        assert entered.wait(1)
        second = pool.submit(cache.get_or_load, "parse", "same", loader)
        time.sleep(0.02)
        release.set()
        outputs = [first.result(), second.result()]
    assert calls == 1
    assert sorted(output.hit for output in outputs) == [False, True]
    outputs[0].value["n"] = 999
    assert cache.get_or_load("parse", "same", loader).value == {"n": 1}
    time.sleep(0.06)
    assert cache.get_or_load("parse", "same", loader).hit is False
    def fails():
        raise RuntimeError("load failed")
    with pytest.raises(RuntimeError):
        cache.get_or_load("answer", "failed", fails)
    assert cache.get_or_load("answer", "failed", lambda: CacheValue("recovered", 1)).value == "recovered"
    invalidate_ask_caches()
    assert len(cache) == 0


def test_limits_rate_and_worker_slot_survives_caller_timeout():
    now = [0.0]
    limits = AskLimits(per_client_per_minute=2, per_worker_per_minute=3,
                       max_in_flight=1, clock=lambda: now[0])
    limits.check_rate("client-a")
    limits.check_rate("client-a")
    with pytest.raises(AskRateLimited):
        limits.check_rate("client-a")
    limits.check_rate("client-b")
    with pytest.raises(AskRateLimited):
        limits.check_rate("client-c")
    now[0] = 61
    limits.check_rate("client-a")

    entered = threading.Event()
    release = threading.Event()
    def work():
        entered.set()
        release.wait(1)
        return 7
    with pytest.raises(AskTimeout):
        limits.run_bounded(work, timeout_seconds=0.02)
    assert entered.is_set()
    with pytest.raises(AskBusy):
        limits.run_bounded(lambda: 1)
    release.set()
    for _ in range(100):
        try:
            assert limits.run_bounded(lambda: 8) == 8
            break
        except AskBusy:
            time.sleep(0.01)
    else:
        pytest.fail("worker slot was not released")


def test_diagnostics_hash_only_bounded_and_expiring():
    now = [1000.0]
    notes = AskDiagnostics(max_entries=2, ttl_seconds=7, clock=lambda: now[0])
    event = DiagnosticEvent("What is my bank password?", operation="unknown",
                            stat="points", missing_fields=("date", "untrusted"),
                            reason="not_basketball")
    assert notes.record(event)
    row = notes.unsupported_request_log()[0]
    assert len(row["question_hash"]) == 64
    assert "bank" not in repr(row)
    assert row["missing_fields"] == ("date",)
    notes.record(DiagnosticEvent("second"))
    notes.record(DiagnosticEvent("third"))
    assert len(notes.unsupported_request_log()) == 2
    now[0] = 1008
    assert notes.unsupported_request_log() == []
