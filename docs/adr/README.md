# Architecture decision records

Ask design decisions from the 2026-09-29 interview. Vocabulary is in
[`../ask-glossary.md`](../ask-glossary.md).

| ADR | Decision |
| --- | --- |
| [0001](0001-python-orchestrates-system-one-models-choose.md) | Python orchestrates; Jev and Laya only choose among options it supplies |
| [0002](0002-laya-jev-luna-cascade.md) | Interpreter cascade: Laya, then Jev, then GPT Luna |
| [0003](0003-stats-nba-primary-bref-fallback.md) | stats.nba.com primary, Basketball-Reference fallback, no Wikipedia |
| [0004](0004-first-pass-tool-families.md) | Adds player season stats, season leaders, records, and team records |
| [0005](0005-records-scope-and-game-log-index.md) | Four record shapes; a precomputed game-log index for scan-based records |
| [0006](0006-asking-is-consent.md) | Ask shows answers immediately; the spoiler preference governs everything else |
| [0007](0007-laya-dev-and-eval-only.md) | Laya runs in development and evaluation only until promoted |
| [0008](0008-laya-checkpoint-then-distillation.md) | Evaluate Laya's published checkpoint, then distill if needed |
| [0009](0009-tier-and-system-gates.md) | Per-tier 98% precision and 30% coverage; system gate at 90% with zero guesses |
| [0010](0010-build-order.md) | Cascade first, then single-fetch, leader, and index-based families |
| [0012](0012-season-leader-qualification-and-sources.md) | Season leaders: source qualification, shared ranks, totals-only BRef fallback |
| [0013](0013-career-stats-scope-and-sources.md) | Career stats: three views, totals-only all-time lists, stats.nba only |

## Open questions

- How Luna, the last tier, gets a veto so the system reaches zero guesses (ADR 0002).
- Season-leader qualification rules, ties, and splits (ADR 0004). Resolved by ADR 0012.
- Record template set: which stats, thresholds, and scopes (ADR 0005).
- Game-log index storage on Railway: a volume or a shipped artifact (ADR 0005).
- Provider terms for training Laya on Luna or Jev outputs (ADR 0008).
