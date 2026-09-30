# Ask release plan

Date: 2026-09-30. Branch `ask/reviewed-components` at `e415c970`. Production is
off. Current state is in `docs/ask-handoff.md` ("Current state, September 30").

Do the steps in order. A failed step stops the release. Nothing here changes
production flags until step 9.

## Pass criteria

From ADR 0009, quoted exactly:

> All gates are measured on a frozen, unseen evaluation set.
>
> **Tier gate** (Laya and Jev, each measured independently):
> - Accepted-field precision of at least 98%: the fields the tier accepts at its
>   calibrated threshold.
> - Coverage of at least 30% of fields. A tier that accepts less than that adds cost
>   and latency for too little benefit.
>
> **System gate** (the full production cascade, including GPT Luna):
> - At least 90% of requests fully correct.
> - At least 90% of clarification and unsupported cases correct.
> - Zero guesses: no request may render a wrong answer.
> - p95 latency of 4 s or less.
>
> A tier that fails its gate is disabled and skipped; the system gate is then
> re-measured without it.

ADR 0009 also says: the unseen set covers all eight tool families, and a
borderline pass is provisional until a larger rerun.

The answer-accuracy check (step 5) is an added criterion: every accepted answer
must match its source. Any wrong value counts as a guess.

## Checklist

1. **Finish the pending engineering.**
   - Run the 8ic slow-host measurement on the production host and save it in
     `docs/verification` (commands in `docs/ask-stage2.md`). Tune the deadline
     settings if needed.
   - Fix the stale deadline notes in `docs/ask-stage2.md` and `docs/ask-stage3.md`.
   - Decide ADR 0015 (disabling a tool). If accepted, build it before step 4, so
     the frozen commit contains the switch.
2. **Calibrate on exposed data only.** Use the development sets
   (`server/tests/ask/fixtures/eval/`, including `stage2-dev.json` and
   `stage3-dev.json`) and the two exposed release sets. Recompute Jev's
   threshold (and Laya's, if it has an endpoint) for 98% precision with the most
   coverage. Offline calibration from saved traces costs nothing; a live rerun
   is needed only for the new stage 2 and 3 cases. Never calibrate on the unseen
   set.
3. **Finish the release tooling.** In progress, by other agents, not committed:
   - `scripts/ask/release.py` generalized to the eight-tool scope. The committed
     file still pins `6cdae70` and requires exactly 100 cases.
   - `scripts/ask/answer_check.py`, the answer-accuracy check.
   - A draft third unseen set.
   Review all three before use. The set's author must not see earlier questions,
   failures or prompts, as for the first two sets.
4. **Freeze.** Pick the release commit. Record it, the cascade settings
   (`FROZEN_CASCADE`), thresholds and input hashes in the manifest. Any later
   code change needs a new freeze.
5. **Run the frozen unseen set once.** Score the tier gate and the system gate.
   Then run the answer-accuracy check on every accepted answer. Save the report,
   journal and labels in `docs/verification`.
6. **If it fails, fix, then use a second fresh set.** The first unseen set is
   now exposed. It becomes development data. Fixes are calibrated on exposed data
   only. Freeze again, and run a new unseen set that nobody has seen. Do not
   rerun the exposed set and call it release evidence. If one family keeps
   failing, disabling it (ADR 0015, if accepted) is an option; re-score the
   gate as that ADR says.
7. **Browser retest** (below), on the frozen commit.
8. **Quality gates before the PR.** `pnpm test:run` (with
   `NODE_OPTIONS=--no-experimental-webstorage`, see the handoff), `pnpm lint`,
   `pnpm build`, and the backend suite
   (`server/venv/bin/python -m pytest -q server/tests`). Then open the PR and
   trigger the CodeRabbit review.
9. **Rollout** (below).

## Budget

All figures are list-price estimates from reported token usage, not billing.

Recorded so far:

| Item | Estimate | Source |
| --- | --- | --- |
| Earlier rounds (user's estimate) | $0.20 | `ask-unseen-two-2026-09-29-manifest.json` |
| First unseen run, 100 questions | $0.032570 (conservative) | `ask-unseen-2026-09-29.json` |
| Second unseen run, 100 questions | $0.030985 | `ask-unseen-two-2026-09-29.json` |
| **Total recorded** | **about $0.264** | |
| Paired Jev/Luna exposed run, 80 questions | $0.017794 | `ask-jev-luna-regression-2026-09-29.json`; not stated whether the $0.20 includes it |

An unseen run costs about $0.0003 per question. The paired calibration run cost
about $0.00022 per question.

Estimates for this release:

| Phase | Size | Estimate |
| --- | --- | --- |
| Calibration: offline from saved traces | - | $0 |
| Calibration: live rerun of new exposed cases | about 250 questions | about $0.06 |
| Evaluation: frozen unseen set | 100-200 questions | $0.03-0.07 |
| Evaluation: second fresh set, if needed | 100-200 questions | $0.03-0.07 |
| Answer-accuracy check | - | TODO: depends on `answer_check.py` |
| **Estimated total** | | **about $0.12-0.20** |

The committed `release.py` limits one run to $0.10.

- Actual billed cost so far: **TODO (user).**
- Remaining authorization: **TODO (user).** The docs mention an original $3
  evaluation authorization and $1 for the stage 1 round.

## Browser retest

Before testing, confirm the preview runs the frozen commit:

- `git -C /private/tmp/ask-reviewed-components log -1 --oneline` shows the
  frozen commit, with no uncommitted changes under `src/` or `server/`.
- The Vite server on port 5289 is serving from that worktree (on September 30 it
  was, not from `/private/tmp/ask-resume-ui`). Restart it and the 8019 backend if
  in doubt.

Open `http://127.0.0.1:5289/design-1?ask=live`. Ask these four questions:

| # | Question | Expected |
| --- | --- | --- |
| 1 | Kevin Durant stats 2015-16 | No clarification. Season line shows per game first (28.2 points). **Per game** is pressed. Select **Totals**: 2029 points. |
| 2 | Kevin Durant total points in 2015-16 | Totals first (2029). **Totals** is pressed. The toggle is still there; **Per game** shows 28.2. |
| 3 | LeBron's career points | Career line for LeBron James, not "Which kind of question?". Totals first, with the Per game \| Totals toggle and "Data as of". |
| 4 | Who led the league in assists in 2019-20? | A measure clarification with two choices, **Season totals** and **Per game**. Pick **Per game**: a top-10 leaderboard, leader emphasized, no toggle. |

The expected Durant values come from the source row in
`server/tests/ask/test_live_feedback_measures.py`.

For questions 1-3, also check:

- **Keyboard.** Tab reaches both toggle buttons. Enter and Space switch the
  measure. Focus does not jump or get lost when the values change.
- **Visible focus.** A clear focus ring shows on the focused button, in light
  and dark themes.
- **Screen reader** (VoiceOver). The group is read with its label, for example
  "Show Kevin Durant 2015-16 statistics per game or as totals". Each button is
  read as a toggle button, and the selected one as pressed/selected. After
  switching, the new state is announced. The toggle has no live region, so
  also check that the new values are read when you move to the table.
- Repeat question 1 at a mobile width and on a physical phone keyboard.

## Rollout

What exists in code today:

- **Off switch for all of Ask:** `ASK_ENABLED` (server). It is read once at
  startup, so turning it off needs a restart or redeploy. When off, every
  question returns "NBA data isn't responding", which is misleading.
- **UI entry:** `VITE_ASK_ENABLED=1` shows the Design 1 entry. It is set at build
  time, so changing it needs a frontend rebuild.
- **Tier switch:** removing `TYPESAFE_API_KEY` skips Jev, and Luna runs alone.
  `LAYA_BASE_URL` is unset in production.
- **Limits:** a daily spend budget (`ASK_DAILY_BUDGET_USD`, default $1),
  per-client and per-worker rate limits, and at most two requests in flight.
- **Logs:** one `ask cascade` INFO line per interpretation (no question text),
  and `logger.error` on request failures.

What is missing:

- A small rollout. There is no percentage or allowlist gate; the flags are all
  or nothing. A small rollout today means a limited deploy (for example a
  preview deploy shared with a few people).
- Error monitoring. No metrics, alerts or error tracker. Someone must read the
  logs. At minimum, count outcomes, `service_unavailable`, budget stops and p95
  latency per day.
- A quick off switch. Both flags need a restart or rebuild. A per-tool switch
  (ADR 0015) and a clear "Ask is turned off" message are not built.

Rollout steps:

1. Deploy with `ASK_ENABLED=1` to a limited audience first.
2. Watch the logs daily for errors, unavailable answers, budget use and latency.
3. If anything renders a wrong answer, turn Ask off (or the one tool, if ADR 0015
   is built), then add the case to the development set.
4. Widen only after a clean period with no guesses.
