# Ask: candidate lookup (#200)

Candidate lookup turns a question and its app context into the bounded, typed
candidates that an interpreter chooses from. The interpreter can only pick
what lookup offers, so candidate recall caps Ask's accuracy. The output is the
contract's `CandidateLookupResult` (`server/ask/models/candidates.py`).

```python
from server.ask.candidates import CandidateLookupService

lookup = CandidateLookupService()  # implements server.ask.protocols.CandidateLookup
result = lookup.lookup(question, context)  # context: AskContext
wider = lookup.expand(question, context, "player", result.sets["player"])
```

## Files

| Piece | File |
| --- | --- |
| Service, orchestration, contract assembly | `server/ask/candidates/lookup.py` |
| Alias loader (the only reader of `aliases.json`) | `server/ask/candidates/aliases.py` |
| Dated team names | `server/ask/candidates/teams.py`, `server/ask/data/franchise_history.json` |
| Player catalog and indexes | `server/ask/candidates/players.py`, `server/ask/data/player_catalog.json` |
| Date language | `server/ask/candidates/dates.py` |
| Seasons, rounds, game numbers | `server/ask/candidates/patterns.py` |
| Measurement | `server/ask/candidates/evaluation.py`, `scripts/ask/measure_candidates.py` |
| Development questions | `server/tests/ask/fixtures/candidates_dev_questions.json` |
| Tests | `server/tests/ask/test_candidates_*.py` |

## What it produces

Lookup returns one `CandidateSet` for each of `player`, `team`, `date`,
`season`, `round`, and `game_number`. Each set has one of three statuses:

- `candidates`: at least one candidate.
- `no_candidates`: the question mentions something of this type, recorded in
  `unmatched_text`, but nothing valid matches it.
- `not_mentioned`: nothing of this type appears in the question.

Bounds: at most 8 candidates per phrase, 12 per field, and 48 in total. When a
bound cuts a list, `truncated` is set. A truncated set is not exhaustive, so
the interpreter should ask for clarification rather than choose from it.
"Jalen" has 18 catalog matches, for example.

A missing candidate is never evidence for a different entity:

- A phrase shaped like a full name that is not in the catalog, such as
  "Dwight Schrute", gets no candidates. It does not fall back to Dwight Howard.
- A historical team name outside its dated window gets no candidates. For
  example, "Seattle SuperSonics" in 2015 does not become the Thunder.
- `expand()` is the only way to loosen matching. The cascade calls it after an
  interpreter reports `no_matching_candidate`. It adds lower-similarity
  spellings and first-name/surname partials. Previous candidates stay first,
  and the per-field limit still applies. For dates it returns `previous`
  unchanged.

## Sources

**Players.** `player_catalog.json` is a snapshot of every NBA player (5,243
rows, generated 2026-09-29). It comes from stats.nba.com `CommonAllPlayers`
merged with nba_api's bundled list, and it records first and last seasons.
Matching tries these in order: full name (accents and `Jr.`/`III` suffixes
ignored), aliases, one-word names, surnames, first names, then close
misspellings (difflib, similarity at least 0.85 for surnames and 0.88 for full
names). Single words need a capital unless the question has no capitals at
all. Ranking decides only which candidates survive a bound. The order is match
strength, then careers that cover a season named in the question, then
players who appeared in a game, then the most recent careers. The catalog
stores no team: current rosters never decide which team a player was on, so
`team_ids` stays empty. Refresh the snapshot with:

```
server/venv/bin/python -m server.ask.candidates.players --refresh
```

**Teams.** `franchise_history.json` lists each current franchise's names with
their first and last seasons, for example Seattle SuperSonics 1967-68 to
2007-08. The 30 current names and tricodes are tested against nba_api's
static team list. A team phrase is filtered to the names in use in any season
the question implies, whether from a season, a year, or a resolved date.
Examples:

- "Hornets" in 2000 is Charlotte.
- "Hornets" in 2008 is New Orleans (now the Pelicans).
- "Hornets" tonight is Charlotte.
- "Hornets" with no date offers both, with the current name first.

Defunct franchises, such as the 1947-1955 Baltimore Bullets, are deliberately
absent, so they can never resolve to a current team.

**Aliases.** `server/ask/data/aliases.json` is the one alias mapping. Every
adapter and Python validation must load it through
`server.ask.candidates.aliases.get_alias_mapping()`. It has three sections:

- `teams`: alias to a dated name record, for example "Sonics" to "Seattle
  SuperSonics", so it still respects seasons.
- `cities`: shorthand to a city, for example "LA" to "Los Angeles".
- `players`: alias to player IDs.

It contains no statistical definitions. An alias adds a candidate and never
hides catalog matches: "Kobe" offers Kobe Bryant first, then the other Kobes.
Aliases written in capitals in the file (KD, AI, OKC, LA) match only when the
question writes them in capitals. `alias_version()` hashes the alias file, the
franchise history, and the player catalog, and it belongs in cache keys.

**Dates.** Dates resolve against the New York calendar day of
`AskContext.reference_time`.

- "Last week" is the preceding Monday–Sunday.
- "Last Friday" is the most recent Friday before today.
- A bare "Friday" keeps two readings: the last Friday and this week's Friday.
- "Past N days" ends today.
- A calendar date without a year (`February 14`, `1/23`, `Christmas`) is kept
  with `year=None` and `unresolved_reason="year_required"`. The year is never
  defaulted.
- Ranges longer than seven days (`last month`, `March 2025`) are kept but
  unresolved (`range_too_long`).
- Impossible dates (`February 30, 2025`) are marked `invalid_date`.

Some phrases have no `RelativeDate` value in the contract: "N days ago", "day
before yesterday", weekends, "next week", "next Friday", and months. They are
emitted as explicit `calendar_date` or `calendar_range` components that Python
has already resolved.

**Seasons.**

- `2023-24` and `2023/24` are explicit seasons. Seasons whose years are not
  consecutive get no candidates.
- A bare year with playoff language (Finals, playoffs, series, round, game N)
  is the playoff year: "2024 Finals" is 2023-24. Without playoff language, both
  seasons that touch the year are offered.
- "This season" and "last season" are relative. From July through September,
  both neighbouring seasons are offered, because either can be meant.
- "This year" and "last year" are calendar years.

**Rounds and game numbers.** Rounds use the contract's modern names, with the
conference when it is stated (East/West, ECF/WCF). Old "division" rounds map
to the corresponding modern slot with a lower score. The play-in tournament is
not a playoff round, so it gets no candidates. Game numbers outside 1–7 get no
candidates.

**App context.** Context is used only when the question points at the page.
"That day" and "this date" use `view_date`. "This series" and "these playoffs"
use `playoff_season`, as does a playoff question with no season asked on the
playoffs or series page.

## Measurement

```
server/venv/bin/python scripts/ask/measure_candidates.py [--questions FILE] [--json] [--min-recall 0.95]
```

The script reports the following, measured against a labeled question file:

- recall per field
- the share of questions where every gold value was offered
- correct abstention (labeled "no valid match" fields that got no candidates)
- ambiguity kept open
- forbidden candidates offered (for example the Thunder for "SuperSonics 2015")
- candidate-set size (median and max)
- warm lookup latency (median and p95), plus the one-time index load

The default file is the **development** set: 75 questions covering all four
intents plus unsupported requests, aliases, historical names, relative dates,
ambiguity, and absent entities. It was written alongside the code and used
for tuning, so its numbers are not release numbers.

Results on the development set, 2026-09-29:

| Measure | Result |
| --- | --- |
| Recall | 161/161 gold values (100%); every field at 100% |
| Correct abstention | 15/15 |
| Ambiguity kept open | 4/4 |
| Forbidden candidates offered | 0 |
| Candidate-set size | median 2, max 9 |
| Warm latency | median 0.128 ms, p95 1.993 ms, max 5.607 ms (fuzzy spelling checks dominate) |
| Index load | 74.4 ms, first call only |

Release targets fixed before opening the unseen set: at least 95% recall per
field and at least 90% of questions with every gold value offered. Warm lookup
p95 must stay below 20 ms. Explicit no-match labels must abstain correctly,
and forbidden candidates must never be offered. Report first-load time
separately. These targets apply to the independently labeled release set;
the development measurements above do not satisfy the release gate.

## Known gaps

- Player candidates carry career spans but no dated team membership
  (`team_ids` stays empty). Adding it needs season-by-team rosters, for
  example `CommonPlayerInfo` or `PlayerCareerStats` per player.
- Nicknames not in `aliases.json` are missed until someone adds them.
- Spelled-out ordinal dates ("the 23rd") and bare month references ("in
  March" is handled; "March games" is not) are not parsed.
