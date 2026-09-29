"""Minimal JSON-over-HTTP helper with bounded retries and per-request timeouts.

Adapters call provider HTTP APIs directly with httpx (already a backend dependency),
so tests can inject `httpx.MockTransport` and no provider SDK is required.
"""

from __future__ import annotations

import time
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from typing import Any, Callable

import httpx

RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 529})
_MAX_IN_FLIGHT = 4
_HTTP_WORKERS = ThreadPoolExecutor(max_workers=_MAX_IN_FLIGHT, thread_name_prefix="ask-provider-http")
_HTTP_SLOTS = threading.BoundedSemaphore(_MAX_IN_FLIGHT)


class ProviderError(Exception):
    """A provider failure with a short machine-readable code.

    `code` is safe to surface as `InterpreterOutput.error_code`; `detail` may contain
    provider text and belongs only in local diagnostics. Neither ever contains keys.
    """

    def __init__(self, code: str, detail: str = ""):
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code[:60]
        self.detail = detail


def _status_code(status: int) -> str:
    if status == 401:
        return "auth_failed"
    if status == 403:
        return "permission_denied"
    if status == 404:
        return "model_not_found"
    if status == 429:
        return "rate_limited"
    if status in (529, 503):
        return "provider_overloaded"
    if status >= 500:
        return "provider_error"
    return f"http_{status}"


def post_json(
    client: httpx.Client,
    url: str,
    api_key: str,
    payload: dict[str, Any],
    *,
    timeout_s: float,
    max_retries: int = 1,
    backoff_s: float = 0.5,
    deadline: float | None = None,
    on_attempt: Callable[[], None] | None = None,
) -> dict[str, Any]:
    """POST JSON and return the decoded object. `deadline` is a time.monotonic() value.

    Never includes request headers in raised errors, so keys cannot leak into logs.
    """
    if deadline is None:
        return _post_json(client, url, api_key, payload, timeout_s=timeout_s,
                          max_retries=max_retries, backoff_s=backoff_s, on_attempt=on_attempt)
    remaining = deadline - time.monotonic()
    if remaining <= 0 or not _HTTP_SLOTS.acquire(timeout=remaining):
        raise ProviderError("deadline_exceeded")
    future = _HTTP_WORKERS.submit(
        _post_json, client, url, api_key, payload, timeout_s=timeout_s,
        max_retries=max_retries, backoff_s=backoff_s, deadline=deadline, on_attempt=on_attempt,
    )
    future.add_done_callback(lambda _: _HTTP_SLOTS.release())
    try:
        return future.result(timeout=max(0, deadline - time.monotonic()))
    except FutureTimeout as exc:
        future.cancel()
        raise ProviderError("deadline_exceeded") from exc


def _post_json(
    client: httpx.Client,
    url: str,
    api_key: str,
    payload: dict[str, Any],
    *,
    timeout_s: float,
    max_retries: int,
    backoff_s: float,
    deadline: float | None = None,
    on_attempt: Callable[[], None] | None = None,
) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    attempt = 0
    while True:
        remaining = timeout_s
        if deadline is not None:
            remaining = min(remaining, deadline - time.monotonic())
            if remaining <= 0.05:
                raise ProviderError("deadline_exceeded")
        try:
            if on_attempt is not None:
                on_attempt()
            with client.stream("POST", url, json=payload, headers=headers, timeout=remaining) as response:
                body = bytearray()
                for chunk in response.iter_bytes():
                    if deadline is not None and time.monotonic() >= deadline:
                        raise ProviderError("deadline_exceeded")
                    body.extend(chunk)
                if deadline is not None and time.monotonic() >= deadline:
                    raise ProviderError("deadline_exceeded")
                response = httpx.Response(response.status_code, headers=response.headers, content=bytes(body))
        except httpx.TimeoutException as exc:
            raise ProviderError("timeout", f"after {remaining:.1f}s") from exc
        except httpx.HTTPError as exc:
            raise ProviderError("connection_error", type(exc).__name__) from exc

        if response.status_code in RETRYABLE_STATUS and attempt < max_retries:
            attempt += 1
            wait = _retry_after(response) or backoff_s * attempt
            if deadline is None or time.monotonic() + wait < deadline:
                time.sleep(wait)
                continue
        if response.status_code >= 400:
            raise ProviderError(_status_code(response.status_code), _error_summary(response))
        try:
            data = response.json()
        except ValueError as exc:
            raise ProviderError("invalid_response", "not JSON") from exc
        if not isinstance(data, dict):
            raise ProviderError("invalid_response", "not a JSON object")
        if deadline is not None and time.monotonic() >= deadline:
            raise ProviderError("deadline_exceeded")
        return data


def _retry_after(response: httpx.Response) -> float | None:
    value = response.headers.get("retry-after")
    try:
        return min(float(value), 5.0) if value else None
    except ValueError:
        return None


def _error_summary(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return response.text[:200]
    error = body.get("error") if isinstance(body, dict) else None
    if isinstance(error, dict):
        return f"{error.get('type') or error.get('code')}: {str(error.get('message'))[:200]}"
    return str(body)[:200]
