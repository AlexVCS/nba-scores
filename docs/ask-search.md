# Ask search

Ask is the Hardwood question interface backed by `POST /ask` and model-free
`GET /ask/suggest`. The HTTP shapes and spoiler rules are defined in
[`ask-contract.md`](ask-contract.md). The feature remains disabled by default:
the backend returns `unavailable` for Ask questions and empty typeahead data
until the release gate is explicitly enabled. Production builds show the Design 1
Ask entry only with `VITE_ASK_ENABLED=1`; the Vite development server shows it
by default. The frontend flag controls visibility, and the backend still needs
`ASK_ENABLED=1` to answer questions.

## What it answers

Ask supports games over one to seven consecutive days, one-game boxscore
statistics and leaders, a playoff series, and a team or league postseason
summary. It asks a clarifying question for an ambiguous player, team, date,
year, or game. Each option carries a short-lived resolution token; selecting
an option can lead to another clarification without another model call.
Unsupported requests are identified explicitly. Missing verified records are
`not_found`; data-source and interpreter failures are `unavailable`.

The model interprets the question using bounded player, team, season, round,
game-number, and date candidates. A Python normalizer validates every selected
ID and produces a typed request. The basketball resolvers use only that typed
request and existing data services. Python writes all result copy, links,
notices, and clarification options. The model never writes answer prose or
calls data services. Exact date searches (`games on YYYY-MM-DD`, `scores for
YYYY-MM-DD`) and boxscore-context leader questions use validated direct
shortcuts with zero model calls. A cached parse or resolution token also
avoids a new model call.

Relative dates use the New York calendar date at request time. A date the
user wrote without a year needs a year choice; no year is guessed. Candidate
aliases, interpreter instructions, model name, cache version, app context,
and New York day key parsed interpretations. Verified answer results have a
short cache lifetime. Cache failures are not stored.

## Spoilers and typeahead

Asking is consent (ADR 0006): Ask shows every requested answer immediately,
whatever the global results preference. The preference still governs what the
user did not ask for. Interpretation chips beside a clarification, clarification
options, follow-up links, and suggestions carry spoiler flags, and the UI omits
flagged content from the DOM while results are hidden. A single-game question
whose choice list could reveal a result (a playoff date or a numbered series
game without teams) asks for the teams before any result lookup.
Typeahead uses bounded candidate lookup and direct scoreboard matches, with
no model call. Hidden typeahead omits postseason direct games whose presence
could reveal advancement.

## Development response details

In the Vite development server, expand **Response details** beneath an Ask result
to see the interpreter model, whether this request made a model call, and whether
the backend reported a cache hit. The server prefers the model identifier returned
by the provider and falls back to the requested identifier. A clarification token
can retain the original interpreter model without a new model call or cache hit.
Exact direct lookups report that no model was used. These details describe question
interpretation; the answer values come from NBA data. Production builds omit the
control through `import.meta.env.DEV`.

## Operations

`ASK_ENABLED=1` enables the endpoint for local development testing. Production
enablement requires the separate release gates. The default model is `gpt-6-luna` at low reasoning effort. A daily
`$1` list-price guard reserves estimated cost before a provider call and
settles reported usage afterward. If the provider call's cost is unknown,
the reservation stays charged. The ledger is shared through `ASK_STATE_DIR`
and fails closed on corruption or a lock error. Only `OPENAI_API_KEY` may be
read from `server/.env`; all other settings come from process environment.

The HTTP boundary limits requests to 10 per client and 60 per worker per
minute. Two Ask workers may run concurrently, with a 20-second response
deadline. A timed-out worker keeps its slot until the provider call ends,
including budget settlement. The client identity uses the transport peer,
not an untrusted forwarded header. Anonymous diagnostics store a salted
question hash and bounded enums, never raw questions, IPs, prompts, or keys.

Run the Ask checks with
`server/venv/bin/python -m pytest -q server/tests/ask` from the repository
root. No provider call is needed for these tests. Enabling production traffic
still requires the separate unseen-question evaluation and manual release
checks; setting the flag alone is an operational choice, not validation.
