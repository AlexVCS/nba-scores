# Stage 2 checks

Initial checkpoint: full backend 1,271 tests, full frontend 477 tests, lint and
production build passed. The build retains the existing large-bundle warning.
After the live NBA standings check, a strict historical-name check was amended
to accept the provider's official "LA Clippers" alias for Los Angeles Clippers;
a regression test covers that alias and rejects a wrong franchise.

`source-probe.json` contains direct live tool results, not interpretation accuracy:
Jokic 2023-24 regular-season rebounds, Boston's 2007-08 record, 2023-24 Eastern
standings, and Jokic's 2024 playoff points. NBA supplied player and team data;
Basketball-Reference supplied the first standings probe when the NBA alias check
rejected LA Clippers. The fallback record preserves the actual source. No model
was called by these probes. Backend request timings are local, not host evidence.

Desktop light and mobile dark captures show the new result types using contract
fixtures. The standings fixture uses the live fallback rows. These UI checks
verify rendering, source links and no horizontal page overflow; they do not
replace physical-device keyboard or screen-reader checks. An initial capture
caught the dialog during its entrance animation; the final images wait for it.

Impeccable's detector reported one advisory: the 56px stat numeral is outside the
written font ramp. It matches the existing Ask single-stat result; retained.

A fresh Opus 5.5 source review follows this checkpoint. See the review and
follow-up artifacts here for findings and disposition. Production stays off.

## Checks after review fixes

- Backend: **1,317 passed** (`python -m pytest server/tests -q`).
- Frontend: **478 passed**, 36 files (`NODE_OPTIONS=--no-experimental-webstorage pnpm test:run`).
  This machine runs Node 26.5, whose native global localStorage conflicts with
  the existing jsdom test environment; disabling experimental native webstorage
  lets the tests use jsdom's storage. The first plain-pnpm run failed on that
  environment issue. No product storage code was changed for it.
- `pnpm lint` and `pnpm build`: passed. The existing bundle-size warning remains.
- The full backend run initially caught unintended boxscore normalization
  behavior from making aggregation clarifiable. That behavior is preserved for
  old tools; totals/per-game ambiguity clarifies for the new season-stat tool.
  An outdated invalid-label test now uses an actually invalid field name.

The second paid development run is saved as `development-eval-after-review.*`:
**19/21**, one bare-year season guess, zero service failures, p95 **5,148 ms**,
accounted list-price cost **$0.005539822** (actual billing unknown). It removed
unneeded default-veto clarifications but exposed a confident model selection for
"Celtics record in 2008". The first run remains saved separately, **16/21** and
**$0.008353894**. These are development runs, not independent release evidence.

The final season guard requires a choice for a bare year that offers two seasons,
regardless of model confidence. Choices use exact season rewrites and validated
continuation tokens. `development-replay-final.json` replays the second run's
recorded tier outputs without provider calls: **20/21**, zero schema-valid guesses,
4/4 required clarifications, zero service failures. Replay latency and cost do
not describe a new live run. One safe unsupported answer still has the wrong
reason (`multi_game_average` instead of `other` for a month split). Labels and old
results were not changed to erase this miss.

`fallback-probe-after-review.json` exercises actual BRef fallback with primary
intentionally unavailable: regular-season rebounds **12.4 over 79 games** and
playoff points **28.7 over 12 games**. Both use the correct season totals page,
separate phase tables, verified links and source metadata. These direct tools
made no interpreter calls. A saved current page excerpt tests the UTF-8 player
name and modern column names for both phases and a named team stint.

The Opus finding disposition is in `review-fixes.md`. Deployment follow-ups
**nba-scores-8ic** (retrieval budget) and **nba-scores-cnm** (boxscore fallback
cooldown/retry) remain open. Production flags are unchanged; independent unseen
six-family gates, Laya dev shadow (no endpoint configured), host and physical
keyboard/screen-reader checks still remain.
