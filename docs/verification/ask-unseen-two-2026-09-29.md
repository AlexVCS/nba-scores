# Second independent Ask evaluation, September 29, 2026

The frozen four-family interpretation system gate passes: 92 of 100 questions
are correct, with no wrong accepted requests. Production remains disabled.
The separate tier precision and coverage gate is still incomplete, and this run
does not establish retrieval, UI, spoiler safety, accessibility, or the broader
eight-family release scope in ADR 0009.

| Gate | Result | Outcome |
| --- | --- | --- |
| At least 90% complete-request accuracy | 92/100 | Pass |
| At least 90% clarification accuracy | 24/25, 96% | Pass |
| At least 90% unsupported accuracy | 10/10 | Pass |
| Zero wrong accepted requests | 0 | Pass |
| p95 interpretation latency at most 4 seconds | 3.508 seconds | Pass |
| All questions scored in one run | 100/100 | Pass |

The median was 234 ms. Jev ran on every question; 43 also called Luna.
Each question entered the cascade once, with no candidate expansion or second
cascade attempt. Seven supported questions received unnecessary clarifications;
one clarification asked about the wrong field. The scorer checks clarification
action and field, not the reason text. Thresholds and scoring are unchanged from
the previous frozen run.

## Frozen inputs and independence

Production code is frozen at `6cdae70d2589e14c65f899555f8311b513c1c213` on
`ask/reviewed-components`. Jev is `jev-1.13.0`, with accept minimum 0.85.
Luna is `gpt-6-luna`, reasoning effort `low`. Veto minimum is 0.5, the deadline
is 20 seconds, and Laya and whole-request fallback are disabled.

A new author agent inherited no conversation. It read only request/model
schemas, the fixture serialization contract, player and franchise reference data,
and a neutral city-tenure export. It did not read old questions, failures,
prompts, lookup logic, or interpreter implementations. The
[authorship note](ask-unseen-two-2026-09-29-author.md) records that isolation and
the pre-live revisions. The parent supplied coverage requirements but no old
question text or provider outputs.

The set contains 25 questions per request family, with 65 accept labels,
25 clarification labels, and 10 unsupported labels. Coverage tags overlap.

| Coverage | Correct / total |
| --- | --- |
| Game search | 24/25 |
| Boxscore statistics | 20/25 |
| Playoff series | 24/25 |
| Postseason summaries | 24/25 |
| Contemporaneous player ambiguity | 12/12 |
| Historical franchises | 24/24 |
| Nicknames | 21/24 |
| Explicit former-home clauses | 2/2 |
| Page context | 7/9 |

Before any provider call, the parent reviewed all labels and compared questions
against 450 distinct prior question/utterance strings. The author replaced one
near-duplicate and three questions with multiple defensible clarification fields,
added two explicit former-home clauses, and removed redundant context timestamps.
The final set has no exact normalized duplicates and no lexical similarity of
0.9 or higher against prior questions or within itself. Lexical screening alone
does not establish semantic novelty. See the reproducible
[preflight audit](ask-unseen-two-2026-09-29-preflight.json) and
[audit script](ask-unseen-two-2026-09-29-preflight.py).

The [fixture](../../server/tests/ask/fixtures/eval/unseen-two-2026-09-29.json)
SHA-256 is `fa3e001b816baf38967fd88c837b6228f2336af811749f06499cd4b59c1cf040`.
The [manifest](ask-unseen-two-2026-09-29-manifest.json) froze the fixture,
production files, runner, configuration, gates, and pre-live evidence.
All hashes still matched after the run. No labels or production files changed
after execution began, and there were no reruns or post-run score adjustments.

## Eight misses

IDs below omit the common `unseen-two-` prefix.

| Case | Observed result |
| --- | --- |
| `game_search-15` | Asked for a date despite the selected scores-page date. Jev reported no matching date; Luna reported absent. |
| `boxscore_stat-01` | Neither tier resolved Magic for the explicit 1987 player-stat question. |
| `boxscore_stat-02` | Luna timed out; the cascade asked for teams despite the fully specified Dream/1994 Finals Game 7 request. |
| `boxscore_stat-03` | No game-number candidate for "sixth game" in Shaq's 2000 Finals question. |
| `boxscore_stat-08` | Asked for a season despite Jokic's explicit date overriding the open game. Jev reported no matching season; Luna reported absent. |
| `boxscore_stat-11` | No game-number candidate for "sixth game" in Tim Duncan's 2003 Finals question. |
| `playoff_series-14` | No round candidate for "first playoff round" in the Lakers' 2020 question. |
| `postseason_summary-22` | Asked about intent when the user had left Boston versus Miami unresolved. |

These are safe refusals or clarification errors, not accepted interpretation
errors. The timeout took 20.010 seconds. It remains in the latency distribution
and the accuracy score; it was not retried. Two Jev `inconsistent_team_count`
outputs were recovered by Luna. No final request returned a service failure.
The [post-run audit](ask-unseen-two-2026-09-29-audit.json) preserves coverage,
failure IDs, and provider errors without altering the strict report.

## Spend and artifacts

The run stayed within its $0.10 cap. Known reported usage totals $0.025571.
Keeping the timeout's unknown-usage reservation gives $0.030985 conservatively
accounted. Added to the previous estimate of $0.232570, the accounted estimate
is $0.263555. Actual billing is unknown. The raw summary leaves aggregate token
cost null because one call has unknown usage; the spend guard retains its
reservation separately.

The frozen price table was checked against the official
[TypeSafe model page](https://docs.typesafe.ai/models) and
[OpenAI Luna page](https://developers.openai.com/api/docs/models/gpt-6-luna)
on September 29, 2026. Prices and model configuration were not changed.

The [strict report](ask-unseen-two-2026-09-29.json),
[original journal](ask-unseen-two-2026-09-29.jsonl), and
[executed runner snapshot](ask-unseen-two-2026-09-29-runner.py) preserve the run.
The runner rejects existing report/journal paths and changed frozen inputs.
Do not delete those files to obtain a second score. This set is now exposed;
future corrections require a new unseen set for release evidence.

## Local handoff

The 1,147 backend tests, release-runner regression, lint, and production build
pass. No production code, prompts, thresholds, or enablement flags changed in
this evaluation session.

`nba-scores-huv` and `nba-scores-2ly` are closed after fresh ambiguity and
historical-franchise validation. `nba-scores-dfc` remains open for the page-context
misses. `nba-scores-kzc.2` records the remaining interpretation misses and manual
checks. New issue `nba-scores-kzc.3` tracks the incomplete accepted-field precision
and coverage gate. Evaluation task `nba-scores-g6l` is complete.

Artifacts and runner updates are local on `ask/reviewed-components`; nothing was
pushed. Existing changes in the user's original workspace were preserved.
