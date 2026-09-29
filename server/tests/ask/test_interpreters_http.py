import gzip
import json
import time
import zlib

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


@pytest.mark.parametrize("encoding,compress", [("gzip", gzip.compress), ("deflate", zlib.compress)])
def test_compressed_json_is_decoded_once(encoding, compress):
    raw = json.dumps({"ok": True}).encode()
    wire = compress(raw)
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(
        200, headers={"content-encoding": encoding, "content-length": str(len(wire))}, content=wire,
    )))
    assert post_json(client, "https://example.test", "key", {}, timeout_s=2,
                     deadline=time.monotonic() + 1) == {"ok": True}


def test_compressed_retry_preserves_status_and_retry_after():
    calls = 0
    def handler(request):
        nonlocal calls
        calls += 1
        if calls == 1:
            wire = gzip.compress(b'{"error":{"type":"busy"}}')
            return httpx.Response(503, headers={"content-encoding": "gzip", "retry-after": "0.01"},
                                  content=wire)
        return httpx.Response(200, json={"ok": True})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    assert post_json(client, "https://example.test", "key", {}, timeout_s=2,
                     deadline=time.monotonic() + 1) == {"ok": True}
    assert calls == 2
