import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from server.services.ask_limits import (
    Budget,
    BudgetUnavailable,
    RateLimiter,
    RateLimitError,
    TTLCache,
)


def test_budget_reserve_settle_and_restart(tmp_path):
    budget = Budget(tmp_path, daily_budget_usd=0.01)
    reservation = budget.reserve({"input": "hello", "max_output_tokens": 500}, "gpt-4.1-mini")
    assert reservation.id
    budget.settle(reservation, {"input_tokens": 3, "output_tokens": 4})
    restarted = Budget(tmp_path, daily_budget_usd=0.01)
    data = json.loads((tmp_path / "budget.json").read_text())
    assert data["reserved_usd"] == 0
    assert data["spent_usd"] >= 0
    assert restarted.reserve({"input": "hello", "max_output_tokens": 500}, "gpt-4.1-mini").id


def test_budget_concurrent_reservations_are_atomic(tmp_path):
    budget = Budget(tmp_path, daily_budget_usd=0.002)

    def reserve():
        try:
            return budget.reserve({"input": "x", "max_output_tokens": 500}, "gpt-4.1-mini")
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=8) as pool:
        reservations = list(pool.map(lambda _: reserve(), range(8)))
    assert sum(item is not None for item in reservations) == 1


def test_budget_corrupt_ledger_fails_closed(tmp_path):
    (tmp_path / "budget.json").write_text("not-json")
    with pytest.raises(BudgetUnavailable):
        Budget(tmp_path).reserve({"max_output_tokens": 500}, "gpt-4.1-mini")


def test_unknown_model_requires_explicit_prices(tmp_path, monkeypatch):
    monkeypatch.delenv("ASK_INPUT_USD_PER_MILLION", raising=False)
    monkeypatch.delenv("ASK_OUTPUT_USD_PER_MILLION", raising=False)
    with pytest.raises(BudgetUnavailable):
        Budget(tmp_path).reserve({}, "custom-model")


def test_budget_rejects_nonfinite_configuration(tmp_path, monkeypatch):
    monkeypatch.setenv("ASK_DAILY_BUDGET_USD", "nan")
    with pytest.raises(BudgetUnavailable):
        Budget(tmp_path)


def test_budget_rejects_missing_or_inconsistent_ledger(tmp_path):
    (tmp_path / "budget.json").write_text(json.dumps({"day": "today", "reservations": {}}))
    with pytest.raises(BudgetUnavailable):
        Budget(tmp_path).reserve({"max_output_tokens": 500}, "gpt-4.1-mini")
    (tmp_path / "budget.json").write_text(json.dumps({"day": "today", "spent_usd": 0, "reserved_usd": 2, "reservations": {}}))
    with pytest.raises(BudgetUnavailable):
        Budget(tmp_path).reserve({"max_output_tokens": 500}, "gpt-4.1-mini")


def test_budget_keeps_reservation_on_unsettled_failure(tmp_path):
    budget = Budget(tmp_path, daily_budget_usd=0.01)
    reservation = budget.reserve({"max_output_tokens": 500}, "gpt-4.1-mini")
    data = json.loads((tmp_path / "budget.json").read_text())
    assert reservation.id in data["reservations"]


def test_settle_records_actual_usage_above_reservation(tmp_path):
    budget = Budget(tmp_path, daily_budget_usd=0.01)
    reservation = budget.reserve({"max_output_tokens": 1}, "gpt-4.1-mini")
    budget.settle(reservation, {"input_tokens": 1, "output_tokens": 5000})
    data = json.loads((tmp_path / "budget.json").read_text())
    assert data["spent_usd"] > reservation.reserved_usd


def test_rate_limiter_and_bounded_ips():
    limiter = RateLimiter(per_ip=1, global_limit=3, max_ips=2)
    limiter.check("a")
    with pytest.raises(RateLimitError):
        limiter.check("a")
    limiter.check("b")
    limiter.check("c")
    assert len(limiter._ips) <= 2


def test_ttl_cache_expiry_version_and_capacity():
    cache = TTLCache(max_entries=2, version="one")
    cache.put("a", 1, ttl=0.01)
    assert cache.get("a") == 1
    import time
    time.sleep(0.02)
    assert cache.get("a") is None
    cache.put("b", 2)
    cache.put("c", 3)
    assert cache.get("b") == 2
    cache.put("d", 4)
    assert cache.get("c") is None
    cache.invalidate_version("two")
    assert cache.get("c") is None
    cache.put("e", 5)
    cache.clear()
    assert cache.get("e") is None
