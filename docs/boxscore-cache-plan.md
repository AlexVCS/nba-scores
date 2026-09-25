## Problem

The current boxscore route calls `fetch_boxscoretraditional()` and then stats.nba.com on every request. There is no shared server-side boxscore cache. Schedule and playoff services have separate module-level dictionaries, but no reusable bounded cache with request coalescing.

Add shared caching for boxscore and authoritative game metadata. This reduces repeated upstream requests for existing boxscore views and provides reusable player/team/date/status context for #187.

## Delivery boundary

Land this work as a standalone PR with its own review, freshness checks and rollback. It can proceed alongside #187's video verification and does not depend on that gate. #187's playlist implementation will depend on this cached service.

Preserve the existing public boxscore and summary response contracts, historical fallback behavior and error conventions. Do not add `statVideoEligible` or video-specific behavior here.

## Implementation

- [ ] Add a small, bounded, thread-safe in-memory cache utility with per-entry expiration and coalescing of identical requests already in flight.
- [ ] Use explicit capacity limits and eviction for each cache. Use monotonic time for expiration.
- [ ] Route existing boxscore retrieval and future playlist context resolution through the same cached service, keyed by validated game ID.
- [ ] Cache authoritative summary metadata containing game date and status. Retain these fields internally during normalization; the current normalized summary drops the game date.
- [ ] Reuse the same cached summary retrieval in the existing summary route where it needs that upstream data. Avoid adding full linescore-repair work merely to retrieve date/status.
- [ ] Expose an internal game-context interface with player/team membership and authoritative date/status. The video feature will derive its season/type eligibility separately.
- [ ] Preserve live-score freshness, historical fallback behavior and upstream timeout/error handling.
- [ ] Do not cache upstream exceptions or malformed responses as successful results. Release and clean up in-flight entries on both success and failure so later requests can retry.
- [ ] Prevent callers from mutating shared cache entries when adding response-specific fields.

### Initial freshness policy

| Data | Lifetime |
| --- | ---: |
| Live or scheduled game | 15 seconds |
| Completed game whose authoritative game datetime is within the last 72 hours | 15 minutes |
| Older completed game | 24 hours |
| Missing, uncertain or stale status/date metadata | 15 seconds |

Choose the lifetime at insertion using freshly retrieved authoritative status and game date. Do not use stale cached status to promote a new boxscore entry to a long lifetime. If fresh status cannot be established, use the short lifetime without masking upstream errors. Cache hits never renew expiration.

A live entry can remain stale for its remaining 15-second lifetime after a game ends. It must never receive the completed-game lifetime while still classified as live or scheduled. Date/status classification should use timezone-aware values and conservative handling of missing dates.

This utility operates per process. It does not coalesce across workers or replicas and is cleared by process restarts. Cross-process caching and migration of the schedule/playoff caches are separate work.

## Acceptance criteria

- [ ] Repeated boxscore requests within the lifetime reuse cached results without changing the public response contract.
- [ ] Concurrent requests for the same key share one in-flight lookup within a process; different keys do not serialize behind one upstream request.
- [ ] Boxscore and summary consumers reuse cached retrieval instead of introducing duplicate per-consumer caches.
- [ ] Expired entries refresh; capacity limits prevent unbounded retained entries, including completed in-flight bookkeeping.
- [ ] Tests cover scheduled-to-live and live-to-final transitions, insertion-time lifetime selection, stale/unknown metadata and reads that do not extend expiration.
- [ ] Tests cover coalescing, failure cleanup/retry, eviction, mutation isolation and reuse across callers/routes.
- [ ] Existing boxscore/summary behavior, historical fallbacks and error handling remain covered by relevant regression tests.
- [ ] Existing lint, build and relevant backend tests pass.

## Estimate

Allow 0.5–1 engineering day for the cache utility, game-context integration and focused tests. This is separate from #187's video implementation and verification estimates.
