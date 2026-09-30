# Ask development handoff

## Stage 2 checkpoint, September 29

Player season stats and team records/standings are now implemented locally on
`ask/reviewed-components`. See `docs/ask-stage2.md` and
`docs/verification/ask-stage2-2026-09-29/` for scope, checks and review.
This supersedes the "next step is stage 1" note below. Production is still off;
the old frozen four-family gate is not release evidence for the new code.

A separate Opus 5.5 thread reviewed the implementation and two correction
checkpoints. Findings and raw review text are saved with the verification
artifacts. The final review found no implementation blockers; its remaining
combined-phase wording recommendation was then added and regression-tested.
Code is committed locally, with no push. Predeployment retrieval budgeting
(**nba-scores-8ic**) and historical boxscore fallback retry/presentation
(**nba-scores-cnm**) remain open alongside the expanded-scope release gates.


## 2026-09-29 design interview (read first)

A design interview after this handoff was written reset several decisions. They
are recorded in `docs/adr/` (index: `docs/adr/README.md`) and `docs/ask-glossary.md`,
and they take precedence over the earlier text below where the two conflict:

- The production model choice is no longer open. The cascade is Laya, then Jev,
  then GPT Luna. Laya runs in development and evaluation only until promoted
  (ADRs 0002, 0007, 0008).
- Ask never hides its answers. Spoiler rules still apply to suggestions,
  clarification options, and pages outside Ask (ADR 0006).
- New tool families: player season stats, season leaders, records, and team
  records. stats.nba is primary, Basketball-Reference is the fallback, and
  Wikipedia is not used (ADRs 0003–0005).
- Gates are per-tier precision and coverage, plus a system gate (ADR 0009).
- Next step is stage 1 of ADR 0010: the tool registry and router over the
  existing four intents, with Jev wired into the production adapter factory.

## Stage 1 backend (branch `ask-stage1-cascade`)

This branch implements the backend half of ADR 0010 step 1. It made no provider
calls and ran no live evaluation. Production enablement is still off
(`ASK_ENABLED`, `VITE_ASK_ENABLED`).

- **Tool registry and router.** `server/ask/tools.py` registers the four intents
  as `AskTool`s, each with a request model, the fields it reads, and a router
  description. The router options (`closed_sets.INTENTS`), the normalizer's
  `RELEVANT_FIELDS` and builders, and the resolver `EXECUTORS` all key off the
  registry. `test_tools.py` checks that every layer covers every tool. The
  descriptions and their order are unchanged, so the OpenAI instructions hash,
  the Jev questions, and the parse-cache keys are identical.
- **One cascade factory.** `server/ask/interpreters/factory.py` builds the
  cascade (`build_cascade`) and its policy (`build_policy`) for both the live
  pipeline and `scripts/ask/release.py`. `config.FROZEN_CASCADE` holds the
  frozen settings: Jev `jev-1.13.0` at accept 0.85, then `gpt-6-luna` at low
  effort, veto 0.5, a 20 s deadline, and no Laya. The `AskConfig` defaults equal
  it. The existing `ASK_*` variables can still override it, but the factory
  logs a warning naming each setting that differs.
  - A missing `TYPESAFE_API_KEY` builds a Luna-only cascade, with a warning.
  - A Jev call that fails is skipped by `TieredAdapter`, as in evaluation.
  - Laya is built only when `ASK_DEV=1` *and* `LAYA_BASE_URL` is set (ADR 0007).
- **Per-field diagnostics.** `InterpreterMetadata.field_decisions` records, for
  each field:
  - the deciding tier
  - its confidence
  - the outcome (`accepted`, `escalated`, `vetoed`, or `undecided`)
  - every tier's read, with its action

  The pipeline logs them on each interpretation at INFO (`ask cascade ...`).
  The log line has enumerated metadata only: no question text, candidate
  values, or keys. Responses carry `field_tiers` and `field_decisions` only
  when the server runs with `ASK_DEV=1`. Production sends `field_tiers: {}`
  and omits `field_decisions`. The dev preview backend now needs `ASK_DEV=1`
  to show the "Decided by" row.
- **Frontend follow-up.** `src/services/ask/types.ts` and `AskResponseDetails`
  do not show `field_decisions` yet. This branch stayed out of `src/`.
- **Release runner.** `release.py` still pins `FROZEN_COMMIT` `6cdae70`, so it
  can't run from this branch until a new frozen commit is designated.

GitHub issues were updated to match: #189 (parent), #199 (cascade), #200
(lookup), #201 (tool registry and router), #202 (glossary only), #204 (leaders),
#205 (UI), and new #207 (player season stats and team records), #208 (game-log
index and records), and #209 (Laya). Pre-edit bodies were saved at
`/tmp/ask-issues-before.md`.

The user authorized **$1** of live evaluation spend for this round (Jev and Luna).
Every run uses the spend guard and reports its estimated cost.


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
2,402 ms median. Neither passed. The live pipeline now builds the Jev, then
Luna cascade through the shared factory (see "Stage 1 backend" above). Do not launch more provider calls until checking the
remaining original $3 evaluation authorization and existing reports. Provider
keys remain in the original workspace's server/.env; never print them.

The interpreter has no separate field for target team versus matchup teams.
Two-team stat questions conservatively require an edit instead of returning
both teams or guessing a target. A typed schema extension is needed for full
support. Physical mobile keyboard and screen-reader checks also remain.

Beads issue `nba-scores-kzc` remains in progress. Follow-ups `nba-scores-kzc.1`
and `nba-scores-kzc.2` track target-team representation and the failed release
gates. Issue metadata changes are in the original workspace's `.beads` directory.
