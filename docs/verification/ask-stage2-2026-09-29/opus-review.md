# Stage 2 Opus review

Model: claude-opus-5-5. New independent thread 45de1446-2b53-4c15-9c16-0da1a21f5ec8.
Frozen checkpoint: 665030a6, baseline a3377198. Read-only source review; no tests or provider calls by reviewer.

# Ask Stage 2 review: HEAD vs a3377198 (read-only)

I found real defects. The worst are constraints that get dropped silently, so the user sees a confident but wrong number. Beyond the narrow items in the brief, there is a whole class of phrasings the split guard never checks. I ran nothing and made no network or provider calls. BRef markup claims are from memory and are marked as needing a saved-page check.

## High

**H1. Playoff round, series and game constraints are dropped for `player_season_stats`.**
- **Where:** `server/ask/tools.py:110` lists the fields as `{player, teams, season, stat, aggregation, season_type}`. The normalizer ignores any field not in that set (`normalize.py:74-76`). The guard at `season_scope.py:11-19,35` only checks date candidates and a word list, and the word list has no `finals|round|series|game`.
- **Trigger:** "Jokic points per game in the 2023 Finals" or "…in the 2023 Western Conference Finals". Lookup produces a `round` candidate, which is ignored. The request becomes `season_type=playoffs` for 2022-23.
- **Impact:** the whole-postseason average is presented as the Finals average. Nothing in the UI shows that the round was dropped.
- **Fix:** in `normalize_question`, return unsupported when a season intent is selected and any `round`, `game_number` or `location` candidate exists (ignoring `source == "app_context"`). Add a dev case for this.

**H2. `team_records` silently drops a named player.**
- **Where:** `tools.py:120`. The fields have no `player`, and the guard masks player spans (`season_scope.py:30-34`) instead of rejecting them.
- **Trigger:** "Nuggets record without Jokic in 2023-24" or "Celtics record when Tatum plays". Neither `without` nor `when` is in `_SPLIT`, and the player span is masked out.
- **Impact:** the full-season 57-25 record is returned as the answer.
- **Fix:** for `team_records`, any non-context player candidate means unsupported. For `player_season_stats`, a second player candidate also means unsupported.

**H3. Jev's `season_type` and `standings_scope` have no "unspecified" option, so the default's confidence gates acceptance.**
- **Where:** `jev.py:137-138` builds these Choices with no `NONE_OPTION`, so `decide_choice` (`jev.py:190-203`) always returns selected or ambiguous with a probability. `cascade._weakest` (`cascade.py:118-124`) takes the minimum confidence over the relevant fields, and those include both new fields. Below `accept_min=0.7` it clarifies, and `CLARIFY_AS` maps these fields to `intent` (`cascade.py:66,71`). An ambiguous read does the same through `normalize.py:220-221`.
- **Trigger:** "Jokic rebounds per game in 2023-24". Nothing in the question says regular season or playoffs, so a split like 0.65/0.35 is plausible. HTTP runs with `fallback_enabled=False` (`pipeline.py:237`), so it lands straight on the clarification.
- **Impact:** valid questions get "Which kind of question?". `_candidate_options` has no `intent` set, so the prompt has no options, a dead end.
  - A related wrong-answer path: if Jev picks `west` for "Celtics record in 2007-08", `_valid_records` filters Boston out, both sources return NotFound, and the user sees "No record found".
- **Fix:** add a "not specified" option to both Choices that decodes to `absent`. Exclude defaulted closed fields from `_weakest`. Ignore `standings_scope`, or clarify it, when a team is named and the team's conference contradicts it.

## Medium

**M1. The split guard misses common phrasings, so these are answered as whole-season numbers** (`season_scope.py:11-18`):
- "Jokic ppg in wins"
- "per 48" or "per minute"
- "in the clutch", "fourth quarter", "first half of the season"
- "as a starter" or "off the bench"
- "last ten games" (only the digit form is caught)
- "Celtics conference record"
- "in overtime" or "on back-to-backs"

Don't add bare `wins`/`losses`, because case 08 ("Nuggets wins and losses in 2023-24") is an accept case. Use `in (their )?(wins|losses)`, `conference record`, `per\s*48`, `quarter|half|clutch|overtime|starter|bench|back-to-back`, and `last\s+\w+\s+games?`.

**M2. Playoff wording isn't cross-checked against `season_type`.** "Celtics playoff record in 2024" or "Jokic playoff ppg 2023-24" returns the regular-season answer if the interpreter leaves `season_type` absent. The OpenAI prompt tells it to leave the field absent unless it is explicit, and the lookup already knows `PLAYOFF_CONTEXT`.
- **Fix:** if playoff wording matches and `season_type != playoffs`, return unsupported for `team_records` and clarify for `player_season_stats`.

**M3. A percentage with zero attempts is shown as a real 0.0%** (`seasons.py:233-236`). The code passes the NBA `FG3_PCT` through without looking at `FG3A`. When a player took no attempts, NBA appears to report 0 (unverified), so the answer is "0.0%". BRef leaves the cell blank, which becomes Unavailable, so the two sources disagree.
- **Fix:** return `None` when attempts are 0 or missing, or compute the rate from made/attempted and cross-check it against the stated percentage.

**M4. Evaluation scores correct absent reads as wrong** (`eval/trace.py:227-233,293-294`).
- `expected_fields` always sets `season_type={"regular_season"}`, and sets `standings_scope={"league"}` for team questions. An absent read is scored `correct = not expected`, which is False, even though the OpenAI instructions require absent here.
- Luna's field accuracy and the threshold sweeps are biased as a result.
- **Fix:** omit these fields from `expected` when the label matches the default, or treat an absent read as correct when the expected value is the default.
- **Test gap:** no test runs the dev-fixture accept cases through `normalize_question`. `test_development_fixture_labels…` only checks candidates, and `test_new_families…` calls `Normalizer` directly. That leaves guard false positives on accept cases untested.

**M5. The playoff fallback to BRef looks dead.**
- `_heading` (`seasons.py:114-118`) requires the season string, e.g. "2023-24", in the `<h1>`. BRef playoff totals pages are titled by year ("2024 NBA Playoffs …"), so every playoff fallback would be rejected. I'm going from memory here; check a saved page.
- The link allowlist (`response.py:129`) also rejects `playoffs/BAA_1947_totals.html`. That check runs in `_output` after the SeasonData is already cached for a day. The pydantic error escapes `_execute` and shows "Ask couldn't read that question".
- **Fix:** accept a year-form heading for playoffs, allow `playoffs/BAA_\d{4}_totals`, and build and validate the link inside the loader.

**M6. The BRef player parser may not match BRef's current markup** (`seasons.py:146,153,164`). It reads `data-stat="player"` and `"g"`. As I recall, pages since the 2024 redesign use `name_display` and `games`. The code already handles the new `team_name_abbr`, which suggests the mixed format was noticed. Then no name matches, and `GP` is None, which trips the non-negative-integer check and raises. The test fixture uses the old names. Only the standings fallback was checked live. Verify against a saved page.

**M7. "NBA standings" (league scope) are grouped East then West, not by record** (`seasons.py:374`). NBA rows always carry `conference`, so the sort key starts with conference. A 60-win West team shows up in row 16 of a table labeled "NBA standings". This also contradicts the code comment and `docs/ask-stage2.md` ("ordered by percentage").
- **Fix:** for `standings_scope == "league"`, sort by `-win_percentage` then name, and keep the conference rank only as a per-row label.

**M8. Two problems with the shared BRef token.**
- `_load` (`seasons.py:240-263`) falls back even when NBA returned a well-formed career payload that simply lacks that season, or lacks a stat that wasn't tracked then (steals and blocks before 1973-74).
  - This spends the process-wide token, one request per 6 s, which boxscore line scores also need.
  - When throttled, an honest not-found becomes "NBA data isn't responding".
  - Suggested rule: skip the fallback for a well-formed NBA miss and for stat/era gaps that are known to be structural.
- Boxscore regression: `game_summary.py:554-569` silently falls back to `periodScoreSource: "unavailable"` when throttled. The 200 response is then cached client-side, so under any concurrent Ask or boxscore fallback traffic, old-game quarter scores disappear with no signal.

## Low

- **L1. BRef team-stint codes are not mapped** (`seasons.py:161`). `to_bref_team_code` only overrides HUS, BOM and DEF. The catalog uses PHX, BKN and CHA (Hornets, 2014 on), while BRef uses PHO, BRK and CHO. Suns, Nets and Hornets stint fallbacks can never match.
- **L2. Clarification continuations mask with stale offsets** (`season_scope.py:30-34` via `pipeline.py:277`).
  - The continuation question is the rewritten text ("Curry" becomes "Stephen Curry"), but the candidate spans are offsets into the original question.
  - Masking hits the wrong characters. For example, the original season span can land on and hide "home".
  - The first pass usually catches split words before a clarification is issued, so this is latent.
  - **Fix:** store the original question in `PendingResolution` and run the guard on it.
- **L3. Uncertain `aggregation` fails instead of clarifying.** Low confidence goes to `FailDecision`, because aggregation isn't in the clarifiable fields. For season stats, total vs per-game matters, so this shows "Ask couldn't read that question".
- **L4. Interpretation readout changes** (`present.py:41`):
  - Stat items no longer appear on clarifications (request is None). That is a regression for the existing boxscore "Which Jalen?" readouts.
  - Every boxscore now shows "Measure: Total".
  - Team-record readouts show "Conference: League".
- **L5. UI nits:**
  - `as_of.slice(0,10)` takes the UTC date, so the date is a day ahead after 8 pm ET.
  - The player-season fixture's href is a teams URL, not the player URL the code produces.
  - The standings table's `overflow-x-auto` wrapper isn't focusable, so it can't be scrolled by keyboard.
- **L6. Nit:** the `_complete` comment (`seasons.py:55-58`) says an October 1 cutoff covers the 2020 late playoffs. The 2020 Finals ended October 11.
- **L7. Worst-case latency:** two 4 s NBA attempts plus backoff, plus 5 s for BRef, exceeds `resolver_reserve` (at most 5 s). Joined cache waiters have no `wait_timeout`.

## Unverified operational and release items (not defects)

- BRef markup, per M5 and M6.
- Whether the BRef standings `team_name` cell includes a seed like "(1)". `name_key` would keep the "1" and fail the name match. That conflicts with your live run returning 15 eastern teams, so confirm which season you ran.
- Whether historical `LeagueStandings` rows use historical team names, and the "New Orleans/Oklahoma City" spelling. A mismatch should fall back cleanly.
- Whether NBA returns 0 or null for stats that weren't tracked in early seasons. If it returns 0, the answer shows "0" instead of Unavailable.
- Whether the NBA and BRef hosts are reachable from production. The limiter is per process only; your doc already says so.
- The unseen release set, ADR 0009 gates, and Laya shadow numbers are still outstanding. The 21 dev labels were written with the implementation. Production flags are untouched.

## Adversarial tests to add (offline)

- "Jokic ppg in the 2023 Finals" and "Nuggets record without Jokic 2023-24" should be unsupported.
- "Celtics playoff record 2024" with `season_type` absent should not be answered.
- A Jev output with `season_type` at p=0.6 and no mention should be accepted, not clarified on intent.
- A `FG3A=0` row should give Unavailable.
- A saved modern BRef totals page, a playoff totals page, and a conference standings page with seeds.
- League-scope row order.
- Dev accept cases run through `normalize_question`.
- Trace `field_reads` with an absent default.

## What I read

- **Read:** the whole frozen diff; the current `normalize.py`, `pipeline.py` (answer, pending and execute paths), `present.py`, `cascade.py` (policy), `jev.py` (questions and decode), `tools.py`, `trace.py` (expected fields and scoring), `cache.py`, `ttl_cache.py`, `candidates/text.py` and `teams.py`, parts of `lookup.py` and `dates.py`, `resolvers/output.py`, the relevant parts of `game_summary.py`, and ADRs 0003, 0006 and 0010.
- **Not read:** ADRs 0004 and 0009, `openai_responses.build_schema`, `eval/runner.py` beyond the change, `AskLinks`, `patterns.round_mentions`, and the `AskSeriesResult` change beyond the diff.
- **Not verified:** any live source behaviour.
