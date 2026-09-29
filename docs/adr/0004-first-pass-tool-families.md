# 4. First-pass tool families

Date: 2026-09-29
Status: accepted (the scope of "records" is refined in a later ADR)

## Context

Ask currently supports four intents: `game_search`, `boxscore_stat`,
`playoff_series`, and `postseason_summary`. Users have asked questions outside
that scope, such as the Thunder's regular-season record, which Ask reports as
unsupported.

## Decision

The first pass adds four tool families to the tool registry:

| Family | Example | Primary source (ADR 0003) |
| --- | --- | --- |
| Player season stats | "Jokić's rebounds per game in 2023-24" | stats.nba player career/season stats |
| Season leaders | "Who led the league in assists in 2019-20?" | stats.nba league leaders |
| Career totals and records | "LeBron's career points" | stats.nba career totals |
| Team records and standings | "Celtics' record in 2007-08" | stats.nba standings, team game logs |

The four existing intents become tools in the same registry. The router then
chooses from eight tools, plus `unsupported`.

## Consequences

- Each family needs its own result type, answer template, spoiler rules,
  evaluation cases, and candidate-lookup support. Season-scoped families need a
  season candidate, which the lookup already produces.
- Season leaders must define qualification thresholds, ties, regular season vs
  playoffs, and per-game vs total before the tool is enabled. This replaces the
  #189 "season leaders" follow-up.
- The removed `unsupported_reason` for regular-season team records must be
  retired from prompts and closed sets when the team-records tool ships.
- Open-ended "records" questions have no fixed shape, so their scope must be
  bounded before implementation.
