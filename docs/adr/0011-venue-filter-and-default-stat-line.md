# 11. Venue filter for game search; a full stat line when no stat is named

Date: 2026-09-29
Status: accepted

## Context

Calibration on exposed cases (ADR 0009, `docs/ask-evaluation.md`) left three
guesses. Two of them were label questions that needed a product decision:

- "What NBA games are on tonight in New York?" was labeled as all games, with no
  filter. Luna filtered to Knicks games instead.
- "How many did Nikola Jokic have on February 3, 2025?" was labeled as a stat
  clarification. Luna answered with Jokić's full stat line.

## Decision

1. **"In <city>" means games played there.** Game search gets an optional
   `location`: a city plus the teams whose home arena is in it. It returns only
   games whose home team is one of them. "Games in New York" means Knicks and
   Nets home games. It does not mean Knicks games, and it does not include Knicks
   road games.
2. **No stat named means the full stat line** for player and team boxscore
   questions. The normalizer already applied this rule; the label was wrong.
   Leaders questions still need a stat.

## Consequences

- Candidate lookup produces `location` candidates only when a known city follows
  "in" or "at". "Boston games" stays a team question, and "games in Boston" is a
  venue question.
- `location` is a new candidate and interpreter field (a Choice for Jev and Laya, a
  schema field for Luna), used by game search only.
- City-to-team mapping covers current franchises only. Historical venues, such as
  Seattle before 2008 or New Jersey before 2012, produce no location candidate.
- Labels `release-two-006` and `release-two-056` were changed to match. Both sets
  were already exposed, so no unseen evidence is affected.
- Candidate sets gain a field. That changes trace keys, so the calibration trace
  must be re-recorded.
