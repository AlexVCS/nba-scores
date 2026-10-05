# Field-label brief for the third unseen Ask set

You will write per-field truth for 39 questions in the third unseen set. Your
labels become the reference for a field-level measurement. Treat this as an
annotation task: record what each question means, field by field. Do not
predict what any software would do.

The question set is still a draft. The template records the fixture's SHA-256
(`fixture_sha256`). If the fixture changes before it is frozen, the template is
regenerated and these labels must be checked against the new version.

## Isolation

Start from a fresh context. Do not rely on anything from earlier conversations
about this project.

You may read only:

- This brief.
- The template, `docs/verification/ask-unseen-three-field-label-template.json`.
- The question fixture, `server/tests/ask/fixtures/eval/unseen-three-draft.json`.
  This includes every case's expected action, request, clarification or
  unsupported reason, tags and rationale.
- The contract schemas: `server/ask/models/common.py`, `server/ask/models/request.py`
  and `server/ask/models/interpreter.py`.
- Reference data: `server/ask/data/player_catalog.json` and
  `server/ask/data/franchise_history.json`.

You must not read, run or search:

- Anything else under `docs/`, including the set's label notes, evaluation
  reports, journals (`*.jsonl`), audits, manifests, verification notes, reviews,
  ADRs, earlier label files and mockups.
- Anything else under `server/ask/`, including interpreters, prompts, tool
  descriptions, candidate lookup, aliases (`aliases.json`), the city table, the
  normalizer, measure and season-scope rules, resolvers, the pipeline and
  `server/ask/eval/`.
- `scripts/`, including the scorer, and every test file except the fixture above.
- Git history (`git log`, `git show`, `git diff`, `git blame`), issue trackers
  (`.beads/`, `bd`, GitHub issues) and pull requests.
- The web, for anything about this project. General NBA knowledge is fine.
  Every player and team ID must come from the reference files.

Do not run any Ask code, lookup or model. You may use `jq` or a short script to
read the allowed files and to check that your JSON parses.

## Deliverable

Copy the template to `docs/verification/ask-unseen-three-field-labels.json` and
fill it in. Do not change `schema`, `fixture`, `fixture_sha256`,
`fields_by_intent`, `field_conditions`, `not_labeled`, `case_id`, `question`,
`reference_time`, `context` or `label_scope`. In `labeler`, give your name or
agent ID, the time you finished, and a one-paragraph isolation statement that
lists what you read. Do not edit any other file.

The template has two kinds of cases.

- `"label_scope": "all"` (34 cases): fill `intent`, `scored_intent` and every
  field that `fields_by_intent` lists for your `scored_intent`, subject to
  `field_conditions` (see `target_team` below).
- `"label_scope": "player"` (5 cases): the intent is fixed (`fixed_intent`,
  always `boxscore_stat` with team or leaders scope). Leave `intent` and
  `scored_intent` as `null` and fill only `fields.player`.

Use `notes` for anything a reviewer should know, especially disagreement with
the fixture's expected label or rationale.

## Intent

`intent` is the request type the question asks for:

- One of the eight request types in `request.py`: `game_search`,
  `boxscore_stat`, `playoff_series`, `postseason_summary`,
  `player_season_stats`, `team_records`, `season_leaders` or `career_stats`.
- `unsupported:<reason>` for a request outside those types, where `<reason>` is
  one of the `UnsupportedReason` values in `interpreter.py`, for example
  `unsupported:prediction`. Do not use the reasons marked "historical reports
  only" (`season_stats`, `regular_season_record`, `standings`, `career_stats`,
  `season_leaders`). Those questions now have request types.

A clarification case still has an intent. For example, a box-score question
that doesn't name its game is still `boxscore_stat`, and a leaders question
without a season is still `season_leaders`.

`scored_intent` names the intent whose fields you label: one of the eight
request types, or `unsupported`. If your intent is `unsupported:<reason>`, use
`"scored_intent": "unsupported"` and `"fields": {}`.

Two situations call for an `any_of` intent:

- **A request type that rejects a parameter.** Some questions fit a request
  type but ask for something that type rejects: an average across several
  games, a home/away or other split, a rookie or team filter, leaders by a
  statistic with no ranking rule, an all-time per-game list, or regular season
  and playoffs combined. If reading it as that type is defensible, use an
  `any_of` intent listing the type and the unsupported reason, such as
  `boxscore_stat` and `unsupported:multi_game_average`. Set `scored_intent` to
  the supported type and label its fields as the question states them. If no
  request type fits, label only the unsupported intent.
- **Two request types.** When the question could mean either of two types (for
  example, a player's career total or one season's total), use an `any_of`
  intent listing both. Set `scored_intent` to the one you consider primary,
  label its fields, and explain the choice in `notes`.

## Fields

Each field records what the question, and any page context it relies on, says.
It does not record what a final request would keep.

`fields_by_intent` lists the fields for each intent. Two things are not
labeled at all:

- `aggregation` (season totals or per game) for `player_season_stats`,
  `season_leaders` and `career_stats`. It is still labeled for `boxscore_stat`.
- The size of a "top N" list and the career view (a player's totals, the
  all-time list, or a player's rank). They are not fields.

| Field | Intents | Meaning | Value format |
| --- | --- | --- | --- |
| `stat_scope` | boxscore_stat | Whose statistic: one player (`player`), one team's totals (`team`), or who led the game (`leaders`) | string |
| `stat` | boxscore_stat, player_season_stats, season_leaders, career_stats | The statistic asked for. See the rules below. | a `Stat` value from `common.py` |
| `aggregation` | boxscore_stat | `total` for one game, or `per_game` for an average across games | string |
| `season_type` | player_season_stats, team_records, season_leaders, career_stats | `playoffs` when the question asks about the playoffs or postseason; `regular_season` when it says regular season | a `SeasonType` value |
| `standings_scope` | team_records | `league` for league-wide standings, `east` or `west` for conference standings | a `StandingsScope` value |
| `player` | boxscore_stat, player_season_stats, career_stats | The NBA player the question names or refers to, whatever the player's role in the question | `player_id` integer from `player_catalog.json` |
| `teams` | all but season_leaders and career_stats | Every NBA franchise the question names or clearly refers to, whether by city, nickname, abbreviation, historical name or description, opponents included | list of one or two franchise `team_id` integers from `franchise_history.json` |
| `target_team` | boxscore_stat with team scope | The one team whose own statistics the question asks for | one franchise `team_id` integer |
| `date` | game_search, boxscore_stat | The calendar date or date range of the games, resolved in America/New_York | `{"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}`, 1 to 7 days |
| `season` | all but game_search and career_stats | A season or playoff year the question states, such as `2016 Finals` or `2015-16` | `"2015-16"` |
| `round` | boxscore_stat, playoff_series | A playoff round the question names. Give a conference only if the round wording names it, such as `Western Conference Finals`. | `{"round": "conference_finals", "conference": "west"}`; conference may be `null` |
| `game_number` | boxscore_stat | A numbered game of a series, such as `Game 7` | integer 1 to 7 |
| `location` | game_search | A city where games are played, as in "games played in Boston" | plain city name, such as `Brooklyn` or `Salt Lake City` |

Further rules:

- **`stat`.** For `boxscore_stat`, use `stat_line` for a whole line, or when
  player or team scope names no statistic; with `leaders` scope and no
  statistic, use absent. For `player_season_stats`, use `stat_line` when the
  question asks for a player's stats without naming one. For `career_stats`,
  use `stat_line` when a named player's career is asked without a statistic,
  and absent when an all-time list names no statistic. For `season_leaders`,
  a question with no statistic has an absent `stat`. "Points per game",
  "scoring average" and "scoring title" are all `points`; "threes" are
  `three_pointers`; a shooting percentage is its percentage stat.
- **`season_type`.** Absent when the question says neither playoffs nor
  regular season. For `team_records`, a question about one team's record or
  standings normally leaves it absent.
- **`standings_scope`.** Absent when the question asks for one team's record.
  `league` when it asks for standings without a conference.
- **`target_team`.** Only for `boxscore_stat` when your `stat_scope` label is
  `team`; omit the field otherwise, as `field_conditions` says. `teams` still
  lists every team named, the target included. With one team named, the target
  is that team. With two named and the question not saying whose statistics it
  wants, `target_team` is ambiguous with both IDs.
- **Relative dates.** Resolve them against `reference_time` using the
  `RelativeDate` definitions in `common.py`. Weeks run Monday to Sunday.
- **Seasons.** A playoff year (`2016 Finals`, `the 1990 playoffs`) is the season
  ending that year (`2015-16`). A bare year for something that spans a season,
  such as a season statistic or a record, could be either of the two seasons
  that include it, so it is ambiguous with both seasons as alternatives unless
  the question settles it. "This season" and "last season" resolve against
  `reference_time`; an NBA season runs from October to June. In the offseason,
  if "this season" could mean the season just finished or the coming one, label
  it ambiguous.
- **Season versus date.** Label `season` only when the question states a season
  or playoff year. Do not derive one from a calendar date. When the question
  gives both, label both.
- **Team names versus venues.** A city used as a team name, or a former home
  used to describe a franchise (for example, "the team that left Seattle"),
  refers to a team. It is not a `location`. An arena name ("at the Barclays
  Center") is a `location`; label its city.
- **Precedent.** The fixture's 140 accept labels show how the fixture author
  mapped wording and page context to request fields. Follow the same
  conventions.

## Page context

`context` may hold `view_date` (the scores page date), `playoff_season` (the
playoffs page season) or `game_id` (the open box score).

- If the question relies on the page ("this date", "these playoffs", "here"),
  label the value the page supplies for `date` or `season`.
- If the question states its own value, label that value, even when the page
  shows something else.
- If the question doesn't refer to the page, ignore the page context.
- `game_id` is not a field. For "this game" or "here" on a box-score page,
  label `date`, `season`, `round` and `game_number` as absent unless the
  question states them.

## Status of each field

Each field takes exactly one of these objects.

| Status | Use when | JSON |
| --- | --- | --- |
| `value` | The question specifies it | `{"status": "value", "value": ...}` |
| `absent` | The question does not specify it, even if the request needs it | `{"status": "absent"}` |
| `ambiguous` | A mention could refer to two or more distinct entities or values, and neither the question nor the page settles it | `{"status": "ambiguous", "alternatives": [...]}` with at least two values in the field's format; for `teams`, each alternative is one `team_id` |
| `unresolved` | `date` only: the date is stated without a year (`year_required`), or the range is longer than seven days (`range_too_long`) | `{"status": "unresolved", "reason": "year_required"}` |
| `unlisted` | `player`, `teams`, `target_team` or `location` only: the question names a specific entity that is not in the reference data | `{"status": "unlisted"}` |

Missing is not the same as ambiguous. A question that names no season has an
absent season. A surname shared by several players whose careers overlap the
question's time frame is ambiguous. List those `player_id` values as
alternatives. If only one of them played in that time frame, it is a value. A
city with two franchises in the question's time frame ("LA", "New York") is an
ambiguous `teams` value listing both.

When two labels are genuinely defensible, use
`{"any_of": [<label>, <label>], "note": "why both are defensible"}`. Use this
rarely. It makes the measurement more lenient, and the scorer reports each use.

## Consistency with the fixture

Your field labels should agree with each case's expected action. A case
expecting clarification of `season` for reason `missing` should normally have an
absent `season`. A case expecting clarification for reason `ambiguous` should
normally have an ambiguous field, and a clarification of `intent` should
normally have an `any_of` intent. Two exceptions:

- A question that names two teams but needs one has a two-team `teams` value,
  not an ambiguous one.
- A clarification of `aggregation` for `season_leaders` has no field to label;
  it is decided from the question text.

The fixture's rationale explains each case. If you disagree, label what you
believe and explain in `notes`. The scorer reports these disagreements for
review.

## Examples (synthetic, not from the set)

Question: "How many blocks did Walker have in Game 2 of the 1978 Finals?"
Suppose two players named Walker in the catalog both played in 1977-78. Then:

```json
{
  "intent": {"status": "value", "value": "boxscore_stat"},
  "scored_intent": "boxscore_stat",
  "fields": {
    "stat_scope": {"status": "value", "value": "player"},
    "stat": {"status": "value", "value": "blocks"},
    "aggregation": {"status": "value", "value": "total"},
    "player": {"status": "ambiguous", "alternatives": [11111, 22222]},
    "teams": {"status": "absent"},
    "date": {"status": "absent"},
    "season": {"status": "value", "value": "1977-78"},
    "round": {"status": "value", "value": {"round": "finals", "conference": null}},
    "game_number": {"status": "value", "value": 2}
  }
}
```

Question: "Walker's playoff assists per game against everyone but Boston, 1979"
(a filter the request type cannot represent; the season is stated as a playoff
year, and one Walker played then):

```json
{
  "intent": {"any_of": [
    {"status": "value", "value": "player_season_stats"},
    {"status": "value", "value": "unsupported:other"}
  ], "note": "a player season question with an opponent filter the request type rejects"},
  "scored_intent": "player_season_stats",
  "fields": {
    "stat": {"status": "value", "value": "assists"},
    "season_type": {"status": "value", "value": "playoffs"},
    "player": {"status": "value", "value": 11111},
    "teams": {"status": "value", "value": [1610612738]},
    "season": {"status": "value", "value": "1978-79"}
  }
}
```

## Before you hand off

- Every `"all"` case has an `intent`, a `scored_intent` that is one of the
  intent values you labeled (or `unsupported`), and exactly the fields listed
  for that intent: `target_team` only for a team-scope `boxscore_stat`, and no
  `aggregation` for `player_season_stats`, `season_leaders` or `career_stats`.
- Every `"player"` case has only `fields.player`.
- Every ID appears in the reference files. Seasons use `YYYY-YY`, and dates are
  ISO ranges of no more than seven days.
- Every `any_of` has a note.
- The file parses as JSON. You did not run or read the scorer.
