"""Shared process-wide fallback transport. Ten starts/minute, no waiting queue.

Every Basketball-Reference caller uses this limiter, including boxscore fallback.
Workers have separate limits; deploy one fallback worker or supply a shared limiter
before adding replicas. A throttled request is unavailable, never guessed.

The limiter never waits, so it cannot outlast a caller's deadline. With a
``deadline`` (``server.utils.deadline.Deadline``), a start is refused before it
consumes the shared slot unless ``MIN_START_SECONDS`` remain, and the request
timeout is capped to the time left.
"""
from __future__ import annotations

import threading
import time
from urllib.parse import urlsplit

import requests

INTERVAL_SECONDS = 6.0
TIMEOUT_SECONDS = 5
MIN_START_SECONDS = 2.0
USER_AGENT = "NBA-Scorez/1.0 (basketball data fallback; https://nbascorez.com)"
_lock = threading.Lock()
_next_start = 0.0


class FallbackRateLimited(requests.RequestException):
    pass


class FallbackDeadlineExceeded(requests.RequestException):
    pass


def get(url: str, *, headers: dict | None = None, timeout: float = TIMEOUT_SECONDS, deadline=None):
    global _next_start
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.netloc != "www.basketball-reference.com":
        raise ValueError("Basketball-Reference transport requires the exact HTTPS host")
    with _lock:
        if deadline is not None and not deadline.fits(MIN_START_SECONDS):
            raise FallbackDeadlineExceeded("Basketball-Reference fallback does not fit the deadline")
        now = time.monotonic()
        if now < _next_start:
            raise FallbackRateLimited("Basketball-Reference fallback is cooling down")
        _next_start = now + INTERVAL_SECONDS
    timeout = min(timeout, TIMEOUT_SECONDS)
    if deadline is not None:
        timeout = max(0.001, deadline.cap(timeout))
    response = requests.get(url, headers={**(headers or {}), "User-Agent": USER_AGENT},
                            timeout=timeout, allow_redirects=False)
    response.encoding = "utf-8"  # BRef declares UTF-8 in HTML; Requests otherwise assumes Latin-1.
    response.raise_for_status()
    if 300 <= response.status_code < 400:
        raise requests.RequestException("Basketball-Reference redirect refused")
    return response
