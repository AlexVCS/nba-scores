# 7. Laya runs in development and evaluation only, for now

Date: 2026-09-29
Status: accepted

## Context

ADR 0002 puts Laya first in the cascade. The API runs on Railway, which bills
RAM at about $10 per GB per month. Keeping Laya's roughly 0.8–1 GB of weights
loaded would cost about $8–10 per month, whether in-process or as its own
service. Laya is also unproven here: its base checkpoints are near chance
zero-shot, and we have no NBA-specific accuracy data yet.

## Decision

- Laya runs locally (`laya-serve` or in-process) for development and for the
  evaluation harness only.
- The production cascade is **Jev, then GPT Luna** until Laya is promoted.
- The Laya tier stays in the code and the configuration, and is disabled in
  production by leaving `LAYA_BASE_URL` unset. When the tier is disabled, the
  cascade skips it, as ADR 0002 specifies for any tier that hasn't passed its gate.

## Promotion

Laya moves to production when it passes its evaluation gate on a frozen, unseen
set. It is then deployed as a separate Railway service reached over private
networking (`laya.railway.internal`), so its memory and crashes are isolated
from the API.

## Consequences

- Every evaluation run reports Laya's per-field accuracy and escalation rate
  alongside Jev and Luna. We can see what Laya would have saved before paying
  for it.
- The evaluation harness must be able to start Laya locally in a reproducible way,
  with a pinned `laya` version and checkpoint.
- Production diagnostics show only the Jev and Luna tiers until promotion.
