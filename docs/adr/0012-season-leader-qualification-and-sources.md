# 12. Season leaders: source qualification, shared ranks, totals-only fallback

Date: 2026-09-29
Status: accepted (development; production gates unchanged)

## Context

ADR 0004 requires season leaders to define qualification, ties, regular season
vs playoffs, and per-game vs totals before the tool is enabled. A stats.nba
probe (saved in `server/tests/ask/fixtures/season-data/nba-leaders-2023-24.json`)
showed that `LeagueLeaders` already applies the NBA's minimums, and that those
minimums vary by era: 2023-24 per-game boards rank only players with 58+ games
(games only), 2012-13 used games *or* a total threshold, and the 1985-86 3P%
rule differs again. Basketball-Reference's leaders page shows only 20 rows at
display precision and does not state its minimums.

## Decision

1. **Qualification belongs to the source.** Per-game boards use stats.nba
   `PerMode=PerGame`; percentage boards use `PerMode=Totals` (the endpoint
   rejects per-game percentages), where stats.nba applies made-shot minimums.
   Totals boards rank everyone. Ask does not re-derive minimums.
2. **Basketball-Reference is a totals-only fallback** for leaders, computed from
   the season totals page Ask already uses for Stage 2. Per-game and percentage
   leaderboards have no fallback: when stats.nba fails, Ask says unavailable
   rather than show a list under a different or guessed rule.
3. **Ties use competition ranking on unrounded values, and a tie group is never
   split.** Top N lists every player whose rank is N or better. A 50-row cap
   drops a whole cutoff tie group and says so.
4. **Counting-stat leaders always need a measure.** No default: an absent or
   ambiguous measure is a server-validated clarification (Season totals / Per
   game). Percentages have no measure.
5. **Top N is read by Python from "top N" text** (1-25, default 10), not by a
   model, as ADR 0005 requires for numbers. N above 25 is unsupported.

## Consequences

- Per-game and percentage leaders depend on stats.nba reachability from the
  production host; a stats.nba outage makes them unavailable.
- A verified per-era qualification table could later extend the fallback to
  per-game boards; it must be checked against stats.nba season by season.
- Pre-1969-70 per-game boards can differ from the historical title holder,
  since titles were then awarded on totals. Answers carry a coverage note.
- Player-rank questions ("where did Curry rank") are unsupported here and move
  to the career/all-time family.
