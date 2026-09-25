# Natural-language search evaluation

The initial live validation on September 11, 2026 was blocked: the backend's
configured OpenAI key returned HTTP 429 with `credit_balance_exhausted` and
`insufficient_quota`. A later request using that key and the eligible
`gpt-4.1-mini-2025-04-14` snapshot succeeded; no replacement key was needed. The key was not printed or copied into frontend code.

The initial access comparison attempted GPT-4.1 mini and GPT-4.1 nano. Both
returned provider failures before producing an interpretation. The saved
[access report](verification/ask-seed-access.json) records those attempts.
Its timings describe failed requests, not successful search latency. Its fixture
and prompt hashes identify the earlier access probe, not the revised fixture set.
The later [sharing access probe](verification/ask-sharing-access.json) passed one
seed question in 3.174 seconds, using $0.0005836 at regular list prices. This
estimate does not establish an actual charge or incentive eligibility. One case
is insufficient to select the model.

The issue asks for parser evaluation before retrieval implementation. That gate
was attempted first, but could not complete because of the provider credit limit.
Backend implementation continued against typed fixtures. GPT-4.1 mini is a
provisional default, not a measured winner. Do not mark the issue release-ready
until the live gates below have run.

## Follow-up live checks

The [endpoint probe](verification/ask-live-endpoint.json) returned a complete 2023
Finals answer (Denver 4–1 Miami, with the Finals route) in 2.490 seconds. The next
request failed at the parser, and the 60-second provider cooldown made subsequent
requests unavailable. These were direct HTTP requests, not browser interaction.

The follow-up seed comparison recorded intermittent `credit_balance_exhausted`
failures as well as interpretation mistakes. A successful individual request does
not establish reliable access or release readiness. Regular-season team records
were then explicitly added to the prompt's unsupported scope after the user's
Thunder question; existing live reports predate that clarification.

A subsequent browser check submitted the user's exact Shai/biggest-win question
on the local Hardwood page. It displayed the specific unsupported explanation,
with four selectable examples visible. This path makes no model call. Regression
coverage now includes all three reported regular-season questions, typographic
season dashes, and choosing an example without automatically submitting it.
The 90 backend search tests and seven frontend search tests pass. The revised
prompt still needs a fresh seed evaluation before any held-out run.

## Fixtures and scoring

`server/tests/fixtures/ask_seed.json` contains 25 seed questions.
`server/tests/fixtures/ask_heldout.json` contains 75 held-out questions covering
aliases, relative dates, playoff years and rounds, numbered Finals games,
boxscore statistics, historical records, ambiguity, and unsupported requests.

Each expected value uses the full `AskInterpretation` schema, including operation,
mentions, raw date expressions, requested statistics, round, game number,
ambiguities, and unsupported status. Offline validation checks fixture schemas
only; it is not a parsing accuracy measurement.

The evaluator calls the production `parse_ask` function with its actual prompt
and strict schema. It scores every selector, clarification fields, and schema
validity separately. A case passes only when all checked fields match. Extra
selectors fail. List order and capitalization are ignored, but identifiers or
resolved dates cannot be substituted for raw mentions. Alternative expected
interpretations can be explicitly recorded when both are valid.

```bash
server/venv/bin/python scripts/evaluate-ask.py --offline --split seed
server/venv/bin/python scripts/evaluate-ask.py --offline --split holdout
server/venv/bin/python scripts/evaluate-ask.py --split seed --models gpt-4.1-mini-2025-04-14 gpt-4.1-nano-2025-04-14 --max-cost 1 --output docs/verification/ask-seed.json
```

After selecting a model on the seed set, freeze the prompt and run the held-out
set. Use repeated representative runs to measure median and p95 latency.
Do not tune the prompt on held-out failures and then report that set as unseen.

```bash
server/venv/bin/python scripts/evaluate-ask.py --split holdout --models gpt-4.1-mini-2025-04-14 --repeat 3 --max-cost 1 --output docs/verification/ask-holdout.json
```

The script reserves a conservative cost before each request using the complete
serialized request's UTF-8 byte length plus framing allowance and the output
token ceiling. It refunds the excess only when usage is known. Failures with
unknown usage keep their reservation. Unknown model prices and custom providers
are rejected by this comparison script.

The recorded rates come from the official model pages: [GPT-4.1 mini](https://developers.openai.com/api/docs/models/gpt-4.1-mini)
and [GPT-4.1 nano](https://developers.openai.com/api/docs/models/gpt-4.1-nano).
They are $0.40/$1.60 and $0.10/$0.40 per million input/output tokens respectively.
The script estimates regular input rates even if caching discounts or complimentary
shared-data tokens apply. Reports label this `list_price_cost_usd`;
`actual_billed_cost_usd` remains null because token usage does not establish billing.
Confirm actual charges in the OpenAI Usage Dashboard. Refresh the rate table before
later evaluations; account access may differ. See [configuration](ask-search.md#complimentary-shared-data-tokens)
for enrollment and balance requirements.

## Separate application checks

`test_ask_basketball.py` checks deterministic resolution and calculations, including
New York date boundaries, previous calendar weeks, aliases, ties, missing values,
player ambiguity, and the repository's real sample boxscore shape.
`test_ask_data.py` checks authoritative retrieval, unique game selection, series
links, pregame scores, and missing records versus provider outages.
`test_ask.py` checks the endpoint, validation, caches, limits, and failure responses.
`AskSearch.test.tsx` checks spoiler behavior, links, clarification, and error states.

These offline tests do not replace live end-to-end checks. Once credit is
available, run representative searches through `/ask`, verify game and series
links against returned NBA data, and measure full-request median and p95 latency
separately from parser latency. Successful requests provide token usage and a list-price estimate; actual billed
cost must be checked separately in the provider dashboard.


## Player/date regression

The user's exact question, `How many points did Shai Gilgeous-Alexander score on
January 2, 2024?`, now succeeds without a team mention. A live
[HTTP probe](verification/ask-player-date.json) returned 36 points for game
`0022300462` in 2.801 seconds. A subsequent browser submission also displayed
36 points and the dated game-details link. NBA LeagueGameFinder and the boxscore
both recorded that value. The browser's global results preference was enabled.

The parser prompt now treats a named player plus one date as sufficient.
Python matches a player catalog ID, verifies the player's historical game/date,
and selects its boxscore; no present-day team assumption or boxscore fanout is
used. Tests cover ambiguity, missing games, malformed provider rows, date/player
mismatches, duplicate game IDs, and matching the selected game to the scoreboard.
The full backend suite passes: 351 tests. This specific live success does not
replace the remaining seed and held-out parser evaluation gates.
