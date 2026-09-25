# Natural-language search plan

Goal: a search box where a fan types a question ("Who led the Celtics in scoring in game 4 of the 2024 Finals?", "What happened on Feb 5 2026?") and gets a short answer plus links to the matching game, boxscore, series, or bracket page.

Constraint: cheap to run and cheap to build. No new database, no vector index. Claude answers by calling the data functions the backend already has.

## Approach

One new FastAPI endpoint, `POST /ask`, runs a small tool-use loop with the Anthropic Python SDK. The tools are thin wrappers over existing service functions, so the model never scrapes or guesses. The frontend adds a search input and renders the answer with links to existing routes.

Why tool use and not RAG: the data is already structured and cached in `server/services`. Fetching on demand is cheaper and always current. Embeddings would cost money up front and go stale.

## Backend

New file `server/services/ask.py` plus one route in `server/main.py`.

Tools (all `strict: true`, small JSON schemas):

| Tool | Wraps | Purpose |
|---|---|---|
| `get_games_on_date(date)` | scoreboard fetch in `nba_stats_client` | list games, ids, scores, status for a day |
| `get_boxscore(game_id)` | `fetch_boxscoretraditional` | player and team stats |
| `get_game_summary(game_id)` | `fetch_game_summary` | line score and period breakdown |
| `get_playoff_bracket(season)` | `get_playoff_games_and_series` | series, rounds, results, game ids |
| `find_games(team, start_date, end_date)` | `nba_schedule` helpers | resolve "Lakers last week" to game ids |

Model call:

- Model: `claude-opus-5` with `output_config.effort` at `low`. Measure first. If per-query cost is still too high, switch to `claude-sonnet-5`. Do not build a multi-model cascade.
- Single-turn only. No chat history sent, so no context growth.
- Loop capped at 4 tool calls and a 20 second wall clock. Return a friendly "couldn't find that" on cap.
- System prompt includes today's date and the current season so relative dates resolve. Put the date in the last user turn, not the system prompt, so the cached prefix stays stable.
- Prompt caching: one `cache_control` breakpoint after the tool definitions and system prompt. Everything before it is frozen.
- Structured output for the final answer: `{answer: string, links: [{label, path}]}` where `path` is a frontend route such as `/games/{id}/boxscore` or `/playoffs/{year}/{seriesSlug}`. The model only builds paths from ids it received in tool results.
- Set `max_tokens` around 1024. Answers are short by design.

Guardrails:

- Rate limit: 10 requests per minute per IP and a daily org cap in the Anthropic console. A hard daily spend cap protects against abuse.
- Reject questions over 300 characters.
- Log `response.usage` per request to a plain log line so cost is visible from day one.
- API key from the `ANTHROPIC_API_KEY` environment variable on Railway. Never shipped to the browser.

## Frontend

- `askQuestion(question)` in `src/services/nbaService.ts`.
- A search input on the scores page header or a new `/ask` route. Enter submits, results appear below with the answer and link chips. Loading and error states only, no streaming needed for answers this short.
- Spoiler safety: the answer reveals scores by definition. Show the answer behind the existing spoiler toggle state. If spoilers are hidden, blur the answer with a "Reveal" button, matching the current game card behaviour.
- Keep the design-neutral styling so it slots into whichever design variant wins.

## Cost estimate

Per query, assuming a cached 2K token prefix, about 4K tokens of tool results, and a 300 token answer:

| Model | Approximate cost per query |
|---|---|
| Opus 5, effort low | $0.03 |
| Sonnet 5 | $0.012 |
| Haiku 4.5 | $0.006 |

At 200 queries a day, Opus 5 is roughly $6 a day and Sonnet 5 roughly $2.50. The daily spend cap in the console makes the worst case bounded.

## Build order

1. Backend endpoint with two tools (`get_games_on_date`, `get_boxscore`). Test with curl.
2. Add playoff and schedule tools. Write a 15 question eval file in `server/tests` with expected game ids or series slugs, and check the returned links rather than the prose.
3. Rate limiting, usage logging, spend cap.
4. Frontend input and result card with spoiler gating.
5. Measure usage from step 3 logs. Decide whether to move to Sonnet 5.

Estimated effort: two to three days.

## Out of scope for v1

- Multi-turn follow-up questions.
- Player career or season-aggregate stats. The current services are game-scoped, so questions like "Jokic's season average" would need new data sources.
- Streaming responses.
