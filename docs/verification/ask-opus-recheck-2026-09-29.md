# Opus 5.5 fix recheck

Model `claude-opus-5-5`, same read-only session as the initial review. Rechecked changes through `80b5570`. The findings below were then reviewed and addressed where applicable; this report itself is preserved unchanged.

I found two spoiler leaks and one mismatch between what a date option says and what it does. Two fixes are incomplete. One production entry point is still ungated, and one point is low. Everything else I checked holds.

## Remaining defects

**1. Medium, new: the recent-player check leaks results before reveal.**
- **Where:** `resolvers/games.py:301-306`.
- **Trigger:** "How many points did Brunson score last night?" asked the day after a playoff date on which his series had an if-necessary game scheduled.
  - If he played and the NBA stats game-log lookup (LeagueGameFinder) has caught up, the user gets a gated answer.
  - If his team didn't play because the series was already over, the finder has no row, other games exist, and `UnavailableError` fires.
  - `resolve()` gates only `NotFoundError`, so the second case shows "NBA data isn't responding" while the first shows "Results hidden". That tells the user whether the game happened.
- **Everyday effect:** "How did LeBron do tonight?" on a Lakers off-night also returns a retryable "NBA data isn't responding" that never goes away.
- **Fix:** When the finder is empty, look for the player in that day's started games through the cached boxscores (a dated record):
  - found: use that game;
  - every game final and he's absent: `player_did_not_play`;
  - otherwise: a `NotFoundError("no_record", …)`, so the gate still applies.

**2. Medium-low: the spoiler pre-clarification misses player questions that name a round.**
- **Where:** `resolvers/__init__.py:277` checks only leaders and team scope.
- **Trigger:** "Brunson points in Game 1 of the 2026 conference finals", asked during the current postseason.
  - `find_playoff_game` sees 0 series (gated `not_found`), 1 series (gated), or 2 series.
  - With 2 series it raises an ungated `AmbiguousError` ("Which teams?"). That reveals both conference-semifinal series are over.
  - Past seasons always give the same result, so they're safe.
- **Fix:** For every scope, clarify up front when the request has a round, no teams and no date, unless the series is unique.

**3. Low: the same pre-check over-clarifies unique series.**
- Only the Finals count as unique. "Who led in points in Game 7 of the 2024 Western Conference Finals?" has a round plus a conference, which names exactly one series, yet it still gets "Which teams?". A Finals question with a date but no game number is also clarified.
- **Fix:** Treat `conference_finals` with a conference as unique, and treat any request with a date plus the Finals round as unique.

**4. Medium: a year option for a cross-year range doesn't match its own question text.**
- **Where:** `present.py` (the `question.replace(expression, f"{expression}, {year}")` rewrite) together with the new rollover in `normalize.py:104-106`.
- **Trigger:** "games Dec 28 to Jan 3" and the user picks 2025.
  - The token resolves Dec 28 2025 to Jan 3 2026.
  - The rewritten question "games Dec 28 to Jan 3, 2025" is re-read by `_MONTH_RANGE_WITH_YEARS` (and `_BETWEEN_MONTH_DAYS`) as Dec 28 2024 to Jan 3 2025.
  - So recent searches, retries after the token expires, and what the user reads all mean a different week than the answer.
- **Fix:** For ranges that cross a year, build the rewrite from the resolved range, e.g. "Dec 28, 2025 to Jan 3, 2026". Same-month ranges and single dates round-trip correctly already.

**5. Medium, conditional on the default design being served: the original header still shows Ask unconditionally.**
- **Where:** `src/components/Header.tsx:20` renders `<AskEntry variant="original" />` with no flag. The original design is the first entry in `designRegistry.ts`.
- **Impact:** With the backend off by default, that header still shows an Ask entry that always answers "NBA data isn't responding". This isn't a parity request; it's the same one-line gate.
- **Fix:** Wrap it in the same `DEV || VITE_ASK_ENABLED === "1"` check, or remove it.

**6. Low: an unresolved `aggregation` now fails cleanly, but the failure sticks for an hour.**
- `normalize.py:199-200` marks it invalid, so the policy fails and the user sees retryable `interpreter_unavailable`.
- The interpreted output is still in the parse cache for an hour (`pipeline.py:140`), so "Try again" returns the same failure without calling the model.
- **Fix:** Don't cache parse results whose normalization is invalid, or mark this notice as not retryable.

## Checked and correct
- **Date option loops:** `_candidate_options` now offers choices only for `ambiguous` or `absent` fields, so the `range_too_long`, invalid-date and multi-day boxscore loops are gone. Year options skip years that wouldn't resolve. The fallback prompt and hint copy is sensible.
- **Year rollover:** the new rollover is limited to year choices (`parts.year` set, `end_year` unset). The lookup always sets both years itself.
- **Leaders and team-scope pre-check:** it depends only on the request and the published-schedule gate, not on results. Team scope always carries a team after normalization, so in practice it covers leaders.
- **Ambiguous teams:** choices are offered only when there's a single mention and no other team mention. Otherwise the user gets a hint to edit. Two selected teams in a team-stat question clarify with the "name the team whose stat you want" hint.
- **Clarification context:** options use the submission's own context, retry uses it too, and two-step clarifications carry it forward.
- **Smaller UI fixes:** "Show all options" only appears when some option is actually a spoiler. The input limit is now 300.
- **Deadline:** interpretation gets the total minus `min(5 s, 25%)`, and the router keeps the full timeout.
- **Response details:**
  - On a token continuation it shows the stored output's model with no call and no cache hit.
  - Direct lookups report no model.
  - `resolved_model` fits `InterpreterInfo.model`'s 80-character limit.
  - The control sits behind a static `import.meta.env.DEV`, so it should be dropped from production builds. I didn't inspect a build.
  - Minor, dev only: under a gate, "Cache hit" can differ between an answer (the answer cache can hit) and `not_found` (never cached).
- **Design 1 header:** the Ask entry needs `VITE_ASK_ENABLED=1` in production, and the keyboard shortcuts go with it.

## Limits
This was source review of `ask-opus-followup.diff` plus the callers it touches. I ran no tests or builds, read no evaluation files, and made no provider calls. How often Luna produces the ambiguous shapes is still inferred from the schema, not observed. Nothing here says the feature is ready to release.
