"""Shared process-wide fallback transport. Ten starts/minute, no waiting queue.

Every Basketball-Reference caller uses this limiter, including boxscore fallback.
Workers have separate limits; deploy one fallback worker or supply a shared limiter
before adding replicas. A throttled request is unavailable, never guessed.
"""
from __future__ import annotations

import threading
import time
from urllib.parse import urlsplit

import requests

INTERVAL_SECONDS = 6.0
TIMEOUT_SECONDS = 5
USER_AGENT = "NBA-Scorez/1.0 (basketball data fallback; https://nbascorez.com)"
_lock = threading.Lock()
_next_start = 0.0


class FallbackRateLimited(requests.RequestException):
    pass


def get(url: str, *, headers: dict | None = None, timeout: float = TIMEOUT_SECONDS):
    global _next_start
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.netloc != "www.basketball-reference.com":
        raise ValueError("Basketball-Reference transport requires the exact HTTPS host")
    with _lock:
        now = time.monotonic()
        if now < _next_start:
            raise FallbackRateLimited("Basketball-Reference fallback is cooling down")
        _next_start = now + INTERVAL_SECONDS
    response = requests.get(url, headers={**(headers or {}), "User-Agent": USER_AGENT},
                            timeout=min(timeout, TIMEOUT_SECONDS), allow_redirects=False)
    response.encoding = "utf-8"  # BRef declares UTF-8 in HTML; Requests otherwise assumes Latin-1.
    response.raise_for_status()
    if 300 <= response.status_code < 400:
        raise requests.RequestException("Basketball-Reference redirect refused")
    return response
