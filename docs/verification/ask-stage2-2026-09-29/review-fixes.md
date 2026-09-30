# Opus 5.5 review disposition

The initial independent review used a new Claude session
`45de1446-2b53-4c15-9c16-0da1a21f5ec8`, model `claude-opus-5-5`, against
`665030a6`. Its full findings are preserved in `opus-review.md`.

- H1/H2 and M1/M2: guard explicit rounds/games/locations, split wording,
  conditional player-dependent records, multiple distinct player mentions, and
  playoff phase consistency. Single ambiguous name candidates remain clarifiable.
- H3: Jev offers NONE for optional selectors. Absent versus explicit default
  has identical semantics in veto comparison. Named team plus conference scope
  is rejected by normalization and request validation.
- M3: percentages require valid made/attempted and positive attempts.
- M4: field scoring recognizes absent defaults; all development accept labels
  are checked through the same question guard as HTTP.
- M5/M6: verified current UTF-8 BRef season-page markup. Regular and postseason
  tables share the season URL and have distinct table IDs. Saved live excerpt
  tests both phases. Source links are validated inside the cache loader.
- M7: league standings sort across conferences by winning percentage. Conference
  rank remains a source label; equal league percentages sort alphabetically.
- M8: known unrecorded era/stat gaps skip all fetching. Other well-formed NBA
  misses still try BRef because primary absence does not establish historical
  nonexistence; ADR 0010 explicitly requires fallback on noncoverage. A busy
  fallback yields unavailable, not a guessed no-record. Historical boxscore
  cooldown presentation/retry is tracked in **nba-scores-cnm** before deployment.
- L1: PHX/BKN/CHA stints map to PHO/BRK/CHO, with parser regression cases.
- L2: guard masking matches current text instead of original candidate offsets;
  a rewritten-name/trailing-home regression is included.
- L3: aggregation and season type clarify with server-validated token choices.
- L4: stat readout stays on clarifications; extra closed selectors only show for
  relevant season tools, with the default league chip omitted.
- L5: Eastern fetch-date formatting, player source fixture URL, and keyboard
  focusable standings overflow region.
- L6: conservative completed-season cutoff is November 1, tested for late 2020.
- L7: joined season-cache callers have a five-second wait bound mapped to
  unavailable. The overall HTTP deadline/worker accounting already bounds the
  response, but slow-source retry/fallback budgeting still needs integration
  tuning. Tracked in **nba-scores-8ic** before deployment.

No release gate is claimed. The development fixture is exposed. The raw first
run's 16/21 strict score, four unnecessary default-veto clarifications, and one
unsupported-reason mismatch remain saved rather than being relabeled.
