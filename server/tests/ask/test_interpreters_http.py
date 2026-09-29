import time

import httpx
import pytest

from server.ask.interpreters.http import ProviderError, post_json


class Trickle(httpx.SyncByteStream):
    def __iter__(self):
        for byte in b'{"ok": true}':
            time.sleep(0.03)
            yield bytes([byte])


def test_deadline_bounds_trickling_response_wall_time():
    client = httpx.Client(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, stream=Trickle())))
    started = time.monotonic()
    with pytest.raises(ProviderError, match="deadline_exceeded"):
        post_json(client, "https://example.test", "key", {}, timeout_s=2,
                  deadline=started + 0.1)
    assert time.monotonic() - started < 0.2


def test_deadline_bounds_blocked_response_headers():
    def blocked(request):
        time.sleep(0.35)
        return httpx.Response(200, json={"ok": True})

    client = httpx.Client(transport=httpx.MockTransport(blocked))
    started = time.monotonic()
    with pytest.raises(ProviderError, match="deadline_exceeded"):
        post_json(client, "https://example.test", "key", {}, timeout_s=2,
                  deadline=started + 0.1)
    assert time.monotonic() - started < 0.2
