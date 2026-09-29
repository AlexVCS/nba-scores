import pytest

from server.ask.limits import AskLimits, AskRateLimited


def test_rejected_new_clients_do_not_grow_rate_buckets():
    now = [0.0]
    limits = AskLimits(per_client_per_minute=2, per_worker_per_minute=1,
                       clock=lambda: now[0])
    limits.check_rate("admitted")

    for index in range(10_000):
        with pytest.raises(AskRateLimited):
            limits.check_rate(f"rejected-{index}")

    assert len(limits._rates) == 1
    assert len(limits._all) == 1

    now[0] = 60.0
    limits.check_rate("new-window")
    assert len(limits._rates) == 2


def test_rate_bucket_cap_and_per_client_quota():
    limits = AskLimits(per_client_per_minute=1, per_worker_per_minute=1025,
                       clock=lambda: 0.0)
    limits.check_rate("first")
    with pytest.raises(AskRateLimited):
        limits.check_rate("first")
    assert len(limits._all) == 1

    for index in range(1024):
        limits.check_rate(f"other-{index}")
        assert len(limits._rates) <= 1024

    assert len(limits._rates) == 1024
    with pytest.raises(AskRateLimited):
        limits.check_rate("worker-full")
    assert len(limits._rates) == 1024
