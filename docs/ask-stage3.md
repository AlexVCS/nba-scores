# Ask Stage 3: season leaders

Stage 3 of ADR 0010 ("leader families"). This document defines the
`season_leaders` tool before it is built, as ADR 0004 requires. Decisions
not already covered by ADRs 0003-0006 are recorded in
[ADR 0012](adr/0012-season-leader-qualification-and-sources.md). Production
flags are unchanged; this ships behind the same disabled `ASK_ENABLED` /
`VITE_ASK_ENABLED` gates as Stage 2.

## What the tool answers

`season_leaders`: the league-wide leaderboard for **one statistic** in **one
NBA season**, regular season **or** playoffs, as **season totals** or **per-game
averages**. Examples:

- "Who led the league in assists per game in 2019-20?"
- "Top 5 in total rebounds in 2023-24"
- "Who led the 2024 playoffs in points per game?"
- "2023-24 field goal percentage leaders"

The answer is a ranked table of the top N ranks (default 10), with rank, player,
team, games played and value. The leader row(s) are emphasized.

## Definitions

### Statistics

Supported (stats.nba `LeagueLeaders` category in brackets): points [PTS],
rebounds [REB], offensive rebounds [OREB], defensive rebounds [DREB], assists
[AST], steals [STL], blocks [BLK], turnovers [TOV], minutes [MIN], field goals
made [FGM], 3-pointers made [FG3M], free throws made [FTM], and field goal,
3-point and free throw percentage [FG_PCT, FG3_PCT, FT_PCT].

Not supported: fouls, plus/minus, "stat line" / "best player", efficiency or
any advanced metric, attempts-only leaderboards, double-doubles, and any
derived rate (per 36, per 100 possessions, per minute). A leaders question with
no statistic is clarified (`stat`, missing), per ADR 0011.

A statistic that was not recorded league-wide in the requested season is
answered as `not_found` (`season_stat_not_recorded`) without any fetch, using
the Stage 2 cutoffs: rebounds from 1950-51, minutes from 1951-52, steals,
blocks and offensive/defensive rebounds from 1973-74, turnovers from 1977-78,
3-pointers from 1979-80.

### Totals vs per game

- Counting statistics need an explicit measure. When the interpreter reads no
  measure ("Who led the league in points in 2022-23?"), or reads it as
  ambiguous, Ask asks **"Which measure (season totals or per game)?"** with two
  server-validated choices (Season totals, Per game). The answer is never
  defaulted: the official NBA scoring title is per game, but "most points"
  reads as totals, and the two leaders differ in many seasons.
- Percentages have no measure. Aggregation is always `total` for them, and a
  per-game reading of a percentage is treated as the same request.

### Qualification

Qualification is the **source's**, never re-derived by Ask for the primary
source. stats.nba `LeagueLeaders` applies the NBA's minimums itself:

| Leaderboard | Who is ranked | Observed stats.nba rule (sampled 2026-09-29) |
| --- | --- | --- |
| Totals (counting stats) | Every player who appeared | No minimum |
| Per game, regular season | Qualified players only | 2013-14, 2023-24, 2024-25: at least 58 games (70% of 82), games only. 2012-13: 70 games *or* a total threshold (Carmelo Anthony qualified with 67 games). 1985-86: 70 games |
| Percentages, regular season | Qualified players only | 2023-24: 300 FGM, 125 FTM, 82 3PM (exact match against the full totals table). 1985-86: 300 FGM, 125 FTM; the 3P% rule differs and is not characterized |
| Per game and percentages, playoffs | The source's playoff list | 2023-24 per game listed 140 players with as few as 3 games; the rule is not publicly specified |

Per-game and percentage leaderboards are requested from stats.nba in the modes
that apply qualification (PerGame for counting stats, Totals for percentages;
PerGame percentages are rejected by the endpoint). The answer says which rule
set applies ("Qualified players only, as listed by NBA.com" or "All players;
totals have no minimum").

**Era variations Ask does not reconcile** (documented, answered as the source
lists them):

- Before 1969-70 the NBA awarded statistical titles on season totals, not
  averages. A per-game leaderboard for those seasons can differ from the
  historical title holder; the answer carries a coverage note saying so.
- Pre-2013-14 minimums combined games with total thresholds; 3P% minimums
  changed several times; shortened seasons (1998-99, 2011-12, 2019-20, 2020-21)
  were prorated. Ask shows stats.nba's list for these seasons and does not
  re-derive it.
- A season in progress uses the source's prorated in-season minimum. The answer
  shows "Data as of" and is cached for 30 seconds only.

### Ties

- Ranks use **competition ranking** on unrounded values: tied players share a
  rank and the next rank skips (1, 2, 2, 4). For stats.nba this is the source's
  own `RANK`, validated for consistency; for Basketball-Reference totals Ask
  computes it from exact integer totals.
- **Every player tied at a shown rank is listed.** Top N therefore means "all
  players whose rank is N or better", and can list more than N rows.
- Displayed values are rounded (27.1). Two different ranks can show the same
  rounded value; the answer then notes that ranks use unrounded values, as
  NBA.com does.
- At most 50 rows are returned. If the tie group at the cutoff would push the
  table past 50, that whole tie group is left out and the answer states how many
  players share the next rank. A table is never cut inside a tie group.

### Regular season vs playoffs

- Default: regular season. Play-in games are excluded from both.
- Explicit playoff/postseason wording requires a `playoffs` reading; otherwise
  Ask asks "regular season or playoffs?" (Stage 2 guard, reused).
- Combined regular season plus playoffs is unsupported (as in Stage 2).

### Top N

- Default N = 10. The server reads "top N" (digits or words, 1-25) directly from
  the question text; System One models do not extract numbers (ADR 0005).
- N above 25 is unsupported. Clarification rewrites keep the original "top N"
  text, so the continuation keeps N.
- "Who led ..." still returns the top 10 with the leader emphasized; the leader
  alone would hide ties and near-ties.

### Seasons

One season per answer, stated or clarified. A bare year outside playoff wording
offers both overlapping seasons (Stage 2 rule). "2024 playoffs" is 2023-24.

## Sources (ADR 0003, ADR 0012)

- **Primary: stats.nba `LeagueLeaders`** (`Scope=S`, `LeagueID=00`), one call
  per season, phase, mode and category, 4-second timeout and one retry. The
  response's echoed parameters must match the request (league, season, season
  type, mode, category), player IDs must be unique, ranks must be consistent
  with values, and each team ID must be a franchise active that season.
  stats.nba lists a traded player under his final team.
- **Fallback: Basketball-Reference season totals page**
  (`/leagues/NBA_YYYY_totals.html`, regular-season or postseason table), through
  the shared rate-limited transport and raw-HTML cache from Stage 2. It is used
  **only for totals leaderboards**. Ask ranks every player's season aggregate
  row (TOT/2TM rows for traded players, shown as "Multiple teams") from exact
  totals. Every shown player must map to exactly one NBA player ID in the
  independent catalog for that season, or the fallback fails.
- **Per-game and percentage leaderboards have no fallback.** Basketball-Reference's
  own leaders page lists only 20 players at display precision and does not
  state its minimums, and Ask cannot reproduce stats.nba's era-dependent
  qualification from the totals table without guessing. When stats.nba cannot
  answer them, Ask reports unavailable, never a list with a different rule.
- One source per answer; values are never merged. A well-formed empty stats.nba
  list for a totals board still tries the fallback; an empty fallback after an
  empty primary is `not_found`. Throttled or failing fallback is `unavailable`.
- Completed seasons are cached for a day (after the following November, as in
  Stage 2); in-progress seasons for 30 seconds. The board is cached once per
  season/phase/mode/category and cut to N afterwards.

## Scope guard (out of scope, answered `unsupported`)

The guard runs after interpretation in HTTP and evaluation, including
clarification continuations, as in Stage 2.

- Team leaders ("who led the Lakers in scoring"), team leaderboards ("which
  team scored the most"), conference, division or position leaders, rookies.
- A named player: "did Jokic lead the league", "where did Curry rank in 3s".
  Player rank questions are a follow-up for the all-time/rank tool.
- Career, all-time, "ever" or multi-season leaders; streaks; records.
- Lowest/fewest/worst leaderboards, thresholds ("at least 30 ppg"), counts of
  games ("most 40-point games", ADR 0005 game-log index).
- Splits: home/away, opponent, month/date, before/after, last N games, clutch,
  quarters/halves/overtime, starters/bench, wins/losses.
- Advanced metrics and rates: PER, win shares, true shooting, usage, per 36/48,
  per 100 possessions, per minute; fouls; plus/minus; double-doubles.
- More than one statistic in one question ("points and assists leaders").
- Combined regular season and playoffs; play-in; preseason; All-Star; NBA Cup.
- Top N above 25.

## Result

`SeasonLeadersResult` (`kind: "season_leaders"`): season, season type, stat,
aggregation, requested N, qualification text, rows (rank, player, team or null
for multiple teams, games played, value), an optional omitted-tie note, an
optional coverage note, and `as_of`. Source link and source metadata follow
Stage 2. Asking is consent (ADR 0006): the table shows immediately.

## Verification

- `server/tests/ask/test_leader_tools.py`: identity and parameter echo checks,
  shared ranks and ties at the cutoff, the 50-row cap, qualification modes,
  playoff separation, unrecorded stats, totals-only fallback, unavailable and
  not-found sources, throttling, caching, normalization and the scope guard.
- `src/components/ask/AskSeasonLeadersResult.test.tsx`: table semantics, tied
  ranks, the leader emphasis, qualification and source notes.
- `server/tests/ask/fixtures/eval/stage3-dev.json`: development cases with
  labels authored before any live run. **Exposed development data, not unseen
  release evidence.**
- The stats.nba shapes and rules above come from a saved probe
  (`server/tests/ask/fixtures/season-data/nba-leaders-*.json`); no live model or
  provider calls were made.

## Career family: `career_stats`

Built after `season_leaders` passed, following the same doc-first rule. Decisions
are recorded in [ADR 0013](adr/0013-career-stats-scope-and-sources.md). One tool,
three views, chosen by Python from the question and the interpreter fields:

| View | When | Example | Source |
| --- | --- | --- | --- |
| `player_totals` | a player is named | "LeBron James career points", "Curry career 3-point percentage", "Jokic career stats" | stats.nba `PlayerCareerStats` career totals rows |
| `leaders` | no player is named | "Who has the most career assists?", "top 5 all-time in blocks" | stats.nba `AllTimeLeadersGrids` (TopX 250) |
| `player_rank` | a player is named with rank wording ("rank", "ranked", "where does ... stand") | "Where does Curry rank in career 3-pointers made?" | stats.nba `AllTimeLeadersGrids` (TopX 250) |

### Definitions

- **Career** means every NBA season the source lists, regular season by default.
  "Playoffs"/"postseason" wording requires a playoff reading (Stage 2 guard);
  combined regular season plus playoffs is unsupported. BAA/ABA seasons are
  whatever stats.nba includes in NBA career totals; ABA totals are never added.
- **Totals vs per game.** Career questions default to totals ("career points",
  "all-time leading scorer" are totals by convention). A player's career per-game
  average is computed from his exact career totals and games played, as in
  Stage 2, never from rounded averages.
- **Percentages** for a player are his career made/attempted ratio from the
  source (`FG_PCT` etc.), shown only with positive attempts.
- **Leaders and rank are totals only.** stats.nba's all-time per-game and
  percentage lists do not apply the NBA's published all-time minimums (the
  2026-09-29 probe lists Victor Wembanyama 2nd in career blocks per game after
  two seasons, and a 2024-25 rookie 4th in career 3P%). Showing those as
  "all-time leaders" would misstate the record, so per-game and percentage
  leaderboards and ranks are unsupported. Minutes have no all-time list.
- **Ties** follow the source's `*_RANK` (competition ranking), validated for
  consistency. Every player tied at a shown rank is listed; the 50-row cap and
  omitted-tie note are the same as season leaders. Top N: default 10, 1-25.
- **Rank** is the player's source rank in the top 250 list. A player outside the
  list is answered as "not in NBA.com's top 250", never with an estimated rank.
  A tied rank says how many players share it.
- **Partially recorded statistics.** Steals, blocks, offensive/defensive rebounds
  (1973-74), turnovers (1977-78) and 3-pointers (1979-80) were not recorded
  earlier. Career totals and all-time lists cover only recorded seasons and say
  so. A player whose career began before a stat was recorded gets his source
  total with a coverage note, but no per-game average for it (games before the
  stat existed would dilute the average), shown as unavailable.
- **Active players' careers change nightly.** Career and all-time data are
  cached for one hour and carry "Data as of".

### Sources

stats.nba only, with no Basketball-Reference fallback (ADR 0013): BRef player
pages need an NBA-ID-to-BRef-slug mapping that Ask does not have, and BRef's
career leader pages are outside the allowlisted source paths and would need
cross-career name identity. When stats.nba fails, career answers are
unavailable.

### Out of scope (unsupported)

- **Career highs** ("Kobe's career high in points"). `PlayerProfileV2`'s
  `CareerHighs` set returned only playoff games for LeBron James in the probe
  (51 points, 2018 Finals; his 61-point regular-season high is missing), so it
  cannot be trusted as a career high. Next: derive highs from the ADR 0005
  game-log index.
- Season or game records ("most points in a season/game"), counting-game
  records, streaks (ADR 0005 index).
- Franchise leaders ("Lakers all-time leading scorer"), active-only lists,
  position, rookie or era lists, comparisons between players, a player's rank in
  per-game or percentage lists, and all splits listed for season leaders.

## Next

- Career highs and season/game records from the ADR 0005 game-log index.
- A verified per-era qualification table would let per-game and percentage
  boards (season and all-time) use a fallback or official all-time minimums.
- Independent unseen evaluation cases for both new families and a new frozen
  release commit, per ADR 0009.
