# Cache scoreboard and game-day lookups with status-aware freshness

## Problem

The scoreboard route (`GET /?date=`) calls `fetch_scoreboard_v3()` and then stats.nba.com on every request. There is no server-side cache at all, so every scores page load, refetch and back-navigation for the same date is a fresh upstream call with a 10-second timeout and two retries. Historical dates never change and are refetched identically.

The game-days route (`GET /api/game-days`) is backed by a module-level dictionary in `nba_schedule.py` that caches the season's date set for 6 hours. It is unbounded, uses wall-clock time rather than monotonic time, has no request coalescing, and caches the `LeagueGameLog` fallback result (completed games only) for the full 6 hours as if it were the complete schedule.

Move both routes onto the shared bounded cache utility from #190 and give each a freshness policy based on what the data actually is.

## Delivery boundary

Depends on the cache utility from #190. Land as a standalone PR after #190 merges, with its own review and rollback.

Preserve the existing scoreboard and game-days response contracts, including the `boxscoreAvailable` enrichment on each game, the default-to-today behaviour when no date is supplied, and current upstream error conventions (503 unavailable, 502 bad response).

Cross-process caching, HTTP `Cache-Control` headers and the playoff caches are separate work.

## Implementation

### Scoreboard

- [ ] Resolve the target date before keying the cache. A request with no `date` must hit the same entry as an explicit request for today's date.
- [ ] Route `fetch_scoreboard_v3()` through the shared cache, keyed by validated `YYYY-MM-DD` date.
- [ ] Cache the raw upstream scoreboard and apply `add_boxscore_availability_to_scoreboard()` on a copy at response time, so callers never mutate the shared entry.
- [ ] Choose the lifetime at insertion from the game statuses in the freshly fetched response, not from any previously cached entry.
- [ ] Do not cache upstream exceptions or malformed responses. Release in-flight entries on failure so later requests retry.

### Game days

- [ ] Replace the `_cache` dictionary in `nba_schedule.py` with the shared utility, keyed by season string.
- [ ] Keep the existing season-blob approach: cache the full date set per season and derive the month view from it. Month requests must not create per-month upstream calls.
- [ ] Give the `LeagueGameLog` fallback result a short lifetime so an incomplete schedule is retried soon rather than served for 6 hours. Tag the entry with its source so tests can assert this.
- [ ] Use monotonic time for expiration and an explicit capacity limit. The realistic key space is small (one entry per season), but the limit should still exist.

### Freshness policy

Scoreboard, chosen from the statuses in the fetched response:

| Data | Lifetime |
| --- | ---: |
| Any game in progress (status 2) | 15 seconds |
| All games scheduled and none started (status 1), or empty game list for today or a future date | 60 seconds |
| All games final (status 3) and the date is within the last 72 hours | 15 minutes |
| All games final and the date is older than 72 hours | 24 hours |
| Empty game list for a past date | 24 hours |
| Missing, unknown or mixed-unparseable statuses | 15 seconds |

Game days, chosen from the season and the source:

| Data | Lifetime |
| --- | ---: |
| Current season, from `ScheduleLeagueV2` | 6 hours |
| Current season, from `LeagueGameLog` fallback | 5 minutes |
| Past season, from `ScheduleLeagueV2` | 7 days |
| Past season, from `LeagueGameLog` fallback | 1 hour |

"Current season" means the season that `get_nba_season()` returns for today. Date comparisons use timezone-aware values. Cache hits never renew expiration.

A scoreboard entry classified as live can remain stale for its remaining 15 seconds after the last game ends. It must never be promoted to a completed-game lifetime while any game is still in progress. Postponed games change status without a new date, which is why "all scheduled" and "empty for today" stay at 60 seconds rather than longer.

## Acceptance criteria

- [ ] Repeated scoreboard requests for the same date within the lifetime reuse the cached result and return an identical response body, including `boxscoreAvailable`.
- [ ] A request with no `date` and a request for today's explicit date share one cache entry and one in-flight upstream call.
- [ ] Concurrent requests for the same date coalesce into one upstream call within a process; different dates do not serialize behind each other.
- [ ] Insertion-time lifetime selection is covered by tests for: all live, mixed live and final, all scheduled, all final within 72 hours, all final older than 72 hours, empty past date, empty today, and unparseable status.
- [ ] Tests cover live-to-final transition: an entry inserted while live expires in 15 seconds and the next fetch receives the completed-game lifetime.
- [ ] Game-days tests cover: month view derived from a cached season blob without extra upstream calls, fallback-source entries expiring on the short lifetime, and past seasons on the long lifetime.
- [ ] Tests cover that mutating a returned scoreboard response does not alter the cached entry.
- [ ] Tests cover failure cleanup and retry, eviction at capacity, and reads that do not extend expiration.
- [ ] Existing scoreboard, game-days and upstream error handling remain covered by regression tests.
- [ ] Existing lint, build and relevant backend tests pass.

## Estimate

Allow 0.5 engineering day once #190 has landed. Most of the work is lifetime classification and tests; the cache utility is reused as-is.
