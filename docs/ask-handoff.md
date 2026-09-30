# Ask development handoff

Work on branch `ask/reviewed-components` in `/private/tmp/ask-reviewed-components`.
The original workspace at `/Users/alexcurtis-slep/Documents/projects/nba-scores`
is on `language-search` and contains unrelated untracked files. Preserve them.
All implementation changes are local; nothing has been pushed.

## User scope and preferences

Only Design 1, Gold on Hardwood, matters for this work. Do not spend time on
Design 0 parity or delete it yet. The user asked for Luna and Sol coding help,
then specifically requested an Opus 5.5 code review. They challenged the runtime
Luna choice because Jev had not received equivalent calibration work. Treat the
production model choice as open. Do not claim the existing comparison proves
one model is inherently better.

## Live preview

Open `http://127.0.0.1:5289/design-1?ask=live` and click Ask. It uses actual NBA
data and the local backend on port 8019. The old Harden fixture interception
has been removed. The preview frontend lives in `/private/tmp/ask-resume-ui`;
its local Vite configuration proxies `/api` to 8019. Keep the user's preview
running. Browser tab 3 belongs to the user's testing; tab 4 was used for checks.

Expand **Response details** below an answer to see the reported interpreter
model, whether a model call occurred, and the cache flag. The dev preview
currently uses GPT-6 Luna at low effort. Models interpret questions; Python
resolvers return verified NBA data. Exact dated game searches can use no model.
The control is omitted from production bundles. Design 1's Ask entry also stays
off in production unless `VITE_ASK_ENABLED=1`; backend activation independently
requires `ASK_ENABLED=1`.

## Verification and review

The full frontend suite passed 463 tests using
`NODE_OPTIONS=--no-experimental-webstorage pnpm test:run`.
The Node runtime's native storage conflicts with jsdom; a localStorage file
workaround caused unrelated StorageEvent failures. Lint and build passed.
The full backend suite passed 1086 tests using the original workspace's
`server/venv/bin/python -m pytest -q server/tests --tb=short` from this worktree.

Opus 5.5's original review is saved in
`docs/verification/ask-opus-review-2026-09-29.md`. It found spoiler-dependent
clarifications, looping date choices, lossy team clarification, a production
feature flag omission, invalid aggregation handling, lost clarification context,
an inert reveal button, timeout allocation, recent player-log lag, and cross-year
choices. Fixes are committed through `80b5570`; frontend fixes are applied to
the live preview. The unsafe suggestion to reconstruct unselected teams from
text spans was replaced with edit guidance when the frozen schema cannot retain
all constraints. Opus rechecked the fixes in Claude session
`5c1438ac-6ee7-48ce-9982-caa2e4f5ae4e`; its unaltered follow-up is saved in
`docs/verification/ask-opus-recheck-2026-09-29.md`. Subsequent corrections through
`b0ef08a` were verified with focused tests and a final backend run. No claim is
made that Opus separately approved every subsequent line.

Use `/Users/alexcurtis-slep/.local/bin/claude` for Opus 5.5. That installation is
2.1.284; the Homebrew binary is an older 2.1.212 that cannot run this model.

## Review disposition

- Spoiler-sensitive clarification now happens before result lookup for nonunique
  playoff selectors. Player scope is included. Fully specified Finals and
  conference finals remain answerable; date-plus-Finals without a complete
  selector conservatively clarifies because the current resolver counts date
  games before validating the round.
- Recent empty player logs with other games on the scoreboard now return a
  gated neutral no-record result, rather than an ungated unavailable result or
  a claim that the player did not play. The fallback makes one scoreboard read.
- Invalid dates and overlong ranges cannot offer themselves again. Year choices
  rewrite cross-year ranges with explicit endpoint years and retain the rest of
  the question. Without a date span, the user must edit rather than accepting a
  rewrite that could discard the requested team, player, or statistic.
- Multi-span team ambiguity and two-team stat focus require editing. The frozen
  model output cannot reliably preserve their distinct roles; no team is inferred
  from text spans or selected-list order.
- Unresolved aggregation returns invalid without crashing or guessing. Invalid
  normalization is not cached, so retry can recover.
- Clarifications preserve submission context, empty reveal controls are gone,
  input accepts 300 characters, and the model leaves time for NBA retrieval.
- Only Design 1's production entry was gated. The original header remains outside
  the user's requested scope. Opus's proxy-rate-limit observation was conditional
  on deployment settings and was not treated as a proven local defect.

## Remaining release work

Production remains disabled. The first independent 80-question release run
scored 75/80 with three guesses; the second scored 64/80 with seven guesses and
one invalid-output failure. Both reports and exposed labels are committed.
Some second-set labels have documented contract conflicts; do not silently
rewrite them or reuse either set as unseen evidence.

The earlier 43-case comparison favored the configured Luna implementation,
but Jev confidence thresholds were uncalibrated and Luna had no confidence
veto. Diagnose extraction versus policy rejection, calibrate on exposed data,
freeze both configurations, then compare on a new independent unseen set.
The paired exposed 80-case comparison is recorded in
`docs/verification/ask-jev-luna-regression-2026-09-29.json`. Jev scored 48/80 with
zero guesses and a 173 ms median; Luna scored 67/80 with four guesses and a
2,402 ms median. Neither passed. The production adapter factory currently
instantiates OpenAI only; wiring Jev into the live pipeline requires code, not
just changing `ASK_PARSER_MODEL`. This is implementation debt from the premature
selection, not a model capability limitation. Do not launch more provider calls until checking the
remaining original $3 evaluation authorization and existing reports. Provider
keys remain in the original workspace's server/.env; never print them.

The interpreter has no separate field for target team versus matchup teams.
Two-team stat questions conservatively require an edit instead of returning
both teams or guessing a target. A typed schema extension is needed for full
support. Physical mobile keyboard and screen-reader checks also remain.

Beads issue `nba-scores-kzc` remains in progress. Follow-ups `nba-scores-kzc.1`
and `nba-scores-kzc.2` track target-team representation and the failed release
gates. Issue metadata changes are in the original workspace's `.beads` directory.
