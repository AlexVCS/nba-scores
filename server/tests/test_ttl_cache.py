import threading
import time
from unittest.mock import Mock

import pytest

from server.utils.ttl_cache import LoadInProgressError, TTLCache


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def test_hits_reuse_value_until_expiry_without_renewing():
    clock = Clock()
    cache = TTLCache(4, clock=clock)
    loader = Mock(side_effect=["first", "second"])

    assert cache.get_or_load("k", loader, lambda _: 10) == "first"
    clock.now += 9
    assert cache.get_or_load("k", loader, lambda _: 10) == "first"
    assert cache.get("k") == "first"
    clock.now += 1
    assert cache.get("k") is None
    assert cache.get_or_load("k", loader, lambda _: 10) == "second"
    assert loader.call_count == 2


def test_lifetime_is_chosen_from_the_loaded_value():
    clock = Clock()
    cache = TTLCache(4, clock=clock)

    cache.get_or_load("live", lambda: "live", lambda value: 15 if value == "live" else 900)
    cache.get_or_load("final", lambda: "final", lambda value: 15 if value == "live" else 900)

    assert cache.expires_in("live") == 15
    assert cache.expires_in("final") == 900


def test_non_positive_lifetime_is_not_stored():
    cache = TTLCache(4)
    cache.get_or_load("k", lambda: "value", lambda _: 0)
    assert len(cache) == 0


def test_failures_are_not_cached_and_later_calls_retry():
    cache = TTLCache(4)
    loader = Mock(side_effect=[RuntimeError("down"), "ok"])

    with pytest.raises(RuntimeError):
        cache.get_or_load("k", loader, lambda _: 60)
    assert cache.get("k") is None
    assert cache._flights == {}
    assert cache.get_or_load("k", loader, lambda _: 60) == "ok"


def test_ttl_failure_releases_the_flight():
    cache = TTLCache(4)
    with pytest.raises(KeyError):
        cache.get_or_load("k", lambda: {}, lambda value: value["missing"])
    assert cache._flights == {}
    assert len(cache) == 0


def test_capacity_evicts_oldest_entry_and_expired_entries_first():
    clock = Clock()
    cache = TTLCache(2, clock=clock)
    cache.set("a", 1, 100)
    cache.set("b", 2, 5)
    clock.now += 5
    cache.set("c", 3, 100)
    assert cache.get("a") == 1
    assert cache.get("c") == 3

    cache.set("d", 4, 100)
    assert len(cache) == 2
    assert cache.get("a") is None
    assert cache.get("d") == 4


def _run_concurrently(count, target):
    barrier = threading.Barrier(count)
    results, errors = [], []

    def worker():
        try:
            barrier.wait()
            results.append(target())
        except BaseException as error:  # pragma: no cover - surfaced by assertions
            errors.append(error)

    threads = [threading.Thread(target=worker) for _ in range(count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(5)
    return results, errors


def test_concurrent_callers_share_one_load():
    cache = TTLCache(4)
    calls = []

    def loader():
        calls.append(1)
        time.sleep(0.1)
        return "value"

    results, errors = _run_concurrently(6, lambda: cache.get_or_load("k", loader, lambda _: 60))
    assert errors == []
    assert results == ["value"] * 6
    assert len(calls) == 1


def test_concurrent_failure_is_shared_then_released():
    cache = TTLCache(4)
    calls = []

    def loader():
        calls.append(1)
        time.sleep(0.1)
        raise RuntimeError("down")

    results, errors = _run_concurrently(4, lambda: cache.get_or_load("k", loader, lambda _: 60))
    assert results == []
    assert len(errors) == 4
    assert len(calls) == 1
    assert cache._flights == {}


def test_different_keys_do_not_serialize():
    cache = TTLCache(4)

    def load(key):
        time.sleep(0.3)
        return key

    threads = [
        threading.Thread(target=cache.get_or_load, args=(key, lambda key=key: load(key), lambda _: 60))
        for key in ("a", "b")
    ]
    started = time.monotonic()
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(5)
    assert time.monotonic() - started < 0.55
    assert cache.get("a") == "a" and cache.get("b") == "b"


def test_non_waiting_caller_fails_fast_while_load_is_in_flight():
    cache = TTLCache(4)
    entered, release = threading.Event(), threading.Event()

    def slow():
        entered.set()
        assert release.wait(2)
        return "value"

    leader = threading.Thread(target=cache.get_or_load, args=("k", slow, lambda _: 60))
    leader.start()
    try:
        assert entered.wait(2)
        with pytest.raises(LoadInProgressError):
            cache.get_or_load("k", Mock(), lambda _: 60, wait=False)
    finally:
        release.set()
        leader.join(2)


def test_rejected_cached_value_is_reloaded():
    cache = TTLCache(4)
    cache.set("k", "partial", 60)
    assert cache.get_or_load("k", lambda: "complete", lambda _: 60, accept=lambda v: v == "complete") == "complete"
    assert cache.get("k") == "complete"


def test_follower_retries_after_failure_of_weaker_load():
    cache = TTLCache(4)
    entered, release = threading.Event(), threading.Event()

    def weak():
        entered.set()
        assert release.wait(2)
        raise RuntimeError("short timeout")

    leader_errors = []

    def run_leader():
        try:
            cache.get_or_load("k", weak, lambda _: 60, tag="weak")
        except RuntimeError as error:
            leader_errors.append(error)

    leader = threading.Thread(target=run_leader)
    leader.start()
    assert entered.wait(2)
    result = []
    follower = threading.Thread(target=lambda: result.append(
        cache.get_or_load("k", lambda: "strong", lambda _: 60, tag="strong", retry_after=lambda tag: tag == "weak")
    ))
    follower.start()
    time.sleep(0.05)
    release.set()
    leader.join(2)
    follower.join(2)

    assert len(leader_errors) == 1
    assert result == ["strong"]


def test_copy_hook_isolates_every_reader_from_the_stored_value():
    cache = TTLCache(4, clock=Clock(), copy=lambda value: {**value, "items": list(value["items"])})
    loaded = cache.get_or_load("k", lambda: {"items": [1]}, lambda _: 60)
    loaded["items"].append(2)
    hit = cache.get_or_load("k", Mock(), lambda _: 60)
    hit["extra"] = True
    cache.get("k")["items"].append(3)
    assert cache.get("k") == {"items": [1]}


def test_copy_hook_isolates_joined_callers():
    release = threading.Event()

    def loader():
        assert release.wait(2)
        return {"items": [1]}

    cache = TTLCache(4, copy=lambda value: {"items": list(value["items"])})
    results = []
    threads = [threading.Thread(target=lambda: results.append(cache.get_or_load("k", loader, lambda _: 60))) for _ in range(3)]
    for thread in threads:
        thread.start()
    time.sleep(0.05)
    release.set()
    for thread in threads:
        thread.join(2)
    assert len({id(result) for result in results}) == 3
    results[0]["items"].append(2)
    assert cache.get("k") == {"items": [1]}


def test_pop_removes_only_the_given_key():
    cache = TTLCache(4, clock=Clock())
    cache.set("a", 1, 60)
    cache.set("b", 2, 60)
    cache.pop("a")
    cache.pop("missing")
    assert (cache.get("a"), cache.get("b")) == (None, 2)
