# 3. Data sources: stats.nba.com primary, Basketball-Reference fallback

Date: 2026-09-29
Status: accepted

## Context

Ask's tools (ADR 0001) need NBA data from websites. The server already uses
`nba_api` (stats.nba.com), Basketball-Reference, and Wikipedia.

## Decision

- **Primary:** stats.nba.com through `nba_api`. Every tool tries it first.
- **Fallback:** Basketball-Reference. A tool uses it only when stats.nba.com
  can't supply the fact: the request fails, times out, or is blocked, or the fact
  isn't covered (for example, pre-1996–97 boxscore detail).
- **Excluded:** Wikipedia, ESPN, and other sources. Ask doesn't answer from them.

## Consequences

- Each tool declares which sources it has, and each answer records the source it
  actually used. The UI's source link names that site.
- Basketball-Reference access needs a shared, process-wide rate limiter that stays
  well under Sports Reference's 20 requests per minute. It also needs long-lived
  caches for completed seasons and games, and a descriptive User-Agent. Its terms
  restrict automated use, so fallback traffic should stay low and be monitored.
- stats.nba.com needs retries, timeouts, and the browser-like headers `nba_api`
  already sets. It sometimes blocks cloud IPs, so production must confirm access
  from its host.
- The two sources can disagree (stat corrections, older records). A fallback
  answer comes from one source only; Ask never merges values across sources.
- This drops Wikipedia from the #189 "glossary and Wikipedia reference answers"
  follow-up. Glossary definitions still work because they need no fetch.
