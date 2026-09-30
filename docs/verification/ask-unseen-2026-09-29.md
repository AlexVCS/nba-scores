# Independent Ask release evaluation, September 29, 2026

The frozen Jev 0.85 → GPT-6 Luna setup fails the system gate. It accepted two
unsafe interpretations. Correcting one independently confirmed label error gives
90/100 correct; the unchanged strict report scores 89/100.

| Gate | Frozen raw result | Post-run semantic audit | Outcome |
| --- | --- | --- | --- |
| At least 90% requests fully correct | 89/100 | 90/100 | Raw fail; audited threshold met |
| At least 90% clarifications correct | 13/15, 86.7% | unchanged | Fail |
| At least 90% unsupported cases correct | 10/10 | unchanged | Pass |
| Zero unsafe accepted requests | 3 flagged | 2 confirmed, 1 label error | Fail |
| p95 at most 4 seconds | 3.728 seconds | unchanged | Pass |

Median interpretation latency was 2.102 seconds. Jev ran on all 100 questions;
Luna ran on 51. Jev finished 49 without Luna. Each question entered the cascade
once; no candidate expansion or second cascade attempt occurred.

## Frozen inputs and independence

Production code was frozen at `9291237869342615c2f3e7005d9d4ccaa61ca116`.
Jev was `jev-1.13.0`, accept minimum 0.85. Luna was `gpt-6-luna`, reasoning
effort `low`. Veto minimum was 0.5 and the production deadline was 20 seconds.
Laya was absent. The runner uses `build_cascade`, the production normalizer and
policy, and the real `CandidateLookupService`. It does not use the older CLI's
whole-request fallback configuration.

A separate agent with no inherited conversation authored 100 questions and labels.
It could read only schemas and entity/city data. It could not read old questions,
results, prompts, lookup logic, or interpreter implementation. Each of the four
Phase 1 request families has 25 associated cases. There are 75 accepted-request
labels, 15 clarification labels, and 10 unsupported labels. The
[author's note](ask-unseen-2026-09-29-author.md) records permitted sources and
pre-live revisions.

The parent checked overlap against 470 previously stored questions. The final
fixture has no exact normalized match and none at lexical similarity 0.9 or
higher. This check alone does not establish semantic novelty; the isolated author
provides stronger evidence. Pre-live review replaced one near-duplicate and
two questions with nonunique clarification fields, aligned five team selectors
with the serialization convention, and disambiguated two relative-season times.
No provider outputs existed during those edits.

The final fixture SHA-256 is
`fd774408c30889239ff297baaabf2b971b73e5210bfa5b842fdfe478a1d37332`.
The [manifest](ask-unseen-2026-09-29-manifest.json) locked configuration, gates,
fixture and implementation hashes before the live run. The
[preflight audit](ask-unseen-2026-09-29-preflight.json) records the overlap check.

## Confirmed unsafe interpretations

- Case 082, "How many points did Curry score on January 15, 2025?" Jev chose
  Stephen Curry with confidence 1.0, despite multiple catalog matches including
  Seth Curry. Luna returned ambiguity, but the merge kept Jev's player selection.
  This exposes a missing veto for a later ambiguous read.
- Case 049, "I want the Nets schedule for January 2, 2002, when they were in
  New Jersey." The historical city phrase describes the franchise. Jev also
  selected a home-city filter, restricting the answer to home games the user
  did not request. That is a wrong normalized request regardless of whether a
  particular day's matching games happen to coincide.

These are accepted interpretation errors. The evaluation did not retrieve or
render their basketball answers, so it does not claim that two factual answers
were displayed to a user.

Case 009 was a label error. `2026-02-09T02:35:00Z` is February 8 at 21:35 in New
York. Under the specified prior-calendar-day meaning, "last night" is February 7.
The frozen app correctly selected February 7; the author had labeled February 8.
The author independently confirmed the error after the run. The original fixture
and strict results remain unchanged. The separate
[semantic audit](ask-unseen-2026-09-29-audit.json) records this adjudication.

## Other misses

| Case | Problem |
| --- | --- |
| 001 | Asked for a date despite explicit "leap day in 2024" |
| 007 | Asked for a round because the "Bad Boys" alias was not resolved |
| 022 | Luna exceeded the deadline; the merged result asked for a date |
| 042 | Treated a boxscore-page question with a game ID as an unsupported follow-up |
| 064 | Ignored the selected postseason season |
| 067 | Asked for teams despite West conference finals and selected season |
| 073 | Ignored the selected scores-page date |
| 090 | Treated missing game/date for Michael Jordan assists as career statistics |

The raw scorer reports zero final service failures, but the tier trace records
one Luna `deadline_exceeded`. Its final outcome was an unnecessary clarification.
Jev also returned `inconsistent_team_count` on case 083; Luna recovered and asked
the correctly missing team. Neither event was rerun.

## Spend and report recovery

The hard cap was $0.10. Known reported usage totals $0.027154. One timed-out
request has unknown usage, so the guard kept its full reservation and ended at
$0.032570 conservatively accounted. Actual billing is unknown. Combined with the
user's prior estimate of $0.20, the accounted total is about $0.233 of $1.

The recorded list prices were checked against the official
[TypeSafe model page](https://docs.typesafe.ai/models) and
[OpenAI Luna page](https://developers.openai.com/api/docs/models/gpt-6-luna).

All 100 records were saved to the [original journal](ask-unseen-2026-09-29.jsonl).
After saving them, the runner failed to assemble its summary because it applied
`relative_to` to a relative manifest path. The [raw report](ask-unseen-2026-09-29.json)
was recovered from that journal with the same frozen scorer, offline. There were
no additional model calls, changed labels, missing cases, or altered outputs.
The [exact executed runner](ask-unseen-2026-09-29-runner.py) retains the manifest's
original script hash. The reusable runner now resolves the manifest path first;
a regression test covers relative paths, report creation, and repeat rejection.

## Handoff

No production Ask files, prompts, thresholds, or championships tool changed.
Production remains disabled. These questions are now exposed evaluation material;
future corrections need a different unseen set.

Follow-up issues are `nba-scores-huv` for the missing ambiguity veto,
`nba-scores-2ly` for the historical city wording, and `nba-scores-dfc` for the
remaining context and clarification misses. Evaluation task `nba-scores-yo4`
is closed; the Ask feature remains in progress.

This is an interpretation system gate for the four Phase 1 request types. It does
not establish data retrieval, UI correctness, spoiler safety, or the tier precision
gate. The existing tier field oracle remains incomplete, so no tier precision pass
is claimed.

The frozen backend's 1,123 tests, lint, and production build passed. The subsequent
runner regression test also passed. Evaluation artifacts and tooling are local.

The saved journal, manifest and report paths deliberately reject a repeated run.
Keep them; do not rerun this set to obtain a better score.
