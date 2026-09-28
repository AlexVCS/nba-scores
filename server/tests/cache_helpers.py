import time


def wait_for_waiters(cache, key, count=1):
    """Block until ``count`` callers have joined the load in flight for ``key``."""
    deadline = time.monotonic() + 2
    while (flight := cache._flights.get(key)) is None or flight.waiters < count:
        assert time.monotonic() < deadline, "caller never joined the in-flight load"
        time.sleep(0.001)
