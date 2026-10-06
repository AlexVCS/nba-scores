# Ask unseen set three: label notes (DRAFT)

Fixture: `server/tests/ask/fixtures/eval/unseen-three-draft.json`, 179 cases. This is a
**draft**. It needs an independent human label review before it is frozen as ADR 0009
unseen evidence. No interpreter, candidate lookup, or provider was run to write it, and
no evaluation results or journals were read.

## Coverage

| Family | Accept | Clarify | Unsupported | Total |
| --- | --- | --- | --- | --- |
| game_search | 17 | 3 | 2 | 22 |
| boxscore_stat | 18 | 3 | 3 | 24 |
| playoff_series | 16 | 2 | 1 | 19 |
| postseason_summary | 19 | 0 | 1 | 20 |
| player_season_stats | 18 | 4 | 3 | 25 |
| team_records | 17 | 2 | 1 | 20 |
| season_leaders | 19 | 2 | 2 | 23 |
| career_stats | 19 | 1 | 6 | 26 |
| **All** | **143** | **17** | **19** | **179** |

Each non-accept case names one family in its id and tags, as `scripts/ask/release.py`
and `scripts/ask/tier_gate.py` expect. Unsupported reasons: `other` 12,
`unsupported_leader_stat` 3, and one each of `multi_game_average`, `prediction`,
`historical_comparison`, `follow_up`, `reference_question`, and `not_basketball`. The
deprecated reasons (`season_stats`, `career_stats`, `season_leaders`, and so on) are not
used.

## Labeling rules applied

- **Sources of truth.** Labels follow `server/ask/models`, `docs/ask-contract.md`,
  `docs/ask-stage2.md`, `docs/ask-stage3.md`, ADRs 0004, 0005 and 0011-0014, and the
  deterministic Python rules in `server/ask/normalize.py`, `server/ask/measure.py` and
  `server/ask/season_scope.py` (the scope guard is part of the production contract).
- **Entities.** Player IDs come from `server/ask/data/player_catalog.json` and aliases
  from `aliases.json`. Team names and tricodes are dated from `franchise_history.json`
  (scoring strips display fields, so only IDs count). Venue `location` values are copied
  from the city table in `server/ask/candidates/locations.py`. That table gives the
  2005-07 Oklahoma City Hornets tenure the tricode `NOP`, while the dated team name uses
  `NOK`. Display fields are stripped in scoring, so this does not matter.
- **Measure (ADR 0014).** Python reads it from the question text. With no stated measure,
  player season stats are `per_game`, a full career stat line is `per_game`, one career
  statistic and all-time lists are `total` (ADR 0013 as amended 2026-10-01), and
  counting-stat season leaders ask for `aggregation`. Percentages are always `total`.
- **Top N.** Python reads it: digits or number words up to "twenty five". Above 25, the
  label is `limit 25` with `requested_limit`. "Who led ..." keeps the default of 10.
- **Seasons.** A playoff year maps to the season that ends in it. A bare year without
  playoff wording is `season` ambiguous. "This season" and "last season" use in-season
  reference times, except in one deliberate offseason case.
- **Relative dates.** These resolve in America/New_York against `reference_time`, with
  one case that crosses the UTC midnight boundary.
- **Box scores.** `game.teams` lists every team named, opponents included. Team scope
  keeps the target in `game.teams`. With no game named, page context supplies `game_id`.
- **Clarify fields.** These follow the precedents in `stage2-dev` and `stage3-dev`: an
  ambiguous surname is `player`/ambiguous; "career or one season?" is `intent`/ambiguous
  (not for present-perfect wording, which is a career total since 2026-10-01);
  a leaders question with no stat is `stat`/missing.
- **Ties.** Ties do not change a request. Top N always lists every tied player, so the
  "including anyone tied" wording (`season_leaders-03`) keeps the plain top-3 request.
  Tie handling can only be checked at the answer level.

## Automated checks (throwaway script, not in the repo)

- All 179 cases load through `LabeledCase.from_json`. Every accept request validates
  through `ASK_REQUEST_ADAPTER` and keeps every labeled value after validation. Ids and
  questions are unique. Family tags match ids and accept intents.
- Overlap was checked against all 673 questions in 11 other fixture files under
  `server/tests/ask/fixtures/`:
  - No exact duplicates after casefolding and whitespace normalization.
  - No accept has the same scored request as any existing labeled accept.
  - Six template-level near matches remain (character ratio at least 0.80, or word
    Jaccard at least 0.60). They use different entities and different labels, so they
    are kept: boxscore_stat-02, -06, -08, -20, player_season_stats-06, career_stats-21.
  - Nine closer matches from the first draft were reworded or replaced. One of them
    duplicated "Kareem career points".
- The ADR 0014 measure rules, top-N parsing, and the stage 2/3 split-word guards were
  checked against every season-family accept. No accept question contains a guard split
  word. Every aggregation, limit, and career view (rank or totals) matches the Python
  rules.

## Debatable labels

Reviewed 2026-09-30. The three typo cases stay accept and now list `clarify` in `also_accept`. season_leaders-19 is now accept per game. The other eight keep their draft labels.

| Case | Question | Draft label | Alternative |
| --- | --- | --- | --- |
| game_search-11 | Warriros games on March 8, 2016 | accept (GSW) | `teams` clarification (typo not matched) |
| boxscore_stat-16 | Joel Embid's points on January 22, 2024 | accept (Embiid) | `player` clarification |
| player_season_stats-18 | Kevin Duarnt points per game 2013-14 | accept (Durant) | `player` clarification |
| postseason_summary-18 | What was the Bucks' playoff record in 2018-19? | accept postseason_summary (MIL) | unsupported/`other` (team_records rejects playoff wording) |
| season_leaders-19 | Who won the scoring title in 2013-14? | clarify `aggregation` | accept per_game (the NBA scoring title is by definition per game) |
| boxscore_stat-20 | Who led Game 3 of the 2019 Finals? | clarify `stat`/missing | clarify `intent`, since it may ask who won |
| boxscore_stat-21 | What did Antetokounmpo score on December 13, 2023? | clarify `player` (Giannis and Thanasis were both Bucks) | accept Giannis, his 64-point game |
| player_season_stats-22 | Jayson Tatum stats this season (ref 2026-09-30) | clarify `season`/ambiguous (offseason) | accept 2025-26 (just finished) |
| postseason_summary-19 | Recap New York's 2021 postseason. | clarify `teams` (Knicks and Nets both qualified) | accept Knicks |
| season_leaders-23 | Who led the league in personal fouls in 2018-19? | unsupported `other` (guard) | `unsupported_leader_stat` |
| team_records-20 | Which team had the best record in 2015-16? | unsupported `other` ("best" split) | accept league standings for 2015-16 |
| boxscore_stat-23 | What were Kawhi Leonard's per-game averages over the 2019 Finals? | unsupported `multi_game_average` | `other` (the player-season guard rejects "finals") |

Lower-risk judgment calls a reviewer may still want to confirm:

- **career_stats-19** (Wembanyama "How many blocks has ... recorded?"): the draft label was
  `intent`/ambiguous, following the stage 3 precedent. Decided 2026-10-01: accept, career
  total blocks (see "Owner decisions 2026-10-01").
- **postseason_summary-06** ("Who won each round of the 1970 playoffs?") and **-05**
  ("Recap every round of the 2017 playoffs."): both are labeled as a league-wide
  postseason summary, not a list of series.
- **playoff_series-12** ("Who did the Mavericks face in the 2006 championship round?"):
  the question asks for the opponent, and the label answers it with the Finals series.
- **playoff_series-07** and **-04**: "conference finals" and "conference semis" with no
  East or West named are labeled with a null conference. For one named team, the team
  and round identify the series.
- **boxscore_stat-10**: the page `game_id` `0042200405` should be 2023 Finals Game 5.
  The label depends only on the context, not on the game.
- **Unsupported reasons** follow the Python guards, which return `other` for team,
  rookie and franchise leaders, splits, advanced metrics, career highs, triple-doubles,
  multi-season lists and combined phases. The one hypothetical cross-era comparison
  (postseason_summary-20) is labeled `historical_comparison`.
- **Game facts.** Dates were picked from well-known games (Booker's 70, Klay's
  37-point quarter, Lillard's 71, Dončić's 73, Wilt's 100, and so on) and should be
  spot-checked. The accept labels do not depend on those facts, but the two
  surname-ambiguity clarifications (boxscore_stat-19 Gasol, -21 Antetokounmpo) assume
  both players were active on those dates.

## Owner decisions 2026-10-01

The owner answered the review sheet's "Needs your decision" items. The fixture, its
`scope` counts and the field-label template (new `fixture_sha256`) were updated.

- **"has recorded" means career.** Present-perfect wording about a named player's count
  is his career total. career_stats-19 is now accept: `career_stats`, `player_totals`,
  Victor Wembanyama (1641705), blocks, `total`, regular season. Counts moved to accept
  140, clarify 18; career_stats is 19/1/6.
- **Full career lines show per game first.** career_stats-07 ("Michael Jordan career
  stats") is now `stat_line` `per_game`. It is the only full-line career case with no
  stated measure in any eval fixture. Single career statistics stay `total`.
- **Dates swapped so the games exist.** game_search-04 is March 4, 1983. game_search-10
  has reference time 2025-01-08, so last week is 2024-12-30..2025-01-05. game_search-11
  is March 7, 2016. game_search-12 is 2/2/2019. boxscore_stat-15 has reference time
  2023-12-08, so last night is 2023-12-07. boxscore_stat-19 is February 21, 2014 (still a
  `player` clarification).
- **game_search-02 is kept** (Salt Lake City, April 20, 1997) as a deliberate "no games
  that day" test.
- No interpreter, lookup or provider was run on this set for these edits. The changed
  questions are still unique across the fixture files.

## Owner decisions 2026-10-06

- **"New York" is the Knicks.** postseason_summary-19 is now accept: the Knicks' 2020-21
  postseason summary.
- **"Best record" is the standings.** team_records-20 is now accept: league standings for
  2015-16. The scope guard lets "best/worst record" through when no team is named.
- **Personal fouls leaders are supported.** season_leaders-23 is now accept: fouls,
  season totals, top 10. stats.nba has no per-game fouls board, so fouls are totals only.
- Counts are now accept 143, clarify 17, unsupported 19. These three cases left the
  field-label file (now 36 cases) because an accept label supplies their field gold.
- **These seven cases are no longer unseen.** The app was changed with these questions
  in view: the three above, plus game_search-11 ("Warriros" now matches the Warriors),
  team_records-14 ("mark" was read as a player), career_stats-18 ("rank" was read as a
  player) and season_leaders-19 ("title" was read as the Finals). The candidate lookup
  was run on them. They should be replaced or reported separately before the freeze.
- The "Unsupported reasons" counts in the Coverage section predate these changes.

## Before freezing

1. An independent reviewer relabels or confirms every case, especially the table above.
   `also_accept` should be added only where the reviewer explicitly accepts two
   outcomes.
2. Rename the file with its freeze date, record the frozen production commit, and keep
   it out of any tuning or calibration run until the release evaluation.
