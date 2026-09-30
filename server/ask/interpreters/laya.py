"""Laya adapter (`InterpreterAdapter`, name "laya").

Laya is ConvAI Innovations' open-weights System One model. `laya-serve` implements the
same `POST /v1/systemone` request and response shape as TypeSafe Jev, so this adapter
reuses the Jev question builder and decoder with a local base URL. It runs in
development and evaluation only until promoted (ADR 0007); production leaves
`LAYA_BASE_URL` unset.
"""

from __future__ import annotations

import httpx

from server.ask.interpreters.jev import JevAdapter, JevThresholds

LAYA_MODEL = "laya"
LAYA_URL = "http://127.0.0.1:8080/v1/systemone"


class LayaAdapter(JevAdapter):
    """Implements `server.ask.protocols.InterpreterAdapter`."""

    name = "laya"
    provider = "laya"

    def __init__(
        self,
        *,
        url: str = LAYA_URL,
        model: str = LAYA_MODEL,
        api_key: str = "",
        thresholds: JevThresholds | None = None,
        timeout_s: float = 2.0,
        http_client: httpx.Client | None = None,
    ):
        if not model.startswith("laya"):
            raise ValueError("Laya model names must start with 'laya' (pin the checkpoint, e.g. laya-en-0.3)")
        super().__init__(api_key, model=model, thresholds=thresholds, timeout_s=timeout_s,
                         http_client=http_client, url=url)
