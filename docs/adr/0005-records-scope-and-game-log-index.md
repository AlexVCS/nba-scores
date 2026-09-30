# 5. Records scope and a precomputed game-log index

Date: 2026-09-29
Status: accepted

## Context

ADR 0004 adds a "career totals and records" family without bounding it. Some
record questions need only one fetch; others require scanning every game ever
played.

## Decision

The records family answers four shapes:

| Shape | Example | Data |
| --- | --- | --- |
| All-time leaders and rank | "Where does Curry rank in career 3s?" | stats.nba `AllTimeLeadersGrids`, live and cached |
| Player career and season highs | "Kobe's career high in points" | stats.nba player profile, live and cached |
| Counting-game records | "Most 50-point games" or "most triple-doubles in a season" | Game-log index |
| Team and franchise records | "Best record in Warriors history" or "longest win streak" | Game-log index plus stats.nba franchise history |

The **game-log index** is a local store (SQLite) of league-wide player and team
game logs from stats.nba, with roughly one call per season per log type, back to
1946-47.

- An offline job builds it. Completed seasons are frozen; the current season
  refreshes nightly.
- Tools query it locally and never scan live.
- Basketball-Reference is not used to fill the index; the fallback is for single
  facts only (ADR 0003).

## Consequences

- Answers must state their coverage. Historical box-score fields are incomplete:
  there are no three-pointers before 1979-80, and no steals, blocks, or
  offensive/defensive rebound splits before 1973-74. Records involving a field
  cover only the seasons that have it, and the answer says so.
- Answers from the index carry an "as of" date for the current season.
- The same index can serve team standings history and some season-leader
  questions, which reduces live traffic.
- Record questions include numbers ("50-point", "10 straight"). System One
  models can't extract numbers, so candidate lookup must extract numeric
  thresholds and offer them as Choice candidates.
- Record query shapes form a closed set of templates (stat, threshold,
  comparison, scope, ordering). A question that doesn't match a template is
  `unsupported`, not an ad hoc query.
- The first build makes a few hundred stats.nba calls. It must be throttled and
  resumable.
- The API runs on Railway, whose container filesystem is ephemeral. The index
  needs either a Railway volume, or to be built offline and shipped as an
  artifact with nightly deltas for the current season.
