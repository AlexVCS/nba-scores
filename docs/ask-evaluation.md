# Ask: interpreter evaluation (#199)

This document covers the interpreter adapters, the evaluator, and the measured
development results. The pipeline should use one GPT-6 Luna adapter. Keep it
disabled until the separate unseen release evaluation passes the gates below.
The comparison used #200's lookup candidates, including its expansion path.

Contract: [`docs/ask-contract.md`](ask-contract.md). Earlier prototype results are
summarized under [History](#history-prototype-parser).

## Components

| Piece | File | Contract role |
| --- | --- | --- |
| Jev adapter (`jev-1.13.0`, pinned) | `server/ask/interpreters/jev.py` | `InterpreterAdapter` (`name="jev"`) |
| OpenAI Responses adapter (gpt-4.1-mini, Luna) | `server/ask/interpreters/openai_responses.py` | `InterpreterAdapter` (`name="openai_responses"`) |
| Closed-set options (intents, stats, scopes, reasons) | `server/ask/interpreters/closed_sets.py` | Built from the contract enums |
| Fallback policy | `server/ask/interpreters/cascade.py` | `CascadePolicy` |
| Normalizer | `server/ask/normalize.py` | `RequestNormalizer` |
| List prices and spend guard | `server/ask/interpreters/pricing.py` | |
| Harness (driver, scoring, report) | `server/ask/eval/runner.py` | |
| CLI (`probe`, `run`) | `scripts/ask/evaluate.py` | |
| Hand-built smoke cases | `server/tests/ask/fixtures/eval/smoke_hand_built.json` | Plumbing only |

Both adapters call the provider HTTP APIs directly with `httpx`, which is now an
explicit dependency. They don't use a provider SDK. Tests inject
`httpx.MockTransport` and make no network calls. Adapters never raise for provider
failures. They return `outcome="unavailable"` with a short `error_code` such as
`timeout`, `rate_limited`, `auth_failed`, or `budget_exceeded`. Raw provider text
never goes in the output.

## Jev: what the API actually is

TypeSafe's Jev is a "System One" model. It takes a `state` and a map of typed
questions, and it returns typed answers. It does not generate text.

- **Endpoint:** `POST https://api.typesafe.ai/v1/systemone` with
  `Authorization: Bearer $TYPESAFE_API_KEY`. The body is
  `{"model", "state", "questions": {id: question}}`. The response is
  `{"model", "answers": {id: answer}, "usage": {"input_tokens", "output_tokens"}}`.
  `GET /v1/models` lists only the aliases (`jev-latest`, `jev-preview`), but
  versioned IDs are accepted.
- **Question types:**
  - `choice`: `criteria` maps each option to a description, with at most 255
    options. The answer has `choice`, a `probabilities` value for every option,
    and `confidence`.
  - `score`: 2–10 ordered levels. The answer has a probability-weighted `score`,
    `probabilities`, and `confidence`.
  - `noul`: a yes/no question. The answer is a single probability `noul`, with no
    confidence.
- `instructions` and `criteria` can be strings or structured objects. The
  documented `confidence` is `(n·p_max − 1)/(n − 1)`, so it depends on the
  number of options.
- **Pricing and limits:** $0.042 per million input tokens; output tokens are free.
  The limit is 64k tokens per request (32k for state plus the longest question).
  Documented rate limits are 1,200 requests per minute and 250k tokens per second,
  and they are "adjusting dynamically".
- **SDK:** `pip install typesafe-sdk` (0.7.2, which depends on `httpx2`) provides
  `TypeSafeClient.system_one(state, questions, model=...)` with retries. The adapter
  uses plain HTTP instead, so it adds no dependency.
- **Documented limits** ([jaggedness](https://docs.typesafe.ai/model-jaggedness/jev-1.13)):
  Jev reads instructions literally. It is unreliable at counting, arithmetic, and
  comparing dates, and it loses accuracy as unrelated state grows. It is not a
  generator. Extraction must be a Choice over options that code has already found.

### How the adapter asks

One request per question, sending the state `{"question": ...}` (the "fan-out"
pattern):

- **Contract enums** (Choices): `intent` (four intents plus `unsupported`),
  `unsupported_reason`, `stat_scope`, `stat`, and `aggregation`.
- **Candidate fields** (Choices over the lookup's candidate IDs): `player`,
  `date`, `season`, `round`, and `game_number`. Each also offers `__none__` (not
  mentioned → `absent`) and `__other__` (mentioned but not listed →
  `no_matching_candidate`).
- **Teams:** one Noul per team candidate, one Noul for "a team not in the list",
  and a `team_count` Choice as a consistency check. If the count disagrees with
  the Nouls, the field is `ambiguous`.
- **Dates:** Jev never extracts date parts or years. It chooses among #200's date
  candidates. The date cookbook's default-year behavior is not used.

**Confidence:** for a Choice field, confidence is the probability of the chosen
option. For teams, it is the least decisive team Noul, `min(max(p, 1 − p))`. The
adapter only chooses between `ambiguous` and `selected`, based on two or more
candidates reaching `ambiguity_floor` while the top option stays below
`ambiguity_top_max`. The cascade policy decides whether a confidence is high
enough to act on.

The adapter rejects `jev-latest` and `jev-preview`, and it logs the response's
`model` field (`resolved_model`).

## OpenAI Responses adapter

One class serves every OpenAI model; the model is a configuration setting. It uses
strict structured outputs (`text.format.type = "json_schema"`, `strict: true`) and
`store: false`. The schema is built for each question:

- Every candidate-backed field is `{status, values}`, where `values` is an enum of
  that field's candidate IDs.
- Closed-set fields are enums of the contract values.
- `extracted_date` (the contract's `DateComponents`) appears only when the date set
  has no candidates. When it is present, the adapter omits the `date` field, and
  Python resolves the components in America/New_York.
- Unknown IDs or impossible shapes produce `outcome="unreliable"` with
  `error_code="invalid_output"`. They are never passed through as guesses.

Responses has no per-field probabilities, so `confidence` is `None`.

| Model | Snapshot the key resolved (probe) | List price in/out per 1M tokens |
| --- | --- | --- |
| `gpt-4.1-mini-2025-04-14` | `gpt-4.1-mini-2025-04-14` | $0.40 / $1.60 |
| `gpt-6-luna` | `gpt-6-luna` | $0.10 / $0.50 (cached $0.01) |
| `gpt-5.6-luna` | `gpt-5.6-luna` | $0.20 / $1.20 (cached $0.02) |

The model pages list no dated snapshot for either Luna model; each model's only
snapshot is its alias. The response's `model` field also returned the undated
name. Because of that, "exact snapshot" currently means the undated ID plus the
evaluation date. Luna defaults to `reasoning.effort="low"`, which can be changed;
gpt-4.1-mini gets no `reasoning` parameter.

## Normalizer

`Normalizer.normalize(output, candidates, context)` returns a `NormalizationResult`.

- **Invalid:**
  - Unknown or misfiled candidate IDs
  - Non-enum closed-set values
  - Outcomes other than `interpreted`/`unsupported`
- **Clarify:**
  - A required field that is `absent` (`missing`), `ambiguous`, or `no_matching_candidate`
  - An optional field the user mentioned but that could not be pinned down, such as
    an unknown team in a game search. It is not silently dropped.
  - A date candidate without a resolved range, which uses its `unresolved_reason`
    (`year_required`, `range_too_long`)
  - A boxscore request whose date spans more than one day
- **Unsupported:** `aggregation="per_game"` on a boxscore request →
  `multi_game_average`.
- **Other rules:**
  - A player or team scope without a named stat becomes `stat_line`; leaders
    require a stat.
  - `extracted_date` is used only when the date set has no candidates. Its year is
    never defaulted. `last_week` is the previous Monday–Sunday, and
    `last_weekday` excludes today.

## Fallback policy

`ThresholdCascadePolicy(primary_model, fallback=None | (adapter, model), thresholds)`
implements the table in #199. The single-provider configuration is the same class
with no fallback, so it never returns `fallback`.

| Last attempt | Decision |
| --- | --- |
| Valid request, weakest relevant confidence ≥ `accept_min` (or no confidences) | `accept` |
| Valid request, a relevant field below `accept_min` | one `fallback`, else `clarify` that field |
| Clarification read confidently (field and intent ≥ `clarify_min`) | `clarify`; the fallback never fills the gap |
| Clarification read with low confidence | one `fallback`, else `clarify` |
| `no_matching_candidate` | `expand_candidates` once for that field, else `clarify` |
| Unsupported (adapter, or normalizer `multi_game_average`) | `unsupported` |
| `unreliable` output or `invalid` normalization | one `fallback`, else clarify-or-fail |
| Primary `unavailable` | `fallback` only if enabled and budget/time allow, else clarify-or-fail |
| Both paths unreliable | `clarify` if an attempt pinned down the unclear field, else `fail` |

"Relevant" means the fields the intent reads (`normalize.RELEVANT_FIELDS`), so a
stray low confidence on an unrelated field does not trigger fallback. The
`not_found` and `unavailable` outcomes from the data service never reach the
policy.

**All Jev and cascade thresholds are uncalibrated placeholders:** `JevThresholds` and
`PolicyThresholds` (`accept_min=0.7`, `clarify_min=0.6`, `ambiguity_floor=0.25`,
and so on). Jev and the cascade failed the complete-request gate, so do not
deploy or imply that these thresholds are calibrated. The selected OpenAI
adapter supplies no per-field confidence; its single-provider policy accepts
only after Python normalization, so these confidence thresholds do not affect
the selected path. No cookbook values are used.

## Harness

`server/ask/eval/runner.py`:

- `drive()` runs one question the way #201's pipeline will: adapter → normalizer →
  policy. It loops on `fallback` and `expand_candidates`, with at most four
  attempts.
- `run()` executes every configuration on every labeled case under one
  `SpendGuard`. Configurations that share a primary adapter reuse its first call,
  so "Jev alone" and "Jev → Luna" see the same Jev read and pay for it once.

Scoring:

- A case is correct only when the final action matches the label.
- For `accept`, the normalized `AskRequest` must equal the labeled request (team
  order ignored).
- For `clarify` with a labeled `clarify_field`, the field must match.
- An `accept` with a wrong request, or where the label expects clarification or
  unsupported, is a schema-valid guess. It counts as a failure and is also counted
  separately.

Each configuration reports:
- complete-request accuracy
- schema-valid guesses
- service failures
- clarification (expected / correct / issued / unneeded)
- unsupported (expected / correct / issued / false)
- median and p95 latency (nearest rank)
- total cost and cost per successful answer
- fallback rate
- resolved model IDs
- failure breakdown

For a cascade, the report also lists the cases the fallback **fixed** and
**worsened** compared with the primary alone.

Budget controls:

- **Hard spend cap:** `--spend-cap`, default $3 for `run` and $0.50 for `probe`.
  Each call reserves a conservative estimate first: about one token per two
  characters of the full payload, plus the full output allowance. The reservation
  is then settled with the reported usage. If a call would exceed the cap, the run
  stops, and the remaining cases are listed under `not_run`.
- **Per-request timeout:** `--timeout`, default 20 seconds.
- **Per-question deadline:** `--deadline-ms`, default 30,000.

```bash
# live access probe (keys from the main checkout's .env; values are never printed)
server/venv/bin/python scripts/ask/evaluate.py --luna-models gpt-6-luna gpt-5.6-luna \
  --env-file /path/to/main/server/.env probe --spend-cap 0.40

# full comparison, once #200 exposes a CandidateLookup factory
server/venv/bin/python scripts/ask/evaluate.py --env-file ... run \
  --cases server/tests/ask/fixtures/eval/dev.json \
  --lookup server.ask.candidates.<module>:<factory> \
  --configs jev gpt-4.1-mini luna jev+luna --spend-cap 3
```

`run` refuses embedded hand-built candidates unless `--allow-hand-built` is passed.
The report labels such runs as invalid for the #199 decision.

Labeled cases use this format: `{id, question, reference_time, context?, tags,
expected: {action, request?, clarify_field?, unsupported_reason?, also_accept?},
candidates?}`. `request` is a contract `AskRequest`.

## Live access probe (2026-09-29)

[`verification/ask-interpreter-probe.json`](verification/ask-interpreter-probe.json)
contains the sanitized outputs, normalizations, decisions, resolved models, usage,
and latency. It contains no keys, prompts, or raw provider text.

Setup: three hand-built smoke questions for each model: "Cavs games last week",
"How many points did Tatum score in game 4 of the 2024 Finals?", and "Lakers vs
Celtics on January 23".

- All 12 calls returned the expected action and request. Each model accepted the
  first two questions and asked a `year_required` date clarification for the third.
- Every model resolved to the ID that was requested.
- The key can call `jev-1.13.0`, `gpt-4.1-mini-2025-04-14`, `gpt-6-luna`, and
  `gpt-5.6-luna`.
- Total estimated spend was $0.0056, plus one earlier single Jev shape check of
  about $0.0001.

| Model | Latency per call | Cost per call |
| --- | --- | --- |
| Jev | 150–420 ms | ~$0.00009 (about 2.2k input tokens) |
| gpt-4.1-mini | 2.7–3.6 s | ~$0.0009–0.0010 |
| gpt-6-luna (effort low) | 2.2–4.0 s | ~$0.00025–0.0003 |
| gpt-5.6-luna (effort low) | 2.1–2.9 s | ~$0.0005–0.0006 |

These results show access and response shapes. They are not an accuracy result:
three hand-built cases cannot separate the models.

Observations for calibration:

- Jev answers every speculative question. Irrelevant closed-set answers, such as
  `stat_scope` on a game search, are noise that the normalizer ignores.
- On the Tatum question, Jev's `absent` confidence for optional boxscore fields
  (`date` 0.71, `teams` 0.73) was close to the placeholder `accept_min=0.7`.
  Calibration should decide whether low-confidence *absent* optional fields should
  block acceptance, or only selected fields plus required absences.

## Decision gates for development evaluation

The development set is exposed to implementation and calibration. These gates
screen configurations; passing them does not authorize production. A separate
unseen release set must pass the same gates before enabling the endpoint:

| Measure | Gate |
| --- | --- |
| Complete request accuracy, among `accept` labels | at least 90% |
| Schema-valid guesses | zero |
| Correct clarification field | at least 90% of clarification labels |
| Correct unsupported reason | at least 90% of unsupported labels |
| Service failures | zero, unless a documented provider outage invalidates the run |
| Median interpreter latency | at most 3 seconds |
| p95 interpreter latency | at most 10 seconds |
| Estimated cost per correct answer | at most $0.005 |

Any configuration that fails a gate remains disabled. The development report
records the labels, resolved models, provider errors, and each wrong case so
that a later run can check whether a proposed fix helped or only moved errors.

The candidate lookup's 75 self-authored development questions informed this
set but are not an unseen test. The two old prototype fixtures are also exposed.

### First live development pass

The first pass used 36 labels and lookup commit `89fd59b`, before the candidate
edge-case fixes and before the prompt clarified unknown entities and long date
ranges. The full case report is
[`ask-interpreter-eval-initial.json`](verification/ask-interpreter-eval-initial.json).
It spent an estimated $0.049015 at list prices, with no candidate errors or
budget stop.

| Configuration | Correct | Guesses | Median | p95 |
| --- | ---: | ---: | ---: | ---: |
| Jev | 22/36 | 0 | 195 ms | 254 ms |
| gpt-4.1-mini | 31/36 | 0 | 1,625 ms | 2,764 ms |
| GPT-6 Luna | 32/36 | 0 | 2,456 ms | 13,768 ms |
| Jev → GPT-6 Luna | 30/36 | 0 | 215 ms | 3,185 ms |

The same four configurations called both unknown-name questions (`dev-038`,
`dev-073`) unsupported even though their labels require an entity
clarification. These labels have not changed. The contract says an unknown
candidate in an otherwise supported single-game or game-search request must
produce `no_matching_candidate`; the model must not turn an entity lookup
failure into a different intent. Both OpenAI models also called the 28-day
`dev-014` game search unsupported, where the contract requires a
`range_too_long` clarification. GPT-6 Luna timed out once at 20 seconds.

### Expanded development pass before independent review fixes

The second pass used 42 labels, lookup commit `5742a1c`, and the revised prompt.
It included both Luna versions. The full case report is
[`ask-interpreter-eval-prereview.json`](verification/ask-interpreter-eval-prereview.json). The
estimated spend was $0.089040, with no candidate errors or budget stop. No
original label changed after the first pass. Six new cases cover invalid day
numbers, historical team names, an unsupported leader percentage, and a page
season reference.

| Configuration | Correct | Clarifications correct | Unsupported correct | Guesses | Median | p95 | Cost per correct |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Jev | 29/42 | 10/12 | 4/5 | 0 | 219 ms | 318 ms | $0.000141 |
| gpt-4.1-mini | 35/42 | 7/12 | 4/5 | 0 | 1,681 ms | 2,687 ms | $0.001208 |
| GPT-6 Luna | 39/42 | 9/12 | 5/5 | 0 | 2,574 ms | 5,668 ms | $0.000301 |
| GPT-5.6 Luna | 38/42 | 9/12 | 5/5 | 0 | 2,178 ms | 4,576 ms | $0.000649 |
| Jev → GPT-6 Luna | 35/42 | 10/12 | 5/5 | 0 | 229 ms | 3,646 ms | $0.000145 |

GPT-6 Luna met the overall 90% accuracy gate but missed the clarification
gate. It called `dev-073` (an unknown team in a game-like question)
unsupported, and invalid dates `dev-invalid-day-32` and `dev-invalid-day-0`
ended as `invalid_output` failures. The adapter must turn an invalid extracted
date into a date clarification without accepting the invalid value. The
separate review also found Jev team-count and cached-primary deadline bugs,
so the cascade numbers here are diagnostic only. All configurations remain
disabled until fixes and an unseen release evaluation pass the gates.
The subsequent `cf3737b` lookup fix inferred the end year in a range crossing
New Year. `dev-cross-year-range` is a 43rd label added after this run; its
lookup candidate resolves to December 30, 2025 through January 2, 2026. The
next run must include it.

### Failed transport rerun

A 43-case rerun after the interpreter review fixes produced `connection_error`
for every provider request. Its [raw report](verification/ask-interpreter-eval-transport-failure.json)
is retained, but its accuracy numbers say nothing about model quality. The
spend guard charged $1.428937 in conservative reservations because the adapter
could not read usage from those responses. Actual billing for those requests
is unknown. A local reproduction points to response decoding in the HTTP
helper. No architecture decision uses this run; a fixed transport needs a
bounded rerun within the remaining authorized budget.

### Corrected 43-case development run and choice

The HTTP decoder fix passed its offline regression test. One live GPT-6 Luna
preflight then returned a complete request and recorded usage for $0.000100.
The full [43-case report](verification/ask-interpreter-eval.json) used lookup
commit `cf3737b` and the reviewed interpreter fixes. It spent an estimated
$0.010432 of its $1.30 guard, with no candidate errors or budget stop. The
failed transport run above remains a separate unknown billing exposure; its
reservations still count against the overall $3 authorization.

The report's `complete_request_accuracy` key is overall case correctness.
For the gate, we recomputed complete-request accuracy on the 26 cases labeled
`accept`. Clarification and unsupported denominators are 12 and 5.

| Configuration | Complete | Clarify | Unsupported | Guesses | Failures | Median | p95 | Cost per correct |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Jev | 15/26 | 10/12 | 4/5 | 0 | 3 | 180 ms | 238 ms | $0.000144 |
| GPT-6 Luna | 26/26 | 11/12 | 5/5 | 0 | 0 | 2,143 ms | 3,582 ms | $0.000120 |
| Jev → GPT-6 Luna | 22/26 | 11/12 | 5/5 | 0 | 0 | 192 ms | 2,526 ms | $0.000142 |

The configured GPT-6 Luna pipeline passed every development gate in this run. Its only miss was `dev-073`, an
unknown Seattle Pilots team in a single-game stat question: it returned
`unsupported/not_basketball` where the label calls for a team clarification.
Jev and the cascade failed the complete-request gate, despite lower median
latency. The cascade adds an adapter and threshold policy yet did not match
Luna's accuracy. The earlier 42-case pass also put GPT-5.6 Luna behind GPT-6
Luna on accuracy (38/42 versus 39/42), with higher estimated cost per correct
answer ($0.000649 versus $0.000301). GPT-5.6 Luna and gpt-4.1-mini were not
rerun after the transport fix; that earlier result is background, not a gate
claim for the final 43 cases.

GPT-6 Luna was selected provisionally for the local development pipeline. This
is not a settled production model choice. The Jev adapter and cascade still use
uncalibrated confidence thresholds; Luna reports no field confidence and does
not face those vetoes. Jev also has no missing-date extraction path equivalent
to Luna's. These results compare configured implementations, not intrinsic
model ability. The report does not retain field probabilities, so it cannot
attribute Jev's ten unnecessary clarifications to particular thresholds.

Before choosing a production architecture, diagnose both implementations on
shared development questions, calibrate Jev thresholds on exposed data, freeze
both configurations, and compare them on a new unseen set. The later independent
Luna release failures below reinforce that the original choice was provisional.
Keep production disabled until the frozen release gates pass. Record the
provider-resolved model and evaluation date for every comparison.

## Prototype fixture audit

`server/tests/fixtures/ask_seed.json` (25 questions) and `ask_heldout.json`
(75 questions) come from the deleted prototype (commit `b8f3a84`). They use its
old `AskInterpretation` schema, with raw mentions and date expressions instead of
candidate IDs and resolved requests.

The 25 seed questions and 75 old "heldout" questions were committed with the
prototype. Their labels are not `AskRequest`s: they describe mentions, raw date
phrases, and an old `boxscore_stats` intent. Five of the 43 new development
questions exactly match questions in those files (`dev-001`, `dev-002`,
`dev-003`, `dev-025`, and `dev-062`). The old heldout file is exposed too; its
name does not make it an unseen release set. Keep both files as historical
evidence, and exclude every reused question from the release evaluation.

Neither file may be used as the unseen release set. They can be mined for
development questions, after relabeling them against the new contract. Any
question reused this way counts as exposed.

## Open work

The development comparison is complete. Keep Jev and cascade thresholds out
of production. #189 must run a separate unseen 75–100 question release set
against the chosen single-provider configuration and the then-current lookup.
The production switch stays off if any gate fails. Investigate the `dev-073`
unknown-team miss without changing the development label or treating this
exposed set as release evidence.

## History: prototype parser

Before the contract existed, a single-call OpenAI parser (`gpt-4.1-mini`) was
built and probed. Its first live runs, on September 11, 2026, hit
`credit_balance_exhausted`/`insufficient_quota`. Later single probes succeeded,
for example 1 seed question in 3.17 s at $0.00058 list price. One full seed run is
recorded in `ask-seed.json`: gpt-4.1-mini passed 10 of 25 seed questions, with 3
requests of unknown usage. No held-out run was recorded. The saved reports remain in
`docs/verification/`:

- `ask-seed-access.json`
- `ask-sharing-access.json`
- `ask-live-endpoint.json`
- `ask-player-date.json`
- `ask-seed.json`

They describe that deleted parser and cannot be compared with the adapters above.


## First independent release attempt, September 29

The selected interpreter and candidate lookup were frozen before the private
release questions were opened. Initial label serialization mistakes invalidated
the first scoring run. An independent label audit corrected the action names,
explicit season/conference labels, and candidate value formats. The original
invalid-label report and the [audit trail](verification/ask-release-label-audit.json)
remain available. No interpreter or candidate changes were made between those
runs. Evaluation scoring now compares authoritative entity IDs and request
parameters, retaining full display fields for review.

The [audited 80-question run](verification/ask-release-2026-09-29.json) scored
75/80 overall, with 65/67 complete requests, 6/9 clarifications, 4/4 unsupported
requests, three schema-valid guesses, and zero service failures. Median latency
was 2.234 seconds, p95 was 3.700 seconds, and estimated provider usage was
$0.009333. This fails the zero-guess and clarification gates, so production
remains disabled. The failures broadened underspecified series or conference
finals requests into whole-postseason summaries, or treated missing game
selection as unsupported. Corrections require another independent unseen set.

[Candidate lookup](verification/ask-candidates-release-2026-09-29.json) passed
all 175 gold values across 83 questions, with 2/2 no-match cases and 2/2
ambiguities preserved. Warm p95 was 0.264 ms. These labels are now exposed and
are stored under `server/tests/ask/fixtures/` for regression use, not future
release evidence.


## Second independent release attempt, September 29

A separate author prepared 80 questions and a separate reviewer audited the labels
before any provider call. Interpreter commit `b4e0229` and candidate commit
`cf3737b` were frozen for this run. The input SHA-256 was
`cf6008f5694814cf9d1671e7ff08a6c2f779760c4f06b3e6569193c8250cc0a3`.

The [unaltered report](verification/ask-release-two-2026-09-29.json) scored
64/80 overall: 38/48 complete requests, 15/20 clarifications, and 11/12 unsupported
requests. It recorded seven schema-valid guesses and one invalid-output service
failure. Median latency was 2.376 seconds, p95 was 3.762 seconds, and estimated
provider usage was $0.023149. This fails the release gates. Production remains
disabled. The questions are now exposed regression material under
`server/tests/ask/fixtures/eval/release-two-2026-09-29-exposed.json`.

Triage found missing boxscore-page game context, lost target-team selection when
both opponents are named, a split calendar range, and an unrecognized hyphenated
round. It also found label concerns: case 029 omits a named team from the game
selector, case 062 requires one particular field when either round or teams can
start clarification, and case 056 expects a missing-stat clarification despite
the documented default to a full stat line. The raw report and labels remain
unchanged. These concerns do not erase the confirmed failures or establish a
passing release. Any corrected implementation needs another unseen release set.


## Paired exposed-set comparison after shared fixes

The user challenged the provisional Luna choice because Jev had not received
comparable calibration work. We ran both configured implementations against the
same exposed second-release 80 questions at commit `80b5570`. This is a regression
comparison, not unseen evidence. Original labels and their documented concerns
were retained. The [raw report](verification/ask-jev-luna-regression-2026-09-29.json)
records $0.017794 in estimated usage under a $0.20 guard.

| Current implementation | Overall | Complete | Clarify | Unsupported | Guesses | Failures | Median | p95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Jev 1.13.0 | 48/80 | 22/48 | 15/20 | 11/12 | 0 | 1 | 173 ms | 228 ms |
| GPT-6 Luna | 67/80 | 41/48 | 14/20 | 12/12 | 4 | 0 | 2,402 ms | 3,836 ms |

Jev had zero schema-valid guesses and was much faster, but requested many
unnecessary clarifications. Luna accepted more correct requests but made four
schema-valid guesses. Neither passes the release gates. Jev's adapter still
uses uncalibrated intent, no-match and team-count thresholds, plus cascade
confidence thresholds; Luna has no confidence veto. The report does not store
the field probabilities needed to separate extraction errors from policy vetoes.
A production model recommendation therefore remains open. Record those details,
calibrate on development data, and freeze both implementations before a fresh
unseen comparison. No additional provider runs are required for this handoff.

## Tiered cascade calibration (2026-09-29, ADRs 0002 and 0009)

`scripts/ask/evaluate.py collect` recorded Jev and GPT-6 Luna once on all 203
exposed cases (`dev.json` plus both exposed release sets), using lookup candidates.
It spent an estimated $0.072 of a $0.60 cap:
[`ask-tier-trace.json`](verification/ask-tier-trace.json). `calibrate` then
replayed the cascade offline across thresholds with no provider calls:
[`ask-tier-calibration.json`](verification/ask-tier-calibration.json).

These are **exposed** cases. They are calibration data, not gate evidence.

| Jev accept_min | Correct | Guesses | Unneeded clarifications | Finished by Jev / Luna |
| ---: | ---: | ---: | ---: | ---: |
| 0.5 | 160/203 | 5 | | 195 / 8 |
| 0.8 | 182/203 | 4 | 12 | 119 / 84 |
| 0.85 | 187/203 | 3 | 8 | 102 / 101 |
| 0.9 | 188/203 | 3 | 7 | 94 / 109 |
| 0.95 | 188/203 | 3 | 7 | 65 / 138 |

`veto_min` from 0.0 to 0.5 changed no outcome. In every remaining guess, either
both tiers agreed on the wrong reading or Jev had no competing selection.
**0.9** keeps accuracy at its plateau while Jev still finishes 46% of cases, so it
remains the default.

The three guesses at 0.9:

- `release-two-056` ("How many did Nikola Jokic have…"): Jev was unsure of the
  stat, and Luna chose `stat_line` instead of asking which stat. This is a real
  guess by the final tier.
- `release-two-006` ("games … tonight in New York"): Luna added a Knicks filter,
  while the label expects no team filter. The label is debatable: a location is
  not a team, and the schema has no venue filter.
- `release-two-029` (Boston's defensive rebounds in Game 3 of the 2024 Finals):
  every field was correct. The normalizer also adds the target team to
  `game.teams`, which selects the same game, but the strict scorer counts it as
  a different request. This is a scoring and normalizer convention mismatch,
  not a wrong answer.

The field-level tier oracle (`trace.field_reads`) reported 99.8% Jev precision
even at 0.5. It scores only `selected` reads on fields that accept labels pin
down, so it misses the errors that matter. It is too lenient to serve as the
ADR 0009 tier gate. Before any gate run, it needs `absent` reads on optional
fields, clarify and unsupported labels, and boxscore team roles.

The Luna-only replay is not comparable: when Jev called a case unsupported, the
cascade never recorded Luna on it (15 cases).

### Recalibration after the external review (2026-09-29)

An external review of `cdc6c68` found three defects, all reproduced and fixed with
regression tests (`server/tests/ask/test_review_fixes.py`, `test_location.py`):

1. A selection from a truncated candidate list ("Jalen" has 18 matches, and 8 are
   offered) was executed. The normalizer now asks for clarification instead.
2. A sentence-initial capital ("How …") disabled lowercase names ("lebron"). The
   casing check now ignores sentence-initial capitals, acronyms, and team names.
   Fuzzy one-word matches still need a capital, or an all-lowercase question.
3. The venue filter ignored history ("games in Brooklyn" in 2005). Each city now
   carries dated team tenures (ADR 0011).

The venue filter adds a `location` field. When the lookup finds no "in <city>",
the field is absent by construction and no model is asked (`LOOKUP_DECIDED`).

The trace was re-recorded on the fixed code for an estimated $0.050. Replay results:

| Jev accept_min | Correct | Guesses | Finished by Jev / Luna |
| ---: | ---: | ---: | ---: |
| 0.8 | 184/203 | 2 | 120 / 83 |
| **0.85** | **188/203** | **1** | **103 / 100** |
| 0.9 | 188/203 | 1 | 92 / 111 |
| 0.95 | 188/203 | 1 | 65 / 138 |

The default is now **0.85**: same accuracy as 0.9, with more traffic kept on Jev.
The one remaining guess is `release-two-029`, the `game.teams` scoring
convention; the answer itself is correct. Remaining failures:

- 4 unsupported answers where the label expects a clarification: missing page
  context, and "Dwight Schrute".
- 4 unneeded team clarifications on two-team stat questions: the known
  target-team schema gap (`nba-scores-kzc.1`).
- 2 season clarifications and 2 date clarifications.

These are exposed cases, used for tuning. Next step: freeze this configuration and
run a new unseen set written by someone who has not seen these cases.

## Frozen independent 100-question run, September 29

The frozen `9291237` production cascade was run once on 100 questions written
by an isolated agent. Each of the four Phase 1 request types has 25 cases.
Jev used accept minimum 0.85, Luna used low effort, and the veto minimum was 0.5.
No production configuration or tool changed during measurement.

The unchanged raw report scores 89/100 and flags three accepted-request errors.
An independently confirmed date-label error accounts for one flag: at February 8,
21:35 New York time, "last night" is February 7, as the application selected.
The separate semantic audit therefore finds 90/100 correct and two unsafe
accepted interpretations. Those errors are selecting Stephen for ambiguous
"Curry", even after Luna reports ambiguity, and treating historical "when they
were in New Jersey" wording as a home-only venue restriction.

The zero-guess gate fails. Clarification accuracy also fails at 13/15, while all
10 unsupported cases are correct. Median latency is 2.102 seconds and p95 is
3.728 seconds. Jev finished 49 questions without Luna; Luna ran on 51.
Known provider usage is $0.027154; the spend guard conservatively accounted
$0.032570 because one timed-out request has unknown usage.

All 100 results survived a report-assembly path error and were summarized offline
without another provider call. The original journal, labels, manifest, executed
runner, and raw report remain intact. The runner's path fix has a regression test.
See the [full evaluation and audit](verification/ask-unseen-2026-09-29.md).

The set is now exposed. It measures interpretations, not retrieval or rendered
answers, and cannot establish the incomplete tier precision gate. Production
remains disabled; fixes require another unseen set.

## Target team field (nba-scores-kzc.1)

Interpreter output now has a `target_team` field, separate from `teams`, for the
team whose statistics a team-scope boxscore question asks for (see
`docs/ask-contract.md`). Jev gets its own Choice for it. Luna's schema and prompt
gained one rule that has not been checked live. The field oracle
(`trace.expected_fields`) scores `target_team` for team-scope accept labels. The
exposed two-team cases (release-two 019-022) are not release evidence for this
change; only a fresh unseen set is.

## Fixes after the second unseen run (not yet measured)

These changes address misses exposed by `ask-unseen-two-2026-09-29`. They are
covered by deterministic tests only; no provider was called. Validate them on a
fresh unseen set.

- Lookup: on-screen date wording ("the date I have open") offers the page date,
  unless the question sets it aside; ordinal game numbers ("the sixth game") in
  playoff questions; rounds named with playoff wording or numbers ("first
  playoff round", "round 2"); "most recent"/"latest" weekdays; a one-word team
  name no team used in the requested season stays open to exact player names
  ("Magic" in 1987).
- Cascade: a later confident `absent` read replaces an earlier
  `no_matching_candidate` when lookup found no text for the field. Jev's
  unsupported outcomes keep their confidence. A later `unsupported` outcome still
  ends the cascade after an accepted intent: it executes nothing, and contesting
  it would have turned two correct unsupported answers in the recorded traces
  into clarifications without fixing any.
- Normalizer: with an ambiguous intent, a field unclear under every intent
  option is asked about first.
- Unverified live: Jev's new `target_team` question and Luna's `target_team`
  schema and prompt rule.
