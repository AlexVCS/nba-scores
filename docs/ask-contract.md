# Ask: shared contract

The contract for Ask (#189) and its children: #199 (interpreters), #200
(candidate lookup), #201 (backend pipeline), #205 (UI). It lets those four
branches proceed in parallel. `docs/ask-search.md` describes a deleted
prototype and is design history only.

The code is the source of truth; this document summarizes it.

| Piece | File |
| --- | --- |
| Shared value types (intent, stat, round, season, refs, dates, `Guarded`) | `server/ask/models/common.py` |
| Normalized application request | `server/ask/models/request.py` |
| Candidate lookup output | `server/ask/models/candidates.py` |
| Interpreter input/output, normalization result | `server/ask/models/interpreter.py` |
| HTTP request/response (`POST /ask`, `GET /ask/suggest`) | `server/ask/models/response.py` |
| Protocols (lookup, adapter, normalizer, cascade policy) | `server/ask/protocols.py` |
| TypeScript mirror of the HTTP contract | `src/services/ask/types.ts` |
| Fixture responses | `src/services/ask/fixtures/{responses,suggest}/*.json` |
| Fixture loader for the UI | `src/services/ask/fixtures/index.ts` |
| Fixture validation | `server/tests/ask/test_contract_fixtures.py` |

All contract models are strict (`extra="forbid"`) and immutable, so they can
be used in cache keys. Import from the submodules
(`from server.ask.models.request import AskRequest`); `server/ask/models/__init__.py`
does not re-export anything.

## Pipeline

```
question + ClientContext
  -> [#201] resolution token / exact match / cache hit?  -> execute, zero model calls
  -> [#200] CandidateLookup.lookup()                      -> CandidateLookupResult
  -> [#199] InterpreterAdapter.interpret()                -> InterpreterOutput
  -> [#199] RequestNormalizer.normalize()                 -> NormalizationResult (AskRequest | clarify | unsupported | invalid)
  -> [#199] CascadePolicy.decide()                        -> accept | fallback | expand_candidates | clarify | unsupported | fail
  -> [#201] resolvers/calculators on AskRequest           -> AskResponse
  -> [#205] UI renders, applying spoiler flags
```

Every call is synchronous. The endpoint runs them in FastAPI's threadpool, as
the existing NBA services do. None of these components may depend on an HTTP
request object, so scripts and evaluations can call them directly.

## 1. Normalized application request (`request.py`)

`AskRequest` is a discriminated union on `intent`. It is the only input that
data tools accept. Every entity has an authoritative ID (`TeamRef.team_id`,
`PlayerRef.player_id`, a 10-digit `game_id`). Every date is a resolved
America/New_York calendar date.

| Intent | Model | Required |
| --- | --- | --- |
| `game_search` | `GameSearchRequest` | `dates: DateRange` (1–7 days inclusive); `teams` has 0–2 entries |
| `boxscore_stat` | `BoxscoreStatRequest` | `scope` (`player`/`team`/`leaders`), `stat: StatSelection`, `game: GameSelector`; `player` required for player scope and only allowed there; `team` (or a team in `game.teams`) required for team scope |
| `playoff_series` | `PlayoffSeriesRequest` | `season`, plus one of: 2 teams; 1 team + round; `round=finals`; `round=conference_finals` + conference |
| `postseason_summary` | `PostseasonSummaryRequest` | `season`; `team` optional (`None` means league-wide) |

- `GameSelector` identifies exactly one game in one of three ways: `game_id`;
  `date` (with optional teams); or `season` + `game_number` + (`round` or two
  teams). A player and a date are enough. The resolver finds that player's
  game from dated records, never from current rosters.
- `StatSelection` is `stat` + `aggregation` (`total`/`per_game`). Stats include
  `stat_line` for a full line, which is not valid for leaders. Single-game
  requests must be `total`. A question that asks for an average across games is
  represented as `per_game` and does not validate. Normalization reports it as
  unsupported (`multi_game_average`) and never silently answers it as a total.
- `Season` is `"YYYY-YY"`, validated as consecutive years. A playoff year maps
  to the season that ends in it: "2024 Finals" is `2023-24`.
- `PlayoffRound` uses the modern names (`first_round`, `conference_semifinals`,
  `conference_finals`, `finals`). Resolvers map historical formats onto them.
- `AskContext` has a server-assigned, timezone-aware `reference_time` in
  America/New_York, plus the page context (`route`, `view_date`, `game_id`,
  `playoff_season`). Relative dates resolve against `reference_time`. "Last
  week" is the preceding Monday–Sunday. Its NY date belongs in relative-parse
  cache keys.
- `DateComponents` is date language broken into parts: `calendar_date`,
  `calendar_range`, or `relative`, where `relative` is one of `today`,
  `last_night`, `last_week`, `last_weekday`+`weekday`, `past_days`+`count`, and
  so on. `year=None` is kept as missing and leads to a `year_required`
  clarification. The year is never defaulted, including the date cookbook's
  default-year behavior.

## 2. Interpreter output (`interpreter.py`)

All adapters return `InterpreterOutput`:

- `outcome` is one of:
  - `interpreted`
  - `unsupported`, with `unsupported_reason`
  - `unreliable`: the adapter ran but cannot answer reliably, which makes this a fallback candidate
  - `unavailable`: provider error, timeout, or quota. Carries `error_code` and no fields.
- `fields` has at most one `FieldInterpretation` per field:
  - Candidate-backed fields (`player`, `teams`, `date`, `season`, `round`,
    `game_number`) select candidate IDs from the lookup.
  - Closed-set fields (`intent`, `stat_scope`, `stat`, `aggregation`) select
    literal enum values from `common.py`.
- Each field's `status` is one of:
  - `selected`: one value, or two for `teams` only
  - `absent`: the question does not say
  - `ambiguous`: two or more `alternatives` remain
  - `no_matching_candidate`: the question mentions it but nothing fits, with `mention` set

  A field that is not listed counts as `absent`.
- `confidence` is per field, from 0 to 1, normalized from the adapter's native
  score, or `None` when the adapter has none. The cascade policy uses it. #199
  calibrates the thresholds on development data; cookbook values are not
  production settings.
- `extracted_date` is optional. Only extraction-capable adapters (OpenAI) set
  it, and only when the date candidate set had no match. Python validates it,
  and it never overrides a selected date candidate.
- `metadata` records the adapter, provider, pinned `model`, the provider-reported
  `resolved_model`, latency, and usage (tokens, calls, list-price cost). It
  holds no prompts or raw output.

A schema-valid guess still counts as a failure. Adapters must report
`absent`, `ambiguous`, or `no_matching_candidate` instead of choosing. A
missing candidate is never evidence that the user meant something else.

`NormalizationResult.status` is one of:
- `valid`, with an `AskRequest`
- `needs_clarification`, with `clarify_field` and `clarify_reason`
- `unsupported`
- `invalid`: an unknown candidate ID or an impossible combination. It is never executed and goes back to the cascade.

## 3. Candidate lookup (`candidates.py`, `CandidateLookup` protocol)

`CandidateLookup.lookup(question, context) -> CandidateLookupResult`:

- The result contains a `CandidateSet` for every field in
  `CANDIDATE_FIELDS = player, team, date, season, round, game_number`.
- Each set's `status` is one of:
  - `candidates`: at least one candidate
  - `no_candidates`: the question mentions something of this type, listed in
    `unmatched_text`, but nothing matched
  - `not_mentioned`: nothing of this type was detected
- Limits: `MAX_CANDIDATES_PER_FIELD = 12`, `MAX_TOTAL_CANDIDATES = 48`, and
  `truncated` is set when a set was cut.
- `Candidate` has these fields:
  - `id`: stable within one result, e.g. `player:1631105`, `team:1610612752`, `date:0`
  - `field` and `label`
  - `matched_text` and `span`: where the match occurs in the question
  - `source`: `alias`, `player_catalog`, `team_catalog`, `historical_team_name`,
    `date_parser`, `pattern`, or `app_context`
  - `alias`: which alias matched
  - `match_score`: lookup similarity, not interpreter confidence
  - `value`: a typed value, discriminated by `kind`
- Typed values:
  - Player values carry dated `team_ids` and a season span.
  - Team values carry a validity window for the name.
  - Date values carry `DateComponents` and `resolved: DateRange | None`, with
    `unresolved_reason` set to `year_required`, `range_too_long`, or `invalid_date`.
- `alias_version` goes into cache keys. The alias mapping is shared by every
  adapter and by Python validation, and it is kept separate from statistical
  definitions.
- `expand(question, context, field, previous)` widens one field within the
  same limit. The cascade uses it after `no_matching_candidate`.

Closed sets (intent, stat, scope, aggregation) are not produced by lookup.
Adapters build them from the enums.

## 4. Adapter, normalizer, and cascade protocols (`protocols.py`)

```python
class InterpreterAdapter(Protocol):
    name: Literal["jev", "openai_responses"]
    model: str  # "jev-1.13.0", "gpt-4.1-mini-2025-04-14", Luna snapshot
    def interpret(self, request: InterpreterInput) -> InterpreterOutput: ...

class RequestNormalizer(Protocol):
    def normalize(self, output, candidates, context) -> NormalizationResult: ...

class CascadePolicy(Protocol):
    def decide(self, state: CascadeState) -> CascadeDecision: ...
```

- `InterpreterInput` contains the question, `AskContext`, the full
  `CandidateLookupResult`, `deadline_ms`, and `max_cost_usd`. Adapters must
  not raise for provider failures; they return `outcome="unavailable"`.
- Jev and both OpenAI-Responses models (gpt-4.1-mini baseline and Luna)
  implement `InterpreterAdapter`. One `openai_responses` adapter class
  parameterized by model is expected.
- `CascadeState` contains the attempts so far (each an output plus its
  normalization), the candidates, the fields already expanded, whether fallback
  is enabled, and the remaining budget and time. `CascadeDecision.action` is
  one of `accept`, `fallback` (with `adapter`), `expand_candidates` (with
  `field`), `clarify` (with `field`), `unsupported`, or `fail`. The single-provider
  configuration is a policy that never returns `fallback`. The fallback table
  in #199 is implemented here. Guessed parameters are never executed.

## 5. HTTP: `POST /ask` (`response.py`, `types.ts`)

The request body is `AskQuery`:
- `question`: 1–300 characters, whitespace stripped
- `context`: an optional `ClientContext` (`route`, `view_date`, `game_id`, `playoff_season`)
- `resolution`: an optional opaque token from a clarification option. The
  server executes that validated request with zero model calls. The token is
  server-issued, short-lived, and never trusted as parameters. #201 chooses
  the encoding, for example a signed request or a cache key.

The response is `AskResponse`. `schema_version` is `"1"`. JSON keys are
snake_case, except the embedded scoreboard `game`, which is the unchanged
camelCase `GameData` payload.

| `outcome` | Required | Meaning |
| --- | --- | --- |
| `answer` | `result`, `interpretation.intent` matching `result.kind` | Verified answer |
| `needs_clarification` | `clarification` | A required detail is missing or ambiguous (options ≤ 9, for keys 1–9) |
| `unsupported` | `notice` with `unsupported_reason` | Outside enabled scope |
| `not_found` | `notice` (`no_games`, `no_record`, `player_did_not_play`) | No basketball record exists |
| `unavailable` | `notice` (`service_unavailable`, `interpreter_unavailable`, `rate_limited`) | Data or provider failure; `retryable`, `retry_after_seconds` |
| `budget_exhausted` | `notice` (`budget_exhausted`) | Spend limit reached; no model call |

Other fields:

- `interpretation` holds the "Reading this as" data:
  - `detected_type` is the badge: `games`, `player_stat`, `team_stat`,
    `stat_leaders`, `series`, or `postseason`. It is not a filter.
  - `items` are the chips. Each has `field`, `value`, `detail`, `expression`
    (the user's words), `origin` (`question`/`inferred`/`context`), `status`
    (`resolved`/`ambiguous`), `match_count`, IDs for logos and headshots, and `spoiler`.
  - `reference_time` and `timezone` are always America/New_York; `dates` and
    `season` are the resolved date range and season.
- `result` is a union discriminated by `kind`:
  - `games`: `days[]` → `GameResultItem { date, game: <scoreboard payload>, spoilers {score, status_text, series_text}, links }`, plus `total_games`.
  - `boxscore_stat`: `game: GameContext`, whose `final_score` is `Guarded`
    and is revealed separately. Then, depending on scope, `player_line`
    (`values: Guarded<StatValue>[]`), `team_lines`, or `leaders` (the player,
    team, and value are all guarded). `StatValue` has `display`, plus `made`
    and `attempted` for shooting stats.
  - `playoff_series`: `teams[2]`, where each row's team is guarded when the
    user did not name it, and seed, wins, and `won_series` are guarded. Also
    guarded `status`, `games_played`, `summary`, and `games`, because the
    game count reveals the series length.
  - `postseason_summary`: guarded `finish`, `record`, `series_won`, and
    `rounds` (team scope), and `champion`, `runner_up`, and `series` (league
    scope). The whole `rounds` list is guarded because its length reveals advancement.
- `clarification` has `field`, `reason`, `prompt`, `detail`, `hint`, and
  `options[]`. Each option has `label`, `sublabel`, `detail`, team and player
  IDs, a standalone rewritten `question`, and a `resolution` token.
- `notice` has `code`, `title`, `message`, `retryable`, `retry_after_seconds`,
  `unsupported_reason`, and `diagnostics_recorded`. When
  `diagnostics_recorded` is true, the UI can say that an anonymous note was kept.
- `links` are `VerifiedLink { kind, label, href, external, spoiler }`, built by
  Python from verified IDs:
  - Internal `href`s must match an allowlist: `/?date=`,
    `/games/{id}/boxscore[?date=]`, `/playoffs[?season=]`, and
    `/playoffs/{year}/{slug}`. They are design-agnostic; the UI adds the
    active design prefix.
  - External links must start with `https://www.nba.com/`.
- `suggestions` are "Ask next" or "Try one of these" entries. Each is a
  standalone question with every name and date spelled out, a `category`, and `spoiler`.
- `sources` describe the data used: the source `name` and `label`, `fetched_at`,
  and `complete` (false while games or series are still in progress).
- `interpreter` supports source-aware copy: `model_called`, `cache_hit`,
  `adapter`, `model`, and `fallback_used`.

### Spoiler rules

The server always sends values. Every protected value is either
`Guarded<T> {value, spoiler}` or an object with `spoiler: true`. While results
are hidden (the default, which respects the global preference), the UI must
leave protected values out of the DOM and accessibility text entirely. Hiding
them with CSS is not enough. This includes suggestions and links with
`spoiler: true`, and interpretation items with `spoiler: true`. Entities the
user supplied are echoed with `spoiler: false`. Participants the server
inferred are `spoiler: true`. Each result is revealed locally, and the final
score is revealed separately. Local reveals reset on a new question.

### `GET /ask/suggest?q=…&hidden=true|false`

Typeahead. It never calls a model and is bounded and cached. `AskSuggestResponse`
has `games` (direct matches whose `href` goes straight to the game), `entities`,
and `questions`. When `hidden=true`, the server omits team-specific playoff
series suggestions and anything else that reveals results.

## 6. Fixtures

`src/services/ask/fixtures/responses/*.json` holds full `AskResponse`
documents, and `suggest/*.json` holds `AskSuggestResponse` documents. The UI
loads them from `@/services/ask/fixtures` (`ASK_RESPONSE_FIXTURES["clarification-which-jalen"]`).
Python validates each fixture and checks that it round-trips exactly. The test
also requires that every outcome and every intent is covered:

```
cd <repo root> && server/venv/bin/python -m pytest -q server/tests/ask
```

Fixtures cover:
- `answer-games-last-week` (includes an overtime game)
- `answer-player-stat`, `answer-team-stat`, `answer-stat-leaders`
- `answer-series-hidden` (teams supplied by the user)
- `answer-series-inferred` (participants inferred, with spoiler items, links, and suggestions)
- `answer-postseason-team`, `answer-postseason-league`
- `clarification-which-jalen`, `clarification-year-required`
- `unsupported-career-stats`
- `not-found-no-games`, `not-found-historical-record`
- `unavailable-service`, `unavailable-interpreter`
- `budget-exhausted`

Fixture numbers are illustrative UI data, not verified records. Do not use
them as evaluation labels.

## 7. File ownership

The shared files are frozen after this PR: `server/ask/models/**`,
`server/ask/protocols.py`, `src/services/ask/types.ts`, and
`src/services/ask/fixtures/**`. Change them only in a separate
coordinated contract PR that updates the Python models, the TS types, the
fixtures, and this document together. A child branch that needs a contract
change should open that PR instead of editing the files in place.

| Issue | Owns (creates/edits) |
| --- | --- |
| #200 candidate lookup | `server/ask/candidates/**` (lookup, alias loading, date parsing, player/team catalogs); `server/ask/data/**` (alias JSON, historical team names, player catalog snapshots); `server/tests/ask/test_candidates*.py`; `scripts/ask/measure_candidates.py`; `docs/ask-candidates.md` |
| #199 interpreters and evaluation | `server/ask/interpreters/**` (`jev.py`, `openai_responses.py`, `cascade.py`, prompts, closed-set builders); `server/ask/normalize.py` (`RequestNormalizer`); `server/ask/eval/**`; `server/tests/ask/fixtures/eval/**` (labeled seed/dev questions); `server/tests/ask/test_interpreters*.py`, `test_normalize*.py`, `test_cascade*.py`; `scripts/ask/evaluate.py`; `docs/ask-evaluation.md`; provider SDK dependency lines in `server/requirements.txt`, `requirements.txt`, `pyproject.toml`, and `uv.lock` |
| #201 backend pipeline | `server/ask/pipeline.py`, `server/ask/router.py` (`APIRouter` for `/ask` and `/ask/suggest`), `server/ask/resolvers/**` (games, boxscore, series, postseason calculators), `server/ask/links.py`, `server/ask/spoilers.py`, `server/ask/cache.py`, `server/ask/budget.py`, `server/ask/limits.py`, `server/ask/diagnostics.py`, `server/ask/config.py`, `server/ask/resolution.py` (tokens); a single `include_router` line in `server/main.py`; `server/tests/ask/test_pipeline*.py`, `test_resolvers*.py`, `test_router*.py`; the final rewrite of `docs/ask-search.md` |
| #205 UI | `src/components/ask/**`, `src/hooks/useAsk*.ts`, `src/services/ask/askService.ts` (fetch client), `src/services/ask/recentSearches.ts`, `src/services/ask/*.test.ts`; Ask entry points in `src/components/Header.tsx` and in design headers under `src/designs/**` (entry-point edits only); `docs/mockups/ask/**` |

Rules:

- `server/main.py` is touched only by #201, and only for the router include.
- Existing services (`server/services/**`, `server/utils/**`) are reused
  read-only. If one needs a change, make it in a separate small PR.
- Tests live under `server/tests/ask/` (a package), with each issue using its
  own file prefix. `server/tests/conftest.py` is not edited by child branches.
- `server/tests/fixtures/ask_seed.json` and `ask_heldout.json` on `main` are
  leftovers from the prototype and use its old interpretation schema. #199 owns
  auditing them for tuning exposure and replacing them. They must not be used
  as the unseen release set.
- Until #199 and #200 land, #201 can code against the protocols with fakes,
  and #205 can build against the fixtures.
