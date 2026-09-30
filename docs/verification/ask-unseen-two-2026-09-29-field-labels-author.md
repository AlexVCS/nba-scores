# Authorship note: field labels for the second unseen Ask set

Labeler: claude-opus-5-5 (independent field-label subagent), 2026-09-29.
Output: `docs/verification/ask-unseen-two-2026-09-29-field-labels.json`.

## Files opened

- `docs/verification/ask-unseen-two-2026-09-29-field-label-brief.md`
- `docs/verification/ask-unseen-two-2026-09-29-field-labels.template.json`
- `server/tests/ask/fixtures/eval/unseen-two-2026-09-29.json`
- `server/ask/models/common.py`
- `server/ask/models/request.py`
- `server/ask/models/interpreter.py`
- `server/ask/data/player_catalog.json`
- `server/ask/data/franchise_history.json`
- `/private/tmp/ask-unseen-two-city-reference.json` was checked with `ls` and does
  not exist. No case needed a `location` value.

## Isolation

I followed the brief's isolation rules. I read nothing else under `docs/` or
`server/ask/`. I didn't open scripts, the scorer or any other test file. I didn't
use git history commands, beads or pull requests. I didn't search the repo and
didn't run any Ask code, lookup, model or evaluation. I used short Python scripts
only to read the allowed files, to look up IDs in the two reference files and to
check that my output parses and matches the template.

## Hard or debatable cases

- `unseen-two-postseason_summary-22` ("Boston or Miami ... not decided"): I
  labeled `teams` as a two-team value, following the brief's exception for
  questions that name two teams but need one. The wording is a disjunction, so an
  ambiguous label would also be defensible.
- `unseen-two-game_search-22` ("New York or Brooklyn team"): I labeled `teams` as
  ambiguous [Knicks, Nets]. It is not a two-team value, because in game_search
  two teams means a matchup, and the exception covers only requests that need one
  team.
- `unseen-two-playoff_series-25` (LeBron's per-game average, 2016 Finals): the
  intent is `any_of` [`boxscore_stat`, `unsupported:multi_game_average`] and
  `aggregation` is `per_game`. It is not playoff_series, even though it says
  "series".
- `unseen-two-boxscore_stat-12` to `-23` (surname or first name only, December 12,
  2018): the alternatives list every catalog player whose career span includes
  2018-19. That includes suffixed surnames (Marcus Morris Sr., Robert Williams
  III, Troy Brown Jr., Derrick Jones Jr.). The fixture rationales name only two or
  three players, but all 12 cases agree with the ambiguous clarification. The
  catalog stores no team or per-game data, so a listed player may not have played
  that day.
- `unseen-two-boxscore_stat-23` ("Chris"): I included only catalog first names
  that are exactly "Chris" (Paul, Boucher, Chiozza) and excluded Christian Wood.
- The Los Angeles cases (`game_search-21`, `playoff_series-22`,
  `postseason_summary-21`): I labeled `teams` as ambiguous [Lakers, Clippers],
  with `location` absent where that field applies, because "the Los Angeles team"
  refers to a team, not a venue.

I found no case where my labels disagree with the fixture's expected action.
