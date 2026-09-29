# 6. Asking is consent: Ask shows answers immediately

Date: 2026-09-29
Status: accepted. This supersedes #189's "results start hidden" requirement for Ask.

## Context

#189 required every Ask result to start hidden and respect the global spoiler
preference, including historical results such as a 2016 Finals score. The new tool
families (ADR 0004) mostly return aggregates. We first considered hiding only
values that depend on games within the last 30 days. We then concluded that
answering is the whole point of Ask: a user who types a question wants the answer.

## Decision

Ask shows every answer immediately, whatever its age and whatever the global
spoiler preference. Submitting a question counts as consent to see its answer.

The global preference still governs everything the user did not explicitly ask
for:

- Scores, boxscore, and playoff pages outside Ask.
- Ask suggestions, typeahead, and example questions.
- Clarification options: "Which game?" choices must not reveal scores, winners,
  or series results when the preference hides results.
- Answers the user didn't request, such as a follow-up link card that would
  reveal another game's result.

## Consequences

- Removes Ask's per-result reveal controls, the local-reveal reset logic, and the
  "protected values absent from the DOM" tests for Ask answers. This is a large
  simplification of the Ask UI.
- Recent-history entries may store answer summaries, since the answers were
  requested. History is still local and clearable.
- The consent boundary moves to *submission*. Answers must never be prefetched or
  rendered while the user is still typing.
- The Ask entry point should say that answers show immediately, so users who
  avoid spoilers aren't surprised.
- Considered and rejected: a 30-day recency window, and keeping game results
  hidden for replays.
