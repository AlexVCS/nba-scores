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
| Fixture validation | `server/tests/ask/test_contract_fixtures.py`, `server/tests/ask/test_contract_rules.py`, `src/services/ask/fixtures/links.test.ts` |

All contract models are strict (`extra="forbid"`) and shallowly frozen:
attributes cannot be reassigned, but nested lists are ordinary lists, so models
are not hashable. Cache keys use `common.canonical_json(model)` (JSON mode,
sorted keys, no whitespace), never `hash()`. Import from the submodules
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
| `boxscore_stat` | `BoxscoreStatRequest` | `scope` (`player`/`team`/`leaders`), `stat: StatSelection`, `game: GameSelector`; `player` required for player scope and only allowed there; `team` (or a team in `game.teams`) required for team scope; leaders exclude `NON_LEADER_STATS` |
| `playoff_series` | `PlayoffSeriesRequest` | `season`, plus one of: 2 teams; 1 team + round; `round=finals`; `round=conference_finals` + conference |
| `postseason_summary` | `PostseasonSummaryRequest` | `season`; `team` optional (`None` means league-wide) |

- `GameSelector` identifies exactly one game in one of three ways: `game_id`;
  `date` (with optional teams); or `season` + `game_number` + (`round` or two
  teams). A player and a date are enough. The resolver finds that player's
  game from dated records, never from current rosters. A question that names
  no game while the user views a boxscore ("who led in rebounds") uses
  `AskContext.game_id` directly in the normalizer; there is no game candidate
  field, and the interpretation item has `origin: "context"`.
- `StatSelection` is `stat` + `aggregation` (`total`/`per_game`). Stats include
  `stat_line` for a full line, which is not valid for leaders. Single-game
  requests must be `total`. A question that asks for an average across games is
  represented as `per_game` and does not validate. Normalization reports it as
  unsupported (`multi_game_average`) and never silently answers it as a total.
- Leaders have a ranking rule only for single-number stats. `stat_line` and
  the three percentages (`NON_LEADER_STATS`; percentages would need a
  qualification threshold) are rejected by the model, and normalization
  reports them as unsupported (`unsupported_leader_stat`) before any data
  call. Made/attempted stats (`field_goals`, `three_pointers`, `free_throws`)
  rank by made.
- `Season` is `"YYYY-YY"`, validated as consecutive years. A playoff year maps
  to the season that ends in it: "2024 Finals" is `2023-24`.
- `PlayoffRound` uses the modern names (`first_round`, `conference_semifinals`,
  `conference_finals`, `finals`). Resolvers map historical formats onto them.
- `AskContext` has a server-assigned `reference_time`, plus the page context
  (`route`, `view_date`, `game_id`, `playoff_season`). `reference_time` must
  be timezone-aware and is converted to America/New_York on validation
  (`NewYorkDateTime`), so `reference_time.date()` is the New York date:
  `2026-02-09T02:00:00Z` becomes Feb 8, 21:00 EST. `Interpretation.reference_time`
  uses the same type. Relative dates resolve against it. "Last week" is the
  preceding Monday–Sunday. The NY date belongs in relative-parse cache keys.
- `DateComponents` is date language broken into parts: `calendar_date`,
  `calendar_range`, or `relative`, where `relative` is one of `today`,
  `last_night`, `last_week`, `last_weekday`+`weekday`, `past_days`+`count`, and
  so on. `year=None` is kept as missing and leads to a `year_required`
  clarification. The year is never defaulted, including the date cookbook's
  default-year behavior.
- `count` accepts up to `MAX_RELATIVE_DAY_COUNT` (366), so "the past 10 days"
  is representable and normalization answers it with a `range_too_long`
  clarification. The seven-day limit is enforced by `DateRange` and
  normalization, not by `DateComponents`.
- The `relative` values are the forms that need the reference date *and* are
  worth keeping symbolic. Other relative phrases ("3 days ago", "last
  weekend", "next Friday", "early March") are intended to be resolved by
  lookup into `calendar_date`/`calendar_range` components with the year taken
  from `reference_time`, plus `resolved`. That is the intended representation;
  no new `relative` values are needed. Only a calendar date the user wrote
  without a year stays `year=None`.

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
- `needs_clarification`, with `clarify_field: ClarifyField` and `clarify_reason: ClarifyReason`
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
- Interpreter fields and candidate fields differ only in `teams` (interpreter,
  may select two) vs `team` (candidate set). `INTERPRETER_TO_CANDIDATE_FIELD`
  in `interpreter.py` is the mapping.

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
  is enabled, and the remaining budget and time. `CascadeDecision` is a union
  discriminated by `action`, and each action carries only its own data:
  `AcceptDecision`, `FallbackDecision` (`adapter`), `ExpandCandidatesDecision`
  (`field: CandidateField`, so `teams` becomes `team`), `ClarifyDecision`
  (`field: ClarifyField`, `clarify_reason`), `UnsupportedDecision`, and
  `FailDecision`. All carry a log-only `reason`. The single-provider
  configuration is a policy that never returns `fallback`. The fallback table
  in #199 is implemented here. Guessed parameters are never executed.
- `ClarifyField` (`common.py`) is the one clarification enum, used by
  `NormalizationResult`, `ClarifyDecision`, and the HTTP `Clarification`:
  `intent`, `stat_scope`, `stat`, `player`, `teams`, `date`, `season`, `round`,
  `game_number`. `teams` covers one team or a matchup. `aggregation` is never
  clarified, because `per_game` is unsupported.

## 5. HTTP: `POST /ask` (`response.py`, `types.ts`)

The request body is `AskQuery`:
- `question`: 1–300 characters, whitespace stripped
- `context`: an optional `ClientContext` (`route`, `view_date`, `game_id`, `playoff_season`)
- `resolution`: an optional opaque token from a clarification option. The
  token is server-issued, short-lived, and never trusted as parameters. #201
  chooses the encoding, for example a signed payload or a cache key. It
  refers to validated resolution state, which may be partial:
  - With a valid token the server makes zero model calls. If every required
    field is resolved, it executes the request. Otherwise it returns the next
    `needs_clarification`, whose options carry new tokens that include the
    earlier choices. Example: "How did Jalen do on March 3?" asks which Jalen
    first, then which year (`clarification-two-step-player` →
    `clarification-two-step-year`).
  - An expired or invalid token (bad signature, unknown, issued for a
    different question) is ignored, and `question` is handled as a new
    question through the normal pipeline, which may call a model. Every
    option's `question` is a standalone rewrite, so this is safe. It may lead
    back to the same clarification. A token longer than 512 characters fails
    request validation (422).

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
  - `games`: `days[]` → `GameResultItem { date, game: <scoreboard payload>, spoilers {score, status_text, series_text, labels}, links, spoiler }`,
    plus `total_games: Guarded<int>` and `hidden_note`. `date` is the New York
    date of `game.gameTimeUTC` and matches the `gameCode` date.
  - `boxscore_stat`: `game: GameContext`, whose `away`/`home` are `Guarded`
    and whose `final_score` is `Guarded` and revealed separately. Then,
    depending on scope, `player_line` (`values: Guarded<StatValue>[]`),
    `team_lines`, or `leaders: Guarded<LeaderRow[]>` (leaders scope only).
    `StatValue` has `display`, plus `made` and `attempted` for shooting stats.
  - `playoff_series`: `teams[2]`, where each row's team is guarded when the
    user did not name it, and seed, wins, and `won_series` are guarded. Also
    guarded `status`, `games_played`, `summary`, and `games`, because the
    game count reveals the series length.
  - `postseason_summary`: guarded `finish`, `record`, `series_won`, and
    `rounds` (team scope), and `champion`, `runner_up`, and `series` (league
    scope). The whole `rounds` list is guarded because its length reveals
    advancement. League `series` rows have two `teams` (each a team and its
    wins), a `status` (`not_started`/`in_progress`/`complete`), and
    `winner_team_id`, which is set only when complete, so unfinished series
    are described without asserting an outcome.
- `clarification` has `field` (`ClarifyField`), `reason`, `prompt`, `detail`,
  `hint`, and `options[]`. Each option has `label`, `sublabel`, `detail`, team
  and player IDs, a standalone rewritten `question`, and a `resolution` token.
- `notice` has `code`, `title`, `message`, `retryable`, `retry_after_seconds`,
  `unsupported_reason`, and `diagnostics_recorded`. When
  `diagnostics_recorded` is true, the UI can say that an anonymous note was kept.
- `links` are `VerifiedLink { kind, label, href, external, spoiler }`, built by
  Python from verified IDs. `VerifiedLink` is the only URL-bearing type:
  `PostseasonRoundRow.series_link` and `SuggestGame.link` use it too, so one
  allowlist applies everywhere.
  - Internal `href`s must match an allowlist: `/?date=`,
    `/games/{id}/boxscore[?date=]`, `/playoffs[?season=]`, and
    `/playoffs/{year}/{series slug}`. They are design-agnostic; the UI adds the
    active design prefix.
  - External links must start with `https://www.nba.com/`.

#### Series slugs

`/playoffs/{year}/{slug}` is resolved by `findSeriesBySlug` in
`src/utils/seriesSlug.ts`, using the bracket from `GET /playoffs`. `year` is
the season's end year (`2024-25` → `2025`). Python derives the slug from the
same enriched bracket, `enrich_playoff_bracket_response(season, series)` in
`server/services/playoffs.py`, which sets `bracketGroupId`, `bracketOrder`, and
`isFinals`:

```python
ROUND_SLUGS = {1: "first-round", 2: "semifinal", 3: "final"}

def slugify(value: str) -> str:  # same as seriesSlug.ts
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")

def series_slug(series: dict) -> str:
    if series["isFinals"]:
        return "the-finals"
    round_slug = ROUND_SLUGS.get(series["round"], f"round-{series['round']}")
    return f"{slugify(series['bracketGroupId'])}-{round_slug}-{series['bracketOrder'] + 1}"
```

Modern examples: `east-conference-first-round-1` … `-4`,
`west-conference-semifinal-2`, `east-conference-final-1`, `the-finals`.
Slugs are positional, so they do not name the teams. Do not use the
`series-{seriesKey}` alias, which contains team IDs. Team-based slugs such as
`finals-okc-ind` are not routes, and the allowlist rejects them.
`links.test.ts` checks that every fixture link matches a route in
`src/main.tsx` and resolves through the slug map.
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
`spoiler: true`, and interpretation items with `spoiler: true`. Each result is
revealed locally, and the final score is revealed separately. Local reveals
reset on a new question.

- Participants. Entities the user supplied are echoed with `spoiler: false`.
  In any postseason context, participants the server inferred are
  `spoiler: true` everywhere: the interpretation items (a `game`/`series`
  chip such as "OKC @ IND"), `GameContext.away`/`home`, series rows,
  clarification options, links whose destination shows them, and suggestions,
  including unsolicited ones ("Try one of these"). A suggestion that names a
  playoff matchup the user did not ask about is a spoiler.
- Whole units. When the shape of a value reveals a result, the whole unit is
  guarded, not only its parts:
  - `leaders` is one `Guarded` list, because a shared rank reveals a tie and
    the length reveals how many tied.
  - `rounds`/`series` (postseason) and `games` (series) are guarded lists.
  - A `GameResultItem` whose existence reveals a result has `spoiler: true`:
    a conditional playoff game (Games 5–7 of a best-of-seven), or a later
    round in a team-filtered search. While hidden the UI omits the whole
    item, and any day left empty. `total_games` is then guarded, and
    `hidden_note` holds neutral copy. The server decides `hidden_note` from
    the schedule and the question, never from which games were played.
  - The embedded scoreboard `game` is rendered only through `spoilers`:
    `score` (scores, winner), `status_text` ("Final/OT"), `series_text`
    ("NYK leads 2-1"), and `labels` (`gameLabel`, `gameSubLabel`,
    `seriesGameNumber`, `ifNecessary`; "Game 7" reveals series length and a
    round label can reveal advancement). Team names and tip-off time are
    schedule data, as on the scores page.
- Gated questions. If every possible outcome of a question reveals a result,
  the response carries `spoiler_gate {title, message}`. Examples: a
  conditional game ("game 7 of the 2024 Finals": an answer if it was played,
  `not_found` if not), and absence that reveals elimination ("Knicks games
  last week" during the playoffs). The server decides from the question and
  schedule, never from the outcome, and sends the same gate copy for an
  answer and for `not_found`. While hidden the UI renders only the gate copy,
  interpretation items with `spoiler: false` (which come from the question
  and must not differ by outcome), and a reveal control. It must not render,
  or change layout based on, `outcome`, `result`, `notice`, `links`, or
  `suggestions`. A gate is allowed only on `answer` and `not_found`.

### `GET /ask/suggest?q=…&hidden=true|false`

Typeahead. It never calls a model and is bounded and cached. `AskSuggestResponse`
has `games` (direct matches whose `link` goes straight to the game), `entities`,
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
- `answer-games-conditional` (possible Games 5–7 flagged, guarded count, `hidden_note`)
- `answer-player-stat`, `answer-team-stat`, `answer-stat-leaders` (inferred Finals participants guarded)
- `answer-stat-leaders-tied` (two leaders share rank 1)
- `answer-conditional-game-hidden` and `not-found-conditional-game-hidden`
  (Game 7 that was played and one that was not, with the same `spoiler_gate`;
  the second is the result-revealing-absence case)
- `answer-series-hidden` (teams supplied by the user)
- `answer-series-inferred` (participants inferred, with spoiler items, links, and suggestions)
- `answer-postseason-team`, `answer-postseason-league`, `answer-postseason-league-in-progress`
- `clarification-which-jalen`, `clarification-year-required`
- `clarification-two-step-player` → `clarification-two-step-year` (a token-backed partial resolution)
- `unsupported-career-stats`
- `not-found-no-games`, `not-found-historical-record`
- `unavailable-service`, `unavailable-interpreter`
- `budget-exhausted`

Fixture numbers are illustrative UI data, not verified records. Do not use
them as evaluation labels. Dates are still consistent: each game's `date`, its
day, its `gameCode`, its link `?date=`, and the New York date of `gameTimeUTC`
agree.

`test_contract_rules.py` also checks, across all fixtures and models: every
URL field is a `VerifiedLink`, and links reject off-allowlist targets. Postseason
participants are named by the user or guarded. Conditional games and leaders
are whole-unit spoilers. Gated outcomes share their hidden state. Dates agree.
Reference times normalize to New York across midnight and DST. Clarify and
expansion fields agree across layers. `canonical_json` is stable.
`src/services/ask/fixtures/links.test.ts` (Vitest, `pnpm test:run`) checks
that the links resolve.

## 7. File ownership

The shared files are frozen after this PR: `server/ask/models/**`,
`server/ask/protocols.py`, `src/services/ask/types.ts`,
`src/services/ask/fixtures/**`, and the contract tests
(`server/tests/ask/test_contract_*.py`). Change them only in a separate
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
