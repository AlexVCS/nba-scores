# Natural-language basketball search

The search UI has been removed from the original and Hardwood pages. The backend
remains available through `POST /ask`, which accepts `{"question":"..."}` with
1–300 characters. The UI descriptions below document the earlier prototype;
`scripts/verify-ask-search.mjs` requires restoring that UI before it can run.
The model interprets one question. Python resolves teams, dates, games, and
statistics, then the frontend renders the answer. Single-stat answers appear
once in the headline; answers with several stats use a compact table beneath
the player and game context. Game results reuse the scores page's existing
game-card component, with the interpretation underneath. There is no second
model call to write an answer.

## Supported requests

- Games on a date or within seven consecutive days, optionally filtered by teams.
- One player's statistics, team totals, or the leaders in one statistic for one game.
  A player name and a single date are sufficient; the team is optional. Team
  totals and leaders still need a team/date or playoff game selectors.
- A playoff series identified by year and matchup or round.
- A whole postseason or one team's postseason game results.

Examples include `Cavs games last week`, `How many points did Tatum score in game
4 of the 2024 Finals?`, and `Who won the 2023 NBA Finals?`.

Career statistics, broad historical comparisons, predictions, conversational
follow-ups, season-wide player averages, regular-season team win/loss totals,
and season-wide biggest-win searches are unsupported. Ambiguous requests
ask for more detail. Historical data gaps return `not_found`; provider outages
return `unavailable`. Some historical names are supported as franchise aliases;
unrecognized or ambiguous team names require clarification.

Relative dates use `America/New_York`. `last week` means the previous Monday
through Sunday. `last Friday` means the preceding Friday, excluding today when
it is Friday. A playoff year of `2024` resolves to season `2023-24`. Dates without
a year require clarification.

Scores, player names, series participants and winners, statistics, and revealing
links are omitted from the DOM while hidden. Each result has its own reveal
control and respects the global results preference. A new search resets local
reveals. Global show followed by global hide also resets them.

The form provides short example chips. Choosing an example fills the input and
submits it. Examples disappear after a result and return when the input is
cleared; notices include two examples to help with another search.

Responses include an `interpretation` list built from the validated question,
so users can check how it was read even while the answer is hidden. Items also
include `context`, `teams` with ID, tricode, and name, and an optional `player_id`
for team colors, logos, and headshots. Game items carry a `game` payload with
the original scoreboard data for the shared game card. Result metadata stays out of the rendered
card until reveal. These additions do not change supported requests or retrieval.

Explicit regular-season record,
standings, and biggest-win requests are checked before the model or budget,
so they receive a specific unsupported response even during provider outages.
Typographic dashes in supported playoff season selectors are normalized.

For a player/date question without a team, Python matches the NBA player catalog
and queries LeagueGameFinder for that player on the exact date. It checks the
returned player ID/date, requires one unique game, and verifies that game against
the date's scoreboard before reading the boxscore. It never infers historical
team membership from a current roster. Ambiguous names request a full name.

## Server configuration

The backend reads `OPENAI_API_KEY` from the process environment or `server/.env`.
Do not use a `VITE_` variable for API keys. Keys belong to projects; switching
models does not require a new key when the project allows that model. An initial
probe on September 11, 2026 returned `credit_balance_exhausted`; a later probe
with the same configured key succeeded. See the evaluation report for live results.
A provider failure is cooled down for 60 seconds to avoid repeated paid attempts.

| Variable | Default | Purpose |
| --- | --- | --- |
| `ASK_PARSER_PROVIDER` | `openai` | `openai` or a Responses-compatible provider |
| `ASK_PARSER_MODEL` | `gpt-4.1-mini-2025-04-14` | Eligible snapshot; provisional parser model pending live evaluation |
| `OPENAI_RESPONSES_URL` | OpenAI `/v1/responses` | Server-configured provider endpoint |
| `ASK_API_KEY` | unset | Key for `openai_compatible` |
| `ASK_DAILY_BUDGET_USD` | `1` | List-price application guard per UTC day |
| `ASK_STATE_DIR` | `server/.ask-state` | Durable budget ledger directory |
| `ASK_INPUT_USD_PER_MILLION` | known model rate | Required for custom providers/models |
| `ASK_OUTPUT_USD_PER_MILLION` | known model rate | Required for custom providers/models |
| `ASK_CACHE_VERSION` | `1` | Bump after corrections or semantic changes |

Only the API key has a server-local dotenv fallback. Set the other configuration
variables in the backend process environment or deployment settings.

The JSON budget ledger uses a file lock, atomic replacement, and fsync so worker
processes sharing the directory reserve spending before a model call. Corrupt or
unwritable state stops paid requests. Unknown-cost failures retain their
reservations. Use a persistent shared volume for backend workers. Separate
replicas with separate filesystems each have their own budget; do not deploy
multiple such replicas and treat the limit as shared.

The endpoint limits each client to 10 requests per minute and each worker to 60
requests per minute. It accepts at most two in-flight search workers and bounds
the HTTP response wait to 20 seconds. Slow synchronous NBA work may finish later,
but retains its worker slot so repeated timeouts cannot build an unbounded queue.
Configure trusted proxy handling in uvicorn; the endpoint does not read arbitrary
forwarded headers itself.

## Complimentary shared-data tokens

The default snapshot is listed in [OpenAI's complimentary-token program](https://help.openai.com/en/articles/10306912-sharing-feedback-evaluation-and-fine-tuning-data-and-api-inputs-and-outputs-with-openai).
The API key's project must have input/output sharing enabled, and the organization
must show enrollment for complimentary daily tokens. Benefits apply automatically;
a new key is unnecessary for an existing eligible project. OpenAI still requires
a positive account balance, including for complimentary usage.

GPT-4.1 mini and GPT-5.6 Luna share the larger daily pool: 2.5 million tokens for
usage tiers 1–2 or 10 million for tiers 3–5. It resets at midnight UTC. Other
eligible traffic in the organization consumes the same pool; a request crossing
the limit is billed in full. Check the Usage Dashboard's incentive service tier
and Costs to confirm actual billing.

The local budget and evaluation reports use regular token list prices before
complimentary tokens or caching discounts. They cannot observe the organization's
remaining allowance. The default $1 guard may therefore pause requests even when
actual charges are zero. Change `ASK_DAILY_BUDGET_USD` deliberately if more
throughput is needed; do not set token prices to zero to represent the incentive.

## Cache and diagnostics

Parse caches are bounded to 256 entries and expire after one hour. Their keys
include normalized question text, New York day, provider, model, prompt/schema
fingerprint, and cache version. Identical concurrent parses share a lock.

Answer caches use resolved dates, team IDs, player mentions, operations, statistics,
rounds and game numbers. Ongoing or uncertain results expire after 30 seconds.
Explicitly final daily games can remain in the bounded process cache until
invalidation or eviction. Postseason data lacks a consistently explicit completion
status, so it always uses the short TTL. No database or vector index is added.

After correcting source data, clear its existing service cache and call
`invalidate_ask_caches()` or restart with a new `ASK_CACHE_VERSION`. Restarting
clears the in-memory search caches. The durable spending ledger survives restart.

Unsupported-request diagnostics retain at most 200 entries for up to seven days,
pruned on insertion/read and cleared on restart. They store question hashes and
requested operations/statistics/missing fields, not raw questions, IPs, or keys.
`unsupported_request_log()` is internal and has no public route. Usage logs contain
model name, token counts, and parser latency only.

See [evaluation](ask-evaluation.md) for the blocked live gate and rerun commands.
