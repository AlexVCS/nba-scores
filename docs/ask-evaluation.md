# Ask: interpreter evaluation (#199)

This document covers the interpreter adapters, the evaluation harness, and the
results so far. The decision on the interpreter architecture (one provider or a
cascade) is still open. The comparison runs once #200's candidate lookup lands,
because Jev must be measured with lookup candidates, not hand-picked ones.

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

**All thresholds are uncalibrated placeholders:** `JevThresholds` and
`PolicyThresholds` (`accept_min=0.7`, `clarify_min=0.6`, `ambiguity_floor=0.25`,
and so on). They must be calibrated on development data before any production
use. No cookbook values are used.

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
| Complete request accuracy | at least 90% |
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

## Prototype fixture audit

`server/tests/fixtures/ask_seed.json` (25 questions) and `ask_heldout.json`
(75 questions) come from the deleted prototype (commit `b8f3a84`). They use its
old `AskInterpretation` schema, with raw mentions and date expressions instead of
candidate IDs and resolved requests.

The 25 seed questions and 75 old "heldout" questions were committed with the
prototype. Their labels are not `AskRequest`s: they describe mentions, raw date
phrases, and an old `boxscore_stats` intent. Five of the 42 new development
questions exactly match questions in those files (`dev-001`, `dev-002`,
`dev-003`, `dev-025`, and `dev-062`). The old heldout file is exposed too; its
name does not make it an unseen release set. Keep both files as historical
evidence, and exclude every reused question from the release evaluation.

Neither file may be used as the unseen release set. They can be mined for
development questions, after relabeling them against the new contract. Any
question reused this way counts as exposed.

## Open work

1. **Labeled dev set.** Write `server/tests/ask/fixtures/eval/dev.json`, covering
   all four intents, aliases, historical names, relative dates, ambiguity, absent
   candidates, historical gaps, and unsupported requests. Label with `AskRequest`
   values.
2. **Comparison run.** Run it with #200's lookup, `--lookup`, and its `expand`.
3. **Calibration.** Calibrate `JevThresholds` and `PolicyThresholds` on the dev
   set, including the weakest required selection and absent-candidate cases.
   Record the chosen values here.
4. **Decision.** Choose between a single provider and a cascade, and between
   GPT-6 Luna and GPT-5.6 Luna. Justify the choice against the maintenance cost of
   a second adapter.
5. **Release set.** Build a separate unseen 75–100 question release set (#189).

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
