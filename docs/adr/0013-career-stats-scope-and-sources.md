# 13. Career stats: three views, totals-only all-time lists, stats.nba only

Date: 2026-09-29
Status: accepted (development; production gates unchanged)

## Context

ADR 0005 names two single-fetch record shapes: all-time leaders and rank
(`AllTimeLeadersGrids`) and career and season highs (player profile). ADR 0004
adds career totals. A stats.nba probe
(`server/tests/ask/fixtures/season-data/nba-career-probe.json`) showed:

- `AllTimeLeadersGrids` honors TopX up to 1000 and uses competition ranks, but
  its per-game and percentage lists include very short careers (Victor
  Wembanyama 2nd in blocks per game after two seasons).
- `PlayerProfileV2.CareerHighs` returned only playoff games for LeBron James and
  omitted his 61-point regular-season high.

## Decision

1. One `career_stats` tool with three views chosen by Python: a named player's
   career totals or averages; the all-time top N when no player is named; a named
   player's all-time rank when the question uses rank wording.
2. All-time lists and ranks are **totals only**. Per-game and percentage
   all-time lists are unsupported until the NBA's all-time minimums can be
   applied and verified.
3. Career questions default to **totals**; averages must be explicit.
4. **Career highs are not built** from `PlayerProfileV2`; they move to the
   game-log index stage (ADR 0005).
5. **stats.nba only.** No Basketball-Reference fallback for this family (no
   verified NBA-to-BRef player mapping; career leader pages are not allowlisted).

## Consequences

- A stats.nba outage makes career answers unavailable.
- Rank beyond 250 is reported as "not in the top 250", never estimated.
- Career totals for statistics first recorded mid-career carry a coverage note;
  their per-game averages are unavailable.
