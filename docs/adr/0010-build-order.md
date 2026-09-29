# 10. Build order: cascade first, then tool families

Date: 2026-09-29
Status: accepted

## Decision

Work continues on `ask/reviewed-components`. #189 and its children (#199,
#200, #201, #205) are updated to match ADRs 0001–0009.

1. **Tool registry and router.** Recast the four existing intents as tools and
   add the router Choice. Wire the production cascade (Jev, then GPT Luna), with
   calibrated thresholds, the tier and system gates (ADR 0009), and per-field
   tier diagnostics. Remove Ask's answer-hiding UI (ADR 0006).
2. **Single-fetch families.** Player season stats and team records and
   standings: stats.nba first, Basketball-Reference as fallback, plus the shared
   rate limiter (ADR 0003).
3. **Leader families.** Season leaders (qualification, ties, and splits
   defined first) and all-time leaders and rank, plus career highs.
4. **Game-log index.** The offline build, nightly refresh, and Railway storage;
   then counting-game records and franchise records (ADR 0005).

**Throughout:** Laya evaluation runs alongside every stage (ADRs 0007 and 0008).
Each stage adds its families' cases to the development set and extends the
unseen set, and every stage's evaluation report includes Laya's shadow numbers.

## Consequences

- Each stage ships independently behind the gates. A family whose cases fail
  stays `unsupported` in the router rather than blocking the others.
- Stage 1 changes no answers users can see except the removal of spoiler
  hiding, which makes it a safe checkpoint for comparing the cascade against the
  Luna-only baseline.
