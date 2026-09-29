# 9. Tier precision gates and a system gate

Date: 2026-09-29
Status: accepted

## Context

The earlier gate required 90% complete-request accuracy from each standalone
model. In a cascade (ADR 0002), a tier is supposed to escalate fields it isn't
sure about. Judging it on overall accuracy penalizes that escalation.

## Decision

All gates are measured on a frozen, unseen evaluation set.

**Tier gate** (Laya and Jev, each measured independently):
- Accepted-field precision of at least 98%: the fields the tier accepts at its
  calibrated threshold.
- Coverage of at least 30% of fields. A tier that accepts less than that adds cost
  and latency for too little benefit.

**System gate** (the full production cascade, including GPT Luna):
- At least 90% of requests fully correct.
- At least 90% of clarification and unsupported cases correct.
- Zero guesses: no request may render a wrong answer.
- p95 latency of 4 s or less.

A tier that fails its gate is disabled and skipped; the system gate is then
re-measured without it.

## Consequences

- Thresholds are calibrated on development data to reach 98% precision with the
  most coverage, then frozen before the unseen run.
- The unseen set must cover all eight tool families (ADR 0004) and have enough
  fields to make 98% meaningful. About 100 questions produce roughly 500 fields;
  at 30% coverage, a tier may make at most 3 accepted-field errors. Treat a
  borderline pass as provisional and rerun with a larger set.
- The evaluation report records, for each tier, precision, coverage, and
  escalation rate for every field and tool family.
- This replaces the per-model 90% gate in `docs/ask-evaluation.md` for cascade
  tiers.
