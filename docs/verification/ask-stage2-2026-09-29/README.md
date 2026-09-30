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

## Final verified state

After Opus's final recommended wording guard and extra abbreviation rewrites:
**1,348 backend tests pass**. Final frontend checks also pass: **478 tests**, lint and build. The final Opus review is saved in
`opus-final-review.md`; it found no implementation blockers, and its remaining
combined-phase wording recommendation was then implemented and tested. The
review's deployment follow-ups remain open. `development-replay-reviewed-final.json`
replays against the final reviewed implementation without provider calls and
retains **20/21**, zero guesses, and the safe unsupported-reason mismatch.

The temporary screenshot server originally blocked fonts from the symlinked
worktree dependency directory. Final environment-only recaptures use the existing
`vite.preview.config.mjs` allowed-directory config. `verified-*.png` and
`ui-check-fonts-verified.json` have no HTTP/page errors, no page overflow and one
source link per result on desktop light and mobile dark. Hardwood's Poppins
font is loaded; Archivo is not used by that surface. These recaptures changed no
product styles. The temporary port5292 server was stopped; the user's existing
port5289 preview/backend8019 were left running.

The final screenshot check caught source-specific wording in the existing
zero-model footer: it said "NBA data" even on a BRef answer. The footer now says
"basketball data", with the actual named source still alongside it. Frontend
tests, lint and build were rerun, and the verified screenshots recaptured.

Stage 2 task **nba-scores-8k5** is closed. Deployment follow-ups remain open.
Issue metadata was exported locally with no pull/push. Only the three Stage 2
issue records are copied into this branch; other issue updates and original
untracked files in the primary workspace are preserved.
