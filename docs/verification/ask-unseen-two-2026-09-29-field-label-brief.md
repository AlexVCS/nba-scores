# Field-label brief for the second unseen Ask set, September 29, 2026

You will write per-field truth for 30 questions in the frozen unseen set. Your
labels become the reference for a field-level measurement. Treat this as an
annotation task: record what each question means, field by field. Do not
predict what any software would do.

## Isolation

Start from a fresh context. Do not rely on anything from earlier conversations
about this project.

You may read only:

- This brief.
- The template, `docs/verification/ask-unseen-two-2026-09-29-field-labels.template.json`.
- The question fixture, `server/tests/ask/fixtures/eval/unseen-two-2026-09-29.json`.
  This includes every case's expected action, request, clarification or
  unsupported reason, tags and rationale.
- The contract schemas: `server/ask/models/common.py`, `server/ask/models/request.py`
  and `server/ask/models/interpreter.py`.
- Reference data: `server/ask/data/player_catalog.json` and
  `server/ask/data/franchise_history.json`.
- The neutral city export at `/private/tmp/ask-unseen-two-city-reference.json`, if
  it exists. It did not exist when this brief was written. Without it, use the
  plain city name, for example `Brooklyn` or `Salt Lake City`.

You must not read, run or search:

- Anything else under `docs/`, including evaluation reports, journals (`*.jsonl`),
  audits, manifests, verification notes, reviews, ADRs and mockups.
- Anything else under `server/ask/`, including interpreters, prompts,
  closed-set descriptions, candidate lookup, aliases (`aliases.json`), the
  normalizer, resolvers, the pipeline and `server/ask/eval/`.
- `scripts/`, including the scorer, and every test file except the fixture above.
- Git history (`git log`, `git show`, `git diff`, `git blame`), issue trackers
  (`.beads/`, `bd`) and pull requests.
- The web, for anything about this project. General NBA knowledge is fine.
  Every player and team ID must come from the reference files.

Do not run any Ask code, lookup or model. You may use `jq` or a short script to
read the allowed files and to check that your JSON parses.

## Deliverable

Copy the template to
`docs/verification/ask-unseen-two-2026-09-29-field-labels.json` and fill it in.
Do not change `schema`, `fixture`, `fixture_sha256`, `case_id`, `question`,
`reference_time`, `context` or `label_scope`. In `labeler`, give your name or
agent ID, the time you finished, and a one-paragraph isolation statement that
lists what you read. Do not edit any other file.

The template has two kinds of cases.

- `"label_scope": "all"` (26 cases): fill `intent`, `scored_intent` and every
  field that `fields_by_intent` lists for your `scored_intent`.
- `"label_scope": "player"` (4 cases): the intent is fixed (`fixed_intent`).
  Leave `intent` and `scored_intent` as `null` and fill only `fields.player`.

Use `notes` for anything a reviewer should know, especially disagreement with
the fixture's expected label or rationale.

## Intent

`intent` is the request type the question asks for:

- `game_search`, `boxscore_stat`, `playoff_series` or `postseason_summary`, as
  described in `request.py`
- `unsupported:<reason>` for a request outside those types, where `<reason>` is
  one of the `UnsupportedReason` values in `interpreter.py`, for example
  `unsupported:standings`

A clarification case still has an intent. For example, a box-score question
that doesn't name its game is still `boxscore_stat`.

`scored_intent` names the intent whose fields you label: one of the four
request types, or `unsupported`. If your intent is `unsupported:<reason>`, use
`"scored_intent": "unsupported"` and `"fields": {}`.

Some questions fit a request type but ask for something that type rejects, such
as an average across several games. If both readings are defensible, use an
`any_of` intent listing both, such as `boxscore_stat` and
`unsupported:multi_game_average`. Set `scored_intent` to the supported type and
label its fields. Label `aggregation` as `per_game` when the question asks for
an average.

## Fields

Each field records what the question, and any page context it relies on, says.
It does not record what a final request would keep.

| Field | Meaning | Value format |
| --- | --- | --- |
| `stat_scope` | Whose statistic: one player (`player`), one team's totals (`team`), or who led (`leaders`) | string |
| `stat` | The statistic asked for. Use `stat_line` for a whole line, or when player or team scope names no statistic. With `leaders` scope and no statistic, use absent. | a `Stat` value from `common.py` |
| `aggregation` | `total` for one game, or `per_game` for an average across games | string |
| `player` | The NBA player the question names or refers to, whatever the player's role in the question | `player_id` integer from `player_catalog.json` |
| `teams` | Every NBA franchise the question names or clearly refers to, whether by city, nickname, abbreviation, historical name or description | list of one or two franchise `team_id` integers from `franchise_history.json` |
| `date` | The calendar date or date range of the games, resolved in America/New_York | `{"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}`, 1 to 7 days |
| `season` | A season or playoff year the question states, such as `2016 Finals` or `2015-16` | `"2015-16"` |
| `round` | A playoff round the question names. Give a conference only if the round wording names it, such as `Western Conference Finals`. | `{"round": "conference_finals", "conference": "west"}`; conference may be `null` |
| `game_number` | A numbered game of a series, such as `Game 7` | integer 1 to 7 |
| `location` | A city where games are played, as in "games played in Boston" (ADR 0011 venue filter) | city name |

Further rules:

- **Relative dates.** Resolve them against `reference_time` using the
  `RelativeDate` definitions in `common.py`. Weeks run Monday to Sunday.
- **Season versus date.** Label `season` only when the question states a season
  or playoff year. Do not derive one from a calendar date. When the question
  gives both, label both.
- **Team names versus venues.** A city used as a team name, or a former home
  used to describe a franchise (for example, "the team that left Seattle"),
  refers to a team. It is not a `location`.
- **Precedent.** The fixture's 65 accept labels show how the fixture author
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
- `game_id` is not a field. For "this game" on a box-score page, label `date`,
  `season`, `round` and `game_number` as absent unless the question states them.

## Status of each field

Each field takes exactly one of these objects.

| Status | Use when | JSON |
| --- | --- | --- |
| `value` | The question specifies it | `{"status": "value", "value": ...}` |
| `absent` | The question does not specify it, even if the request needs it | `{"status": "absent"}` |
| `ambiguous` | A mention could refer to two or more distinct entities, and neither the question nor the page settles it | `{"status": "ambiguous", "alternatives": [...]}` with at least two values in the field's format; for `teams`, each alternative is one `team_id` |
| `unresolved` | `date` only: the date is stated without a year (`year_required`), or the range is longer than seven days (`range_too_long`) | `{"status": "unresolved", "reason": "year_required"}` |
| `unlisted` | `player`, `teams` or `location` only: the question names a specific entity that is not in the reference data | `{"status": "unlisted"}` |

Missing is not the same as ambiguous. A question that names no date has an
absent date. A surname shared by several players whose careers overlap the
question's time frame is ambiguous. List those `player_id` values as
alternatives. If only one of them played in that time frame, it is a value.

When two labels are genuinely defensible, use
`{"any_of": [<label>, <label>], "note": "why both are defensible"}`. Use this
rarely. It makes the measurement more lenient, and the scorer reports each use.

## Consistency with the fixture

Your field labels should agree with each case's expected action. A case
expecting clarification of `season` for reason `missing` should normally have an
absent `season`. A case expecting clarification for reason `ambiguous` should
normally have an ambiguous field. One exception: a question that names two
teams but needs one has a two-team `teams` value, not an ambiguous one. The
fixture's rationale explains each case. If you disagree, label what you believe
and explain in `notes`. The scorer reports these disagreements for review.

## Example (synthetic, not from the set)

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

## Before you hand off

- Every `"all"` case has an `intent`, a `scored_intent` that is one of the
  intent values you labeled (or `unsupported`), and exactly the fields listed
  for that intent.
- Every `"player"` case has only `fields.player`.
- Every ID appears in the reference files. Seasons use `YYYY-YY`, and dates are
  ISO ranges of no more than seven days.
- Every `any_of` has a note.
- The file parses as JSON. You did not run or read the scorer.
