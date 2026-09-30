# Independent Opus 5.5 recheck

Session `45de1446-2b53-4c15-9c16-0da1a21f5ec8`; requested frozen commit
`c875ee06`; reviewer explicitly observed and inspected the current `bbc2500e`
files. Model reported by CLI: `claude-opus-5-5`. Read-only, no network/tests.

# Stage 2 fixes recheck (frozen c875ee06 vs 665030a6, read-only)

**Checkout mismatch:** this worktree's branch ref is `bbc2500e`, not `c875ee06`, and some files differ from the frozen diff. For example, `normalize.py:224-228` now limits the aggregation clarification to `player_season_stats`, and `season_scope.py:25-36,66-67` adds `ambiguous_season_candidates`. Neither is in `review-fixes.diff`. I reviewed the frozen diff and say below wherever the current tree differs.

## Status of the original findings

| Finding | Status |
|---|---|
| H1 rounds/games | Fixed. Any non-context `round`, `game_number`, `location` or `date` candidate, or finals/round/series/game wording, means unsupported (`season_scope.py:18,59-60`). |
| H2 player dropped from team records | Fixed. Any player candidate on `team_records` means unsupported; so do two or more distinct player mentions on `player_season_stats` (`:61-65`). |
| H3 no "unspecified" option | Mostly fixed. Jev now offers NONE for both selectors (`jev.py:137-138`). An absent read and the explicit default no longer veto each other (`tiered.py:126-137`). A named team plus a conference is rejected (`normalize.py`, `request.py` validator). Remaining gap in N2. |
| M1 split wording | Fixed for all the phrasings I listed. |
| M2 playoff wording | Fixed (`season_scope.py:68-73`). |
| M3 zero-attempt percentages | Fixed (`seasons.py` `_value`). |
| M4 eval scoring | Fixed for `season_type` and `standings_scope`. Dev accept labels now go through the guard. Aggregation gap in N1. |
| M5/M6 BRef playoff and markup | Fixed, as far as the saved excerpt shows. The fallback now uses the `leagues/…_totals` page with `totals_stats` / `totals_stats_post`, and reads `name_display` and `games`. Source links are validated inside the loader, so a bad link can't be cached. |
| M7 league standings order | Fixed. |
| M8 fallback on NBA miss | Accepted as dispositioned: it follows ADR 0010's non-coverage rule, the skipped era gaps cover the listed stats, and a busy fallback gives unavailable, not no-record. |
| L1 BRef team codes | Partly fixed, and it introduces a regression (N4). |
| L2 continuation masking | Fixed by matching on text instead of offsets. |
| L3 aggregation not clarifiable | Fixed, with side effects (N1, N5). |
| L4, L5, L6 | Fixed. |
| L7 cache waiters | Partly fixed (N6). |

## New or remaining defects

**Two items should be fixed before calling the implementation done:** N1 and N3. Everything else is low priority.

**N1. Medium. Aggregation default isn't treated as equivalent, so the "Season totals / Per game" choice can appear on single-game boxscore questions.**
- **Where:** `tiered.py:129` and `trace.py:294` only list defaults for `season_type` and `standings_scope`. Jev always selects `aggregation`, since it has no NONE option there. Luna may leave it absent.
- **What happens:** the earlier selection and the later absent read count as a veto. The field keeps a sub-threshold confidence, `_weakest` picks it, and `_clarify("aggregation")` goes through because `aggregation` is now a `ClarifyField` (`common.py`). `present.py:162-175` then offers "Season totals / Per game" whatever the intent is.
- **Trigger:** "How many points did James Harden score on March 9, 2026?", when Luna runs for any field and leaves `aggregation` absent. The user sees options like "…March 9, 2026 season totals?" for a single game, and "Per game" leads to unsupported. Before this change the same path ended in a fail.
- **Season tools too:** the same path adds an unnecessary aggregation clarification to "Jokic rebounds in 2023-24".
- **Current tree:** the normalizer-side limit on the working tree doesn't cover this cascade path.
- **Fix:**
  - Add `aggregation: "total"` to both default tables.
  - For boxscore, only offer the aggregation clarification for `player_season_stats` (or map it to fail).
  - Correct the stale comment at `common.py:62` ("aggregation is never clarified").

**N2. Low. Uncertain `standings_scope` still hits a dead end.** It is still mapped to `intent` (`cascade.py:66`, `normalize.py:220-221`), and the "Which kind of question?" prompt it produces has no options. NONE makes this rarer, but when Jev spreads probability across east, west and league it can still happen. Fix: give it closed choices like `season_type` has, or treat an ambiguous `standings_scope` without a team as league-or-clarify.

**N3. Medium-low. "Regular season and playoffs" silently loses one half.**
- **Trigger:** "Jokic total points in 2023-24 including playoffs", or "…regular season and playoffs".
- **What happens:** with `season_type=playoffs` selected, the guard passes (`season_scope.py:68-73`) and only playoff totals are returned. With `regular_season` selected, the clarification makes the user pick one half.
- **Fix:** when both regular-season and playoff wording appear, or `including|combined|plus` appears next to playoffs, return unsupported.

**N4. Low. Regression from the L1 fix: Charlotte Bobcats stints now map to the wrong BRef code.**
- **Where:** `seasons.py:163` maps `CHA` to `CHO` unconditionally. The catalog uses `CHA` for both the Bobcats (2004-13) and the Hornets (2014 on) (`franchise_history.json:92-93`). BRef uses `/teams/CHA/…` for the Bobcats years.
- **Impact:** every Bobcats team-stint fallback misses. The result is unavailable or no-record, never a wrong number.
- **Fix:** map to `CHO` only when the season starts in 2014 or later.

**N5. Low. The closed-choice rewrite leaves contradictory wording** (`present.py:165-170`).
- The aggregation pattern doesn't strip `ppg|rpg|apg|averaged`, so the rewrite can read "Jokic ppg in 2023-24 season totals?". The resolution token executes the right request, but the question shown to the user and saved in history contradicts it.
- For `team_records`, the season-type choice offers "Playoffs", which can only return unsupported.

**N6. Low, deployment work. The 5 s waiter bound sits below the answer cache.**
- **Where:** `pipeline.py:180` coalesces identical requests on the answer cache with no `wait_timeout`, before the season cache is ever reached. For identical HTTP requests, the 5 s bound at `seasons.py:409` therefore mostly doesn't apply.
- **Why it isn't a new unbounded-worker problem:** the leader's own time is limited by the source timeouts (around 14 s), and the HTTP route caps the response.
- **Tracking:** this belongs with nba-scores-8ic. Add a `wait_timeout` to the answer layer when you do it.

**N7. Low. Guard false positives and a gap.**
- `\bround\b` matches "all-around" ("Jokic all-around stats 2023-24"), making it unsupported.
- The era-gap list (`seasons.py` `_valid_player` and the `player_season` pre-check) doesn't include rebounds before 1950-51. If NBA returns 0 rather than null for those seasons, the answer would show "0". That depends on NBA's payload, which I haven't verified.

## Deferred items, in context

None of the deferred items produces a wrong local answer:
- **M8 / nba-scores-cnm:** the boxscore page gets `periodScoreSource: unavailable`, which is degraded but not wrong data.
- **L7 / nba-scores-8ic:** bounded by the source timeouts and the HTTP cap, apart from the N6 note.
- **Still outstanding before release:** host access, the multi-replica limiter, the unseen gates and the manual accessibility checks. None of this is claimed as done.

## What I inspected and what I didn't verify

- **Inspected:**
  - All of `review-fixes.diff`, `review-fixes.md` and `docs/ask-stage2.md`.
  - The current `season_scope.py`, `present.clarification`, `resolution.choose`/`read`, `normalize._optional`, `cascade._clarify`/`_weakest`, and the tiered merge (veto registration and `_fields`).
  - The lookup's entity and location mention order, `franchise_history` for Charlotte, and the `pipeline._execute` answer cache.
  - The new tests and the saved BRef excerpt.
- **Not verified:**
  - That the working tree's extra changes match any commit.
  - That live BRef pages for older seasons include `totals_stats_post`.
  - NBA's null-vs-0 values for early-era stats.
  - How often Luna leaves aggregation absent.
  - Your 119-test result; I ran nothing.
