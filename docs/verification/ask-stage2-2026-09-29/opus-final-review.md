# Final independent Opus 5.5 source review

Session `45de1446-2b53-4c15-9c16-0da1a21f5ec8`; reviewed frozen implementation
`fd216d3e776fddb5d60c822749a90af4900a6120`. CLI reports model `claude-opus-5-5`.
Read-only; reviewer did not run tests or provider calls.

# Final recheck of Stage 2 corrections (checkout fd216d3e)

**Verdict:** I found no implementation blockers. One narrow wrong-answer risk remains (R1 below); I'd fix it, but it doesn't block. The branch ref is `fd216d3e776f…`, and the current files match `final-corrections.diff` at every place I checked.

## N1–N7: behaviours I traced

- **N1 (aggregation default and boxscore regression): fixed.**
  - In the tier veto, an absent aggregation now counts the same as `total` (`tiered.py:129`). Trace scoring does the same (`trace.py:294`).
  - The cascade only asks the measure question for `player_season_stats` (`cascade.py:73`). Every call to it now receives the output (`:132-137`, `:166`, `:175`, `:183`).
  - The clarification screen also offers no measure choices outside that tool (`present.py:172`).
  - A valid boxscore with low aggregation confidence now falls back or fails, which is what the pre-Stage-2 baseline did. The new test for that path matches the real policy branch.
- **N2 (standings scope dead end): fixed.**
  - An uncertain standings scope now asks about `standings_scope` itself; it is no longer mapped to `intent`.
  - It offers league, east or west choices, and `choose` accepts only those values (`resolution.py`).
  - When a team is named, only "NBA league" is offered, so the answer can't hit the team-plus-conference unsupported path.
- **N3 (combined regular season and playoffs): fixed for the listed wordings**, whichever phase the interpreter picked (`season_scope.py:69-72`). One gap remains (R1).
- **N4 (Charlotte BRef code): fixed.** `CHO` is used only when the season's end year is 2015 or later (`seasons.py:163`). The Al Jefferson 2013-14 fixture checks that the older `/teams/CHA/2014.html` link still works.
- **N5 (clarification wording): fixed.**
  - `ppg`, `rpg` and `apg` are expanded before "per game" is stripped, and "averaged" is stripped too.
  - For team records, the season-type choice now offers only "Regular season".
  - Remaining copy-only nits, where the resolution token still executes the right request:
    - `spg`, `bpg` and `mpg` are not expanded.
    - Stripping "average" can leave broken grammar, e.g. "did Jokic in 2023-24 season totals?".
- **N6 (answer-cache waiters): fixed.** Joined waiters for the two season tools now give up after 5 s (`pipeline.py:183`). The timeout returns `service_unavailable`, and this happens inside `_execute`, which covers the continuation path as well.
- **N7:**
  - My "all-around" claim was wrong: in "all-around", "round" follows "a", so the `\bround\b` pattern can't match. The regression test you added is reasonable.
  - Rebounds before 1950-51 are now treated as missing, and a specific rebounds question for those seasons skips fetching (`seasons.py:212`, pre-check near `:284`).

## Remaining risk (not a blocker)

**R1. Low–medium: "season and playoffs" without the word "regular" still loses half the scope.**
- **Trigger:** "Jokic total points in 2023-24 season and playoffs" or "…regular and postseason", with the interpreter selecting `season_type=playoffs`.
- **What happens:** none of the three combined-phase patterns match, so the guard returns valid and the answer covers only the playoffs.
- **If the interpreter picks regular season instead:** the question goes to the season-type clarification, and the user explicitly chooses one half, so nothing is dropped silently.
- **Fix:** add a pattern like `\b(?:season|regular)\s+(?:and|&|\+)\s+(?:the\s+)?(?:playoffs?|postseason)\b` and a regression case.

## Deployment-only follow-ups (not implementation defects)

- Retry and display of historical boxscore quarter scores when BRef is throttled (nba-scores-cnm).
- A shared retrieval deadline and slow-host tuning (nba-scores-8ic). The new 5 s bounds cover waiters only; the loader doing the fetch is still limited just by the source timeouts and the HTTP cap.
- A BRef limiter shared across replicas.
- NBA and BRef access from the production host.
- Independent unseen labels and the ADR 0009 gates.
- Laya shadow numbers.
- Physical keyboard and screen-reader checks.

## Inspected, and not verified

- **Inspected:**
  - The Recheck corrections subsection of the disposition doc.
  - The code and test parts of `final-corrections.diff`.
  - The live `cascade.py`, `pipeline.py`, `present.py`, `seasons.py` and `season_scope.py` at the lines cited.
  - The frontend `AskClarifyField` usage.
- **Not verified:**
  - I skimmed the replay and probe JSON artifacts but didn't audit them.
  - The cited NBA FAQ and live BRef results.
  - The 140 passing tests and the full test, lint and build run; I ran nothing.
