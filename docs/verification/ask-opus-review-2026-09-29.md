# Opus 5.5 source review

Model: `claude-opus-5-5`. Read-only Claude Code review, session `5c1438ac-6ee7-48ce-9982-caa2e4f5ae4e`. Requested base `54295ce`, initial head `b4e0229`. Other local fixes landed while the review was running; the diff input was frozen at the initial head. The reviewer ran no tests.

I found 4 medium issues, 1 low-to-medium and 5 low, plus 2 points I couldn't confirm. The worst is a spoiler leak: a hidden answer can show up as a clarification before the user reveals anything. Nothing was run; every finding comes from following the code paths and checking them against `docs/ask-contract.md`.

## Medium

**1. A clarification raised by a resolver skips the spoiler gate, so the outcome shows before reveal**
- **Where:** `server/ask/resolvers/__init__.py:114-122` attaches the gate only to answers and `NotFoundError`. `pipeline.py:171-175` returns `needs_clarification` with no gate. `resolvers/games.py:228-234` raises `AmbiguousError` when a date has more than one game. `spoiler_policy.py:72-73` gates every playoff date.
- **Trigger:** "Who led in rebounds on <playoff date>, <year>?" The Luna prompt (`openai_responses.py:84-87`) steers this to leaders scope with only a date. The resolver then counts the games actually played that day:
  - one game: a gated answer;
  - no games: a gated `not_found`;
  - two or more: a "Which teams?" clarification with no gate.
- **Impact:** When the schedule has an if-necessary game that day, getting the clarification tells the user it was played, which reveals series length. `AskResult.tsx:29` only hides content when `spoiler_gate` is set. `_select_series` ambiguity ("Game 2 of the 2026 conference semifinals" mid-playoffs) has the same shape but matters less.
- **Fix:** Before calling the resolver, check whether the request is gated, uses leaders or team scope, has no teams and uses a date or a non-Finals round. If so, raise `ClarificationError("teams", "missing")` every time. The clarification then depends only on the question, never on which games were played.

**2. Some date clarifications offer only the same unusable date, so the user loops**
- **Where:** `present.py:116-123` offers every candidate in the field's set when the field isn't ambiguous. `normalize.py:215-216` turns `range_too_long` or `invalid_date` (reported as `missing`) into a clarification. `normalize.py:298-299` turns a multi-day range in a boxscore question into `date/ambiguous`.
- **Triggers:**
  - "games from March 1 to March 20, 2024": the only option is "… (longer than 7 days)".
  - "games on February 30, 2024": the only option is "(not a real date)".
  - "Brunson points this week": the only option is the same week.
  - "games in March": choosing a year produces a 31-day range, then the same loop.
- **Impact:** Each option's token rebuilds the same state, so choosing it returns the identical clarification. Zero model calls, but the user is stuck.
- **Fix:** In `_candidate_options`, offer candidates only when the field is `ambiguous` or `absent`. Always drop the currently selected IDs. The hint text then covers the rest.

**3. Choosing one team in a teams clarification can drop the other team the user named**
- **Where:** `resolution.py:126-132` replaces the whole `teams` field with the single chosen candidate.
- **Trigger:** "Knicks vs LA games last week". The schema has no way to say "one team selected, one ambiguous", so the model returns `teams: ambiguous [LAL, LAC]` (or all three). The user picks the Lakers. The rewritten question reads "Knicks vs Los Angeles Lakers…", but the stored request is `teams=[LAL]`.
- **Impact:** The app answers with every Lakers game, which doesn't match the question text it shows. I haven't confirmed how often Luna produces this shape.
- **Fix:** In `choose` for `teams`, keep team candidates from other spans that are the only candidate for their span, plus the chosen one, up to 2.

**4. The Ask entry always appears in the Design 1 header, even though the backend is off by default**
- **Where:** `HardwoodHeader.tsx` (the `<AskEntry />` added around line 41), `router.py:31-32` and `pipeline.py:83-85`.
- **Trigger:** Any deploy without `ASK_ENABLED`, while Design 1 is a registered public design (`designRegistry.ts:5`).
- **Impact:** Every question shows "NBA data isn't responding · Try again in a moment", which is retryable and wrong. There's no frontend flag at all (a search for `VITE_ASK` finds nothing).
- **Fix:** Gate `AskEntry` behind a build flag such as `VITE_ASK_ENABLED` that defaults to off.

## Low-medium

**5. A non-selected `aggregation` crashes the normalizer**
- **Where:** `normalize.py:252` calls `_optional("aggregation")`, which raises `_Clarify("aggregation", …)`. At `normalize.py:156-157`, building `NormalizationResult(clarify_field="aggregation")` then fails validation, because `ClarifyField` excludes `aggregation`.
- **Trigger:** The strict schema lets aggregation come back `ambiguous` with `[total, per_game]`, or as `no_matching_candidate`.
- **Impact:** The live path returns `interpreter_unavailable`. The model output is cached for an hour (`pipeline.py:140`), so retries fail the same way. On the token path, `_from_pending` sits outside the try block, so the router returns `service_unavailable`.
- **Fix:** In `_boxscore`, treat any non-selected aggregation as `total`, or catch it and return unsupported `multi_game_average`.

## Low

6. **A clarification option picked after navigating away can cost a model call.** `AskPanel.tsx:97-108` sends the current page's context, but the token is bound to the original context (`resolution.py:86`). If the user closes the dialog, changes page and then picks an option, the token is silently ignored and the question goes through the paid model path again. **Fix:** store the submission's context and resend it when an option carries a `resolution`.
7. **A "Show all options" button that does nothing.** `AskClarification.tsx:69-77` shows it on every clarification while results are hidden. The server never sets `spoiler: true` on options (the `app_context` team check at `present.py:165-167` can never fire, because lookup never produces `app_context` teams). **Fix:** render it only if some option has `spoiler: true`.
8. **No time is reserved for the resolvers after the model call.** The router timeout and the pipeline deadline are the same value (`router.py:35`, `pipeline.py:186`).
   - A slow model call plus slow NBA fetches means a paid answer is thrown away with "NBA data isn't responding".
   - The worker keeps holding one of the two `max_in_flight` slots. Other users then get busy errors with the same wrong copy.
   - **Fix:** give the pipeline a shorter deadline than the router timeout (for example 3–5 s less).
9. **"Player did not play" during or just after a game.** Player + date questions depend on LeagueGameFinder (`games.py:270-275`, `data.py:137-149`), which lags live and just-finished games. The result is `not_found` / "Player did not play" while the player is actually playing (cached for 5 minutes). **Fix:** for today and yesterday, try the scoreboard or boxscore for that date before claiming the player didn't play.
10. **Year choice breaks cross-year ranges.** "Dec 28 to Jan 3" plus a chosen year gives `end_year = year` (`resolution.py:115`), so the end comes before the start and the date is invalid. This then feeds the loop in #2. **Fix:** set `end_year = year + (end_month < month)`.

## Uncertain
- **Per-client rate limit behind a proxy:** it uses `request.client.host` (`router.py:24-26`). If the deployment sits behind a proxy that uvicorn doesn't trust, all users share one 10-per-minute bucket. This depends on deployment settings I couldn't see.
- **Input length:** the search field caps typing at `maxLength={200}` (`AskSearchField.tsx:35`), while the contract allows 300 characters. This is inconsistent but probably harmless.

## Checked and correct
- **Clarification tokens:** random, server-stored, bound to the question and context, 15-minute lifetime, validated again before use.
- **Budget:** each call reserves up front and settles afterwards, and an unknown bill counts as the full reservation.
- **Model output:** a strict enum schema, with candidate IDs checked again in Python.
- **Links:** checked against the allowlist.
- **Typeahead:** `hidden` filtering happens on both server and client.
- **Spoiler rendering:** gated views render only the gate copy, non-spoiler interpretation chips and a reveal control; hidden values are omitted from the DOM through `guarded` and `withoutSpoilers`.
- **Footer:** doesn't reveal whether sources are complete while hidden.
- **Final score:** has its own reveal.
- **Reveals:** reset on every new question.
- **Suggestions:** contain no participants the server inferred.

## Coverage and limits
- **Read in full:** pipeline, router, config, budget, cache, limits, resolution, present, normalize, cascade, the OpenAI adapter, HTTP retry code, pricing, lookup and date parsing, all resolvers, spoiler policy, links, suggest and diagnostics. On the frontend: session store, service, panel, dialog, entry, result renderers, clarification, notices, links, suggestions and typeahead.
- **Skimmed or not read:** `patterns.py`, `players.py`, `teams.py`, aliases and `text.py`, `closed_sets`, `jev.py`, the eval code, `stats.py`, most of `response.py`, `types.ts`, `askFormat`, the viewport hook and the tests.
- **Not done:** I ran no tests and no provider calls. How often the model produces the shapes in #3 and #5 is inferred from the schema, not observed.
