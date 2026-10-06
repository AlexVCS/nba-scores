# 14. Python reads the measure; unstated player measures show both; top N clamps to 25

Date: 2026-09-30
Status: accepted (development; production gates unchanged). Amends ADR 0012
decision 5 and the Stage 2 measure clarification (`docs/ask-stage2.md`).

## Context

Live testing on `ask/reviewed-components` (dev field decisions, ASK_DEV=1) found:

- "Who led the league in assists in 2019-20?" was answered as total assists. Jev
  accepted aggregation "total" at 0.96, although the question states no measure.
  ADR 0012 says counting-stat leaders never default. A confident model read
  still defaulted in practice.
- "Top 30 scorers 2023-24" was refused as unsupported, because N above 25 was out of
  scope.
- "Kevin Durant stats 2015-16" showed season totals only. For a player's season,
  per-game averages are the usual reading, and totals are one tap away.

## Decision

1. **The measure is read by Python from the question text.** Per-game wording
   ("per game", "a game", "ppg"/"apg"/..., "average(d)") and totals wording ("total",
   "totals", "in total", "how many") decide `aggregation` for player season stats,
   season leaders and career stats. The interpreter's `aggregation` read is replaced
   before normalization and before the cascade policy sees it (`server/ask/measure.py`).
   Diagnostics mark the field as decided by `question`. "How many" is a weak totals
   signal: per-game wording wins over it. Both kinds of wording make the measure
   ambiguous.
2. **With no stated measure:** season leaders ask the measure clarification (Season
   totals / Per game), as ADR 0012 intended. Career stats keep the ADR 0013 default
   (totals; since 2026-10-01 a full career line shows per game first, see the ADR 0013
   amendment). **Player season stats show per-game averages first, and the answer also
   carries season totals**, so the card offers a Per game | Totals toggle instead of a
   clarification.
3. **Both measures come from one source row.** Per-game values are the source's exact
   totals divided by games played, shown to one decimal (Python `format(value, ".1f")`).
   They are never rebuilt from rounded averages, and they never mix sources. Percentages are
   identical in both measures, so a percentage-only answer has no toggle. Shooting splits
   show made/attempted per game and in total.
4. **Explicit measure wording shows that measure first, and keeps the toggle.** The
   other measure is already in the same verified row. Showing it on request hides nothing
   and adds no fetch (ADR 0006).
5. **Top N above 25 is shown as the top 25 with a note** ("Showing the top 25, the most
   Ask lists."), for season leaders and all-time lists. It replaces "N above 25 is
   unsupported" in ADR 0012. Top 0 stays unsupported. The note is recomputed from the
   question text, so it survives clarification continuations.

## Consequences

- Development labels changed to match. `stage2-player_season_stats-04` and `-06` are
  now per game. `stage3-season_leaders-08` ("the most three-pointers", no measure) now
  expects the measure clarification. `stage3-season_leaders-24` (top 50) now expects the
  top 25. Every set was already exposed, so no unseen evidence is affected.
- The career line (`player_totals`) gets the same toggle; all-time lists and ranks stay
  totals only (ADR 0013).
- Interpreter prompts and router descriptions are unchanged. The model's aggregation read
  is still requested, but for these tools it is only diagnostics.

## Amendment, 2026-10-06: an unsure measure no longer escalates

The cascade still waited for a tier to decide `aggregation` on these three tools, so a
Jev read below its accept threshold caused a Luna call whose only possible use was a
value decision 1 then discards. `TieredAdapter._complete` now leaves `aggregation` out
of the fields it waits for when the accepted intent is player season stats, season
leaders or career stats. Box score questions are unchanged: their measure is still a
tier's read. `tier_gate.py` already treats the field as Python-decided (field tier
`question`), so no gate rule changes.

Measured by replaying the 2026-10-06 calibration journal
(`docs/verification/ask-calibration-2026-10-06/`, 229 exposed questions): the same 212
correct, 6 flagged guesses (5 of them stale labels) and every clarify/unsupported
outcome; Luna calls fall from 125 to 121 and replayed p95 from 4.61 s to 4.49 s. Luna
no longer gets its incidental second look at those four questions; on this journal it
changed none of them.
