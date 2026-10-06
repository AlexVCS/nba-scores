# Ask unseen-three answer keys: check against stats.nba.com (2026-10-06)

This report compares every answer key ("gold" case) for the Ask release evaluation with what stats.nba.com returns today. stats.nba.com is Ask's primary source; Basketball-Reference is the fallback. Many keys were written from Basketball-Reference pages, so the question is whether any of them disagree with the primary source. Differences are listed for the owner to rule on; no gold value was changed to make the two agree.

The answer keys are `server/tests/ask/fixtures/answers/unseen-three-answers-part-a.json` (70 cases) and `unseen-three-answers-part-b.json` (73 cases): one per accept case in `server/tests/ask/fixtures/eval/unseen-three-draft.json` (143). Each key lists `checks`: a path into Ask's response and the value expected there.

Seven questions were replaced on 2026-10-06 because the app had been changed with them in view. Their keys moved, unchanged, to `unseen-three-exposed-dev-answers.json` (development data, not release evidence), and seven keys were written for the replacement questions. The counts below are for the final 143; the seven moved keys are reported separately at the end.

## Result

| | Cases | Checked values |
|---|---|---|
| Checked against stats.nba.com | 143 | 1095 |
| Matched | 142 | 1094 |
| Differs | 1 | 1 |
| Could not check | 0 | 0 |

The keys hold 1330 checks. 1095 of them state a fact the source can confirm and were compared with the raw response. The other 235 repeat the question itself (the season, statistic, measure, view or scope that was asked for, the team asked about, and the player in a rank question); they were confirmed against the request, since no source value exists for them.

stats.nba.com was reachable throughout: 205 requests, 204 answered HTTP 200 on the first attempt and one (`teamyearbyyearstats` for Portland) returned HTTP 500 and then 200 on the retry. No timeouts. Requests were sequential with a pause between them, sent with the headers the server uses (`NBA_STATS_HEADERS` in `server/services/nba_stats_client.py`) to the endpoints and parameters the resolvers use.

| Family | Cases | Source checks | Request checks | Differing checks | stats.nba endpoint |
|---|---|---|---|---|---|
| game_search | 17 | 137 | 0 | 0 | `scoreboardv3` (one request per date in the range) |
| boxscore_stat | 18 | 109 | 0 | 0 | `boxscoretraditionalv3`; game found with `scoreboardv3`, `leaguegamefinder` (player and date) or `leaguegamelog` (playoff game number) |
| playoff_series | 16 | 128 | 0 | 0 | `leaguegamelog` (SeasonType=Playoffs, team rows); `leaguestandings` for the conference label |
| postseason_summary | 19 | 337 | 0 | 1 | `leaguegamelog` (SeasonType=Playoffs, team rows); `leaguestandings` for the conference label |
| player_season_stats | 18 | 88 | 74 | 0 | `playercareerstats` (PerMode=Totals), season rows |
| team_records | 17 | 114 | 18 | 0 | `teamyearbyyearstats` (one team) or `leaguestandings` (standings) |
| season_leaders | 19 | 110 | 76 | 0 | `leagueleaders` (Scope=S, PerMode Totals or PerGame) |
| career_stats | 19 | 72 | 67 | 0 | `playercareerstats` career rows, or `alltimeleadersgrids` (TopX=250) for lists and ranks |

## Difference needing an owner ruling

| Case | Question | Checked path | Gold value and its source | stats.nba value and endpoint | Recommendation |
|---|---|---|---|---|---|
| `unseen-three-postseason_summary-03` | Give me the Philadelphia Warriors' 1956 postseason. | `result.rounds[round=conference_finals].conference` | `east`. Basketball-Reference, 1956 NBA Playoffs (`playoffs/NBA_1956.html`): "Eastern Division Finals: Philadelphia Warriors over Syracuse Nationals (3-2)". | No single side. `leaguestandings?Season=1955-56` lists Philadelphia in Division `East` and Syracuse in Division `West` (it shows five West teams and three East). The playoff game log itself carries no division or conference. | Keep gold as `east`. The stats.nba standings row for Syracuse looks like a source error: Syracuse met Boston and then Philadelphia in that postseason. Ask does not read the side from this endpoint (it uses its own team history table in `server/services/playoffs.py`), so the release run is not expected to show `west`. |

Every other checked value in this series (opponent, 3-2 result, winner, the Finals, the 7-3 record) matches the stats.nba game log.

## How each family was compared

For each case a small script fetched the raw response, read the value each check points at, and compared it with the gold value using the same matching rules as `scripts/ask/answer_check.py` (exact, rounded to the shown digits, unordered list, list length, one of). Ask itself was not run: no pipeline, resolver, interpreter or candidate lookup saw these questions, including the seven replacements.

- **game_search.** Games on each date from `scoreboardv3`, filtered by the named teams and, for a city, by the home team. The one `not_found` case (Salt Lake City, 1997-04-20) is confirmed: eight games that day, none hosted by Utah.
- **boxscore_stat.** The player, team or leader values from `boxscoretraditionalv3`; game date, home and away teams and final score from `scoreboardv3`.
- **playoff_series and postseason_summary.** Series were rebuilt from the playoff game log: games between two teams, wins from each row's W/L. The log has no round or conference label, so two values were derived. The round is counted back from the Finals (the series whose winner plays no later series is the Finals, and so on); for 2001-02 and later it was also checked against the round digit in the game id, with no conflicts. The conference is the two teams' shared Conference (or, before 1970-71, Division) in `leaguestandings`. Play-in games are not in the playoff log.
- **player_season_stats and career_stats.** Totals from `playercareerstats`; per-game values are total divided by games played and must round to the gold value. A team stint uses that team's row; otherwise the season total row.
- **team_records.** One team's record from `teamyearbyyearstats`; standings from `leaguestandings`, ordered as Ask orders them (league: win percentage; conference: the source's PlayoffRank).
- **season_leaders.** `leagueleaders` rows by the source's RANK, cut at the requested top N with ties kept together.

## Notes that are not differences

- **Neutral-site game.** `unseen-three-game_search-14` (Philadelphia Warriors, 1962-03-02) accepts either home/away order because the Basketball-Reference page does not settle it. stats.nba lists Philadelphia as home (169) and New York as away (147). The key passes either way; the owner may tighten it to the stats.nba order.
- **Known Basketball-Reference differences, already keyed to stats.nba.** Five part-B keys are tagged `source_disagreement` and explain in their notes where Basketball-Reference differs. All five still match stats.nba today: `team_records-03` and `team_records-04` (conference order is the source's playoff seeding, with shared ranks in 1997-98), `season_leaders-07` and `season_leaders-14` (different qualification minimums change who is listed), `season_leaders-11` (rounding at x.x5). Two more (`season_leaders-08`, `season_leaders-10`) differ only in order inside a tie, which the keys do not check.
- **Values that move.** Career totals of active players and the all-time lists (`career_stats` cases) match as of today and will change once the 2026-27 season starts.
- **Part A sources.** Most part A keys cite Basketball-Reference only. Apart from the one row above, all of their checked values match stats.nba, including the older ones (games and box scores from 1962, 1975 and 1983, and playoff series from 1956 to 1971), which stats.nba does hold.

## Answer keys written for the seven replacement questions

Each was read on 2026-10-06 from the raw stats.nba response and from the Basketball-Reference page. The two sources agree on every value, and all seven are `verified: true`. The requests are copied from the evaluation fixture. No question's premise turned out to be wrong.

| Case | Question | Key values | Sources read |
|---|---|---|---|
| `unseen-three-game_search-23` (part A) | Was there a Timberwoves game on April 11, 2018? | One game: Denver 106 at Minnesota 112, in overtime. | stats.nba `scoreboardv3` 2018-04-11 (game 0021701225); Basketball-Reference `boxscores/?month=4&day=11&year=2018` |
| `unseen-three-postseason_summary-21` (part A) | Take me through Sacramento's 2002 playoffs. | Kings beat Utah 3-1 and Dallas 4-1, then lost the West finals to the Lakers 3-4; record 10-6; two series won. | stats.nba `leaguegamelog` 2001-02 Playoffs; Basketball-Reference `playoffs/NBA_2002.html` |
| `unseen-three-team_records-21` (part B) | Will you show me the Trail Blazers' record from 1990-91? | Portland 63-19 (.768). | stats.nba `teamyearbyyearstats` (Portland); Basketball-Reference `leagues/NBA_1991_standings.html` |
| `unseen-three-team_records-22` (part B) | Who finished with the worst record in the NBA in 1992-93? | League standings, 27 rows; last is Dallas 11-71, then Minnesota 19-63; first is Phoenix 62-20. Wins and losses are checked in order, team ids unordered because of equal records. | stats.nba `leaguestandings` 1992-93; Basketball-Reference `leagues/NBA_1993_standings.html` |
| `unseen-three-season_leaders-24` (part B) | Who took the rebounding crown in 2006-07? | Top 10 per game: Garnett 12.8, Chandler 12.4, Howard 12.3, Boozer 11.7, Camby 11.7, Wallace 10.7, Duncan 10.6, Marion 9.8, Stoudemire 9.6, Brand 9.3. Ranks 1 to 10 with no ties: both sources rank on unrounded averages, and Biedrins (also 9.3) is eleventh in both. Leader played 76 games for Minnesota. | stats.nba `leagueleaders` REB per game 2006-07; Basketball-Reference `leagues/NBA_2007_leaders.html` |
| `unseen-three-season_leaders-25` (part B) | Who sank the most field goals in total in 2002-03? | Top 10 totals: Bryant 868, McGrady 829, Iverson 804, Garnett 743, Duncan 714, O'Neal 695, Jamison 691, Nowitzki 690, Jordan 679, Marbury 671. No ties; eleventh is Mashburn 670. Leader played 82 games for the Lakers. | stats.nba `leagueleaders` FGM totals 2002-03; Basketball-Reference `leagues/NBA_2003_totals.html` |
| `unseen-three-career_stats-27` (part B) | What is Hakeem Olajuwon's ranking on the career blocks list? | Rank 1 with 3,830 blocks (Mutombo is second with 3,289). | stats.nba `alltimeleadersgrids` BLKLeaders; Basketball-Reference `leaders/blk_career.html` |

Three facts in `ask-unseen-three-review-sheet.md` had been written from memory by the question author. All three are confirmed by both sources: the Timberwolves hosted Denver on 2018-04-11 (G-23), Kevin Garnett led the league in rebounds per game in 2006-07 (L-24), and the Kings reached the 2002 West finals and lost to the Lakers in seven games (R-21).

No existing gold value was edited: no transcription errors were found.

## Per-case results (final 143)

Source checks matched / source checks, per case. Request checks are not counted here.

| Case | Result | Source checks matched | stats.nba request |
|---|---|---|---|
| `game_search-01` | match | 12/12 | `scoreboardv3?GameDate=2016-11-02&LeagueID=00` ... GameDate through 2016-11-05 (4 daily requests) |
| `game_search-02` | match | 1/1 | `scoreboardv3?GameDate=1997-04-20&LeagueID=00` |
| `game_search-03` | match | 7/7 | `scoreboardv3?GameDate=2009-02-02&LeagueID=00` |
| `game_search-04` | match | 7/7 | `scoreboardv3?GameDate=1983-03-04&LeagueID=00` |
| `game_search-05` | match | 7/7 | `scoreboardv3?GameDate=1975-01-10&LeagueID=00` |
| `game_search-06` | match | 12/12 | `scoreboardv3?GameDate=2025-02-10&LeagueID=00` ... GameDate through 2025-02-14 (5 daily requests) |
| `game_search-07` | match | 7/7 | `scoreboardv3?GameDate=2024-11-19&LeagueID=00` |
| `game_search-08` | match | 7/7 | `scoreboardv3?GameDate=2025-01-08&LeagueID=00` |
| `game_search-09` | match | 7/7 | `scoreboardv3?GameDate=2025-03-08&LeagueID=00` |
| `game_search-10` | match | 22/22 | `scoreboardv3?GameDate=2024-12-30&LeagueID=00` ... GameDate through 2025-01-05 (7 daily requests) |
| `game_search-12` | match | 7/7 | `scoreboardv3?GameDate=2019-02-02&LeagueID=00` |
| `game_search-13` | match | 7/7 | `scoreboardv3?GameDate=1985-01-05&LeagueID=00` |
| `game_search-14` | match | 6/6 | `scoreboardv3?GameDate=1962-03-02&LeagueID=00` |
| `game_search-15` | match | 7/7 | `scoreboardv3?GameDate=2015-04-01&LeagueID=00` ... GameDate through 2015-04-03 (3 daily requests) |
| `game_search-16` | match | 7/7 | `scoreboardv3?GameDate=2023-02-07&LeagueID=00` |
| `game_search-17` | match | 7/7 | `scoreboardv3?GameDate=2025-01-08&LeagueID=00` |
| `boxscore_stat-01` | match | 4/4 | `boxscoretraditionalv3?GameID=0021601076&LeagueID=00&endPeriod=10&endRange=0&rangeType=0&startPeriod=0&startRange=0` (game via leaguegamefinder (player, date)) |
| `boxscore_stat-02` | match | 6/6 | `boxscoretraditionalv3?GameID=0021400651&LeagueID=00&endPeriod=10&endRange=0&rangeType=0&startPeriod=0&startRange=0` (game via leaguegamefinder (player, date)) |
| `boxscore_stat-03` | match | 6/6 | `boxscoretraditionalv3?GameID=0022200917&LeagueID=00&endPeriod=10&endRange=0&rangeType=0&startPeriod=0&startRange=0` (game via leaguegamefinder (player, date)) |
| `boxscore_stat-04` | match | 17/17 | `boxscoretraditionalv3?GameID=0022300634&LeagueID=00&endPeriod=10&endRange=0&rangeType=0&startPeriod=0&startRange=0` (game via leaguegamefinder (player, date)) |
| `boxscore_stat-05` | match | 4/4 | `boxscoretraditionalv3?GameID=0026100329&LeagueID=00&endPeriod=10&endRange=0&rangeType=0&startPeriod=0&startRange=0` (game via scan of that date's boxscores (no player game log)) |
| `boxscore_stat-06` | match | 6/6 | `boxscoretraditionalv3?GameID=0040400407&LeagueID=00&endPeriod=10&endRange=0&rangeType=0&startPeriod=0&startRange=0` (game via leaguegamelog playoffs: game 7 of the series by date) |
| `boxscore_stat-07` | match | 8/8 | `boxscoretraditionalv3?GameID=0042000406&LeagueID=00&endPeriod=10&endRange=0&rangeType=0&startPeriod=0&startRange=0` (game via leaguegamelog playoffs: game 6 of the series by date) |
| `boxscore_stat-08` | match | 8/8 | `boxscoretraditionalv3?GameID=0041800217&LeagueID=00&endPeriod=10&endRange=0&rangeType=0&startPeriod=0&startRange=0` (game via leaguegamelog playoffs: game 7 of the series by date) |
| `boxscore_stat-09` | match | 8/8 | `boxscoretraditionalv3?GameID=0041200407&LeagueID=00&endPeriod=10&endRange=0&rangeType=0&startPeriod=0&startRange=0` (game via leaguegamelog playoffs: game 7 of the series by date) |
| `boxscore_stat-10` | match | 8/8 | `boxscoretraditionalv3?GameID=0042200405&LeagueID=00&endPeriod=10&endRange=0&rangeType=0&startPeriod=0&startRange=0` (game via game_id given; date from boxscoresummaryv3) |
| `boxscore_stat-11` | match | 4/4 | `boxscoretraditionalv3?GameID=0041800406&LeagueID=00&endPeriod=10&endRange=0&rangeType=0&startPeriod=0&startRange=0` (game via scoreboardv3) |
| `boxscore_stat-12` | match | 4/4 | `boxscoretraditionalv3?GameID=0042000405&LeagueID=00&endPeriod=10&endRange=0&rangeType=0&startPeriod=0&startRange=0` (game via scoreboardv3) |
| `boxscore_stat-13` | match | 4/4 | `boxscoretraditionalv3?GameID=0041500406&LeagueID=00&endPeriod=10&endRange=0&rangeType=0&startPeriod=0&startRange=0` (game via leaguegamefinder (player, date)) |
| `boxscore_stat-14` | match | 4/4 | `boxscoretraditionalv3?GameID=0048700060&LeagueID=00&endPeriod=10&endRange=0&rangeType=0&startPeriod=0&startRange=0` (game via leaguegamefinder (player, date)) |
| `boxscore_stat-15` | match | 4/4 | `boxscoretraditionalv3?GameID=0022301229&LeagueID=00&endPeriod=10&endRange=0&rangeType=0&startPeriod=0&startRange=0` (game via leaguegamefinder (player, date)) |
| `boxscore_stat-16` | match | 4/4 | `boxscoretraditionalv3?GameID=0022300608&LeagueID=00&endPeriod=10&endRange=0&rangeType=0&startPeriod=0&startRange=0` (game via leaguegamefinder (player, date)) |
| `boxscore_stat-17` | match | 4/4 | `boxscoretraditionalv3?GameID=0048200043&LeagueID=00&endPeriod=10&endRange=0&rangeType=0&startPeriod=0&startRange=0` (game via scan of that date's boxscores (no player game log)) |
| `boxscore_stat-18` | match | 6/6 | `boxscoretraditionalv3?GameID=0021100158&LeagueID=00&endPeriod=10&endRange=0&rangeType=0&startPeriod=0&startRange=0` (game via leaguegamefinder (player, date)) |
| `playoff_series-01` | match | 8/8 | `leaguegamelog?Counter=0&Direction=ASC&LeagueID=00&PlayerOrTeam=T&Season=1989-90&SeasonType=Playoffs&Sorter=DATE` (+ leaguestandings for conference) |
| `playoff_series-02` | match | 8/8 | `leaguegamelog?Counter=0&Direction=ASC&LeagueID=00&PlayerOrTeam=T&Season=1980-81&SeasonType=Playoffs&Sorter=DATE` (+ leaguestandings for conference) |
| `playoff_series-03` | match | 8/8 | `leaguegamelog?Counter=0&Direction=ASC&LeagueID=00&PlayerOrTeam=T&Season=2011-12&SeasonType=Playoffs&Sorter=DATE` (+ leaguestandings for conference) |
| `playoff_series-04` | match | 8/8 | `leaguegamelog?Counter=0&Direction=ASC&LeagueID=00&PlayerOrTeam=T&Season=2013-14&SeasonType=Playoffs&Sorter=DATE` (+ leaguestandings for conference) |
| `playoff_series-05` | match | 8/8 | `leaguegamelog?Counter=0&Direction=ASC&LeagueID=00&PlayerOrTeam=T&Season=2011-12&SeasonType=Playoffs&Sorter=DATE` (+ leaguestandings for conference) |
| `playoff_series-06` | match | 8/8 | `leaguegamelog?Counter=0&Direction=ASC&LeagueID=00&PlayerOrTeam=T&Season=2018-19&SeasonType=Playoffs&Sorter=DATE` (+ leaguestandings for conference) |
| `playoff_series-07` | match | 8/8 | `leaguegamelog?Counter=0&Direction=ASC&LeagueID=00&PlayerOrTeam=T&Season=1981-82&SeasonType=Playoffs&Sorter=DATE` (+ leaguestandings for conference) |
| `playoff_series-08` | match | 8/8 | `leaguegamelog?Counter=0&Direction=ASC&LeagueID=00&PlayerOrTeam=T&Season=2018-19&SeasonType=Playoffs&Sorter=DATE` (+ leaguestandings for conference) |
| `playoff_series-09` | match | 8/8 | `leaguegamelog?Counter=0&Direction=ASC&LeagueID=00&PlayerOrTeam=T&Season=1957-58&SeasonType=Playoffs&Sorter=DATE` (+ leaguestandings for conference) |
| `playoff_series-10` | match | 8/8 | `leaguegamelog?Counter=0&Direction=ASC&LeagueID=00&PlayerOrTeam=T&Season=1996-97&SeasonType=Playoffs&Sorter=DATE` (+ leaguestandings for conference) |
| `playoff_series-11` | match | 8/8 | `leaguegamelog?Counter=0&Direction=ASC&LeagueID=00&PlayerOrTeam=T&Season=2006-07&SeasonType=Playoffs&Sorter=DATE` (+ leaguestandings for conference) |
| `playoff_series-12` | match | 8/8 | `leaguegamelog?Counter=0&Direction=ASC&LeagueID=00&PlayerOrTeam=T&Season=2005-06&SeasonType=Playoffs&Sorter=DATE` (+ leaguestandings for conference) |
| `playoff_series-13` | match | 8/8 | `leaguegamelog?Counter=0&Direction=ASC&LeagueID=00&PlayerOrTeam=T&Season=2022-23&SeasonType=Playoffs&Sorter=DATE` (+ leaguestandings for conference) |
| `playoff_series-14` | match | 8/8 | `leaguegamelog?Counter=0&Direction=ASC&LeagueID=00&PlayerOrTeam=T&Season=1998-99&SeasonType=Playoffs&Sorter=DATE` (+ leaguestandings for conference) |
| `playoff_series-15` | match | 8/8 | `leaguegamelog?Counter=0&Direction=ASC&LeagueID=00&PlayerOrTeam=T&Season=1995-96&SeasonType=Playoffs&Sorter=DATE` (+ leaguestandings for conference) |
| `playoff_series-16` | match | 8/8 | `leaguegamelog?Counter=0&Direction=ASC&LeagueID=00&PlayerOrTeam=T&Season=1970-71&SeasonType=Playoffs&Sorter=DATE` (+ leaguestandings for conference) |
| `postseason_summary-01` | match | 20/20 | `leaguegamelog?Counter=0&Direction=ASC&LeagueID=00&PlayerOrTeam=T&Season=1970-71&SeasonType=Playoffs&Sorter=DATE` (+ leaguestandings for conference) |
| `postseason_summary-02` | match | 15/15 | `leaguegamelog?Counter=0&Direction=ASC&LeagueID=00&PlayerOrTeam=T&Season=1975-76&SeasonType=Playoffs&Sorter=DATE` (+ leaguestandings for conference) |
| `postseason_summary-03` | DIFFERS | 14/15 | `leaguegamelog?Counter=0&Direction=ASC&LeagueID=00&PlayerOrTeam=T&Season=1955-56&SeasonType=Playoffs&Sorter=DATE` (+ leaguestandings for conference) |
| `postseason_summary-04` | match | 10/10 | `leaguegamelog?Counter=0&Direction=ASC&LeagueID=00&PlayerOrTeam=T&Season=1968-69&SeasonType=Playoffs&Sorter=DATE` (+ leaguestandings for conference) |
| `postseason_summary-05` | match | 9/9 | `leaguegamelog?Counter=0&Direction=ASC&LeagueID=00&PlayerOrTeam=T&Season=2016-17&SeasonType=Playoffs&Sorter=DATE` (+ leaguestandings for conference) |
| `postseason_summary-06` | match | 9/9 | `leaguegamelog?Counter=0&Direction=ASC&LeagueID=00&PlayerOrTeam=T&Season=1969-70&SeasonType=Playoffs&Sorter=DATE` (+ leaguestandings for conference) |
| `postseason_summary-07` | match | 25/25 | `leaguegamelog?Counter=0&Direction=ASC&LeagueID=00&PlayerOrTeam=T&Season=1994-95&SeasonType=Playoffs&Sorter=DATE` (+ leaguestandings for conference) |
| `postseason_summary-08` | match | 20/20 | `leaguegamelog?Counter=0&Direction=ASC&LeagueID=00&PlayerOrTeam=T&Season=2013-14&SeasonType=Playoffs&Sorter=DATE` (+ leaguestandings for conference) |
| `postseason_summary-09` | match | 25/25 | `leaguegamelog?Counter=0&Direction=ASC&LeagueID=00&PlayerOrTeam=T&Season=2003-04&SeasonType=Playoffs&Sorter=DATE` (+ leaguestandings for conference) |
| `postseason_summary-10` | match | 25/25 | `leaguegamelog?Counter=0&Direction=ASC&LeagueID=00&PlayerOrTeam=T&Season=2005-06&SeasonType=Playoffs&Sorter=DATE` (+ leaguestandings for conference) |
| `postseason_summary-11` | match | 20/20 | `leaguegamelog?Counter=0&Direction=ASC&LeagueID=00&PlayerOrTeam=T&Season=2020-21&SeasonType=Playoffs&Sorter=DATE` (+ leaguestandings for conference) |
| `postseason_summary-12` | match | 9/9 | `leaguegamelog?Counter=0&Direction=ASC&LeagueID=00&PlayerOrTeam=T&Season=1983-84&SeasonType=Playoffs&Sorter=DATE` (+ leaguestandings for conference) |
| `postseason_summary-13` | match | 25/25 | `leaguegamelog?Counter=0&Direction=ASC&LeagueID=00&PlayerOrTeam=T&Season=1997-98&SeasonType=Playoffs&Sorter=DATE` (+ leaguestandings for conference) |
| `postseason_summary-14` | match | 25/25 | `leaguegamelog?Counter=0&Direction=ASC&LeagueID=00&PlayerOrTeam=T&Season=1989-90&SeasonType=Playoffs&Sorter=DATE` (+ leaguestandings for conference) |
| `postseason_summary-15` | match | 15/15 | `leaguegamelog?Counter=0&Direction=ASC&LeagueID=00&PlayerOrTeam=T&Season=1963-64&SeasonType=Playoffs&Sorter=DATE` (+ leaguestandings for conference) |
| `postseason_summary-16` | match | 15/15 | `leaguegamelog?Counter=0&Direction=ASC&LeagueID=00&PlayerOrTeam=T&Season=2020-21&SeasonType=Playoffs&Sorter=DATE` (+ leaguestandings for conference) |
| `postseason_summary-17` | match | 15/15 | `leaguegamelog?Counter=0&Direction=ASC&LeagueID=00&PlayerOrTeam=T&Season=2023-24&SeasonType=Playoffs&Sorter=DATE` (+ leaguestandings for conference) |
| `postseason_summary-18` | match | 20/20 | `leaguegamelog?Counter=0&Direction=ASC&LeagueID=00&PlayerOrTeam=T&Season=2018-19&SeasonType=Playoffs&Sorter=DATE` (+ leaguestandings for conference) |
| `game_search-23` | match | 7/7 | `scoreboardv3?GameDate=2018-04-11&LeagueID=00` |
| `postseason_summary-21` | match | 20/20 | `leaguegamelog?Counter=0&Direction=ASC&LeagueID=00&PlayerOrTeam=T&Season=2001-02&SeasonType=Playoffs&Sorter=DATE` (+ leaguestandings for conference) |
| `player_season_stats-01` | match | 6/6 | `playercareerstats?PlayerID=201939&PerMode=Totals&LeagueID=00` [SeasonTotalsRegularSeason] |
| `player_season_stats-02` | match | 4/4 | `playercareerstats?PlayerID=201566&PerMode=Totals&LeagueID=00` [SeasonTotalsRegularSeason] |
| `player_season_stats-03` | match | 4/4 | `playercareerstats?PlayerID=76375&PerMode=Totals&LeagueID=00` [SeasonTotalsRegularSeason] |
| `player_season_stats-04` | match | 4/4 | `playercareerstats?PlayerID=202695&PerMode=Totals&LeagueID=00` [SeasonTotalsPostSeason] |
| `player_season_stats-05` | match | 4/4 | `playercareerstats?PlayerID=76631&PerMode=Totals&LeagueID=00` [SeasonTotalsRegularSeason] |
| `player_season_stats-06` | match | 3/3 | `playercareerstats?PlayerID=203507&PerMode=Totals&LeagueID=00` [SeasonTotalsRegularSeason] |
| `player_season_stats-07` | match | 4/4 | `playercareerstats?PlayerID=202710&PerMode=Totals&LeagueID=00` [SeasonTotalsRegularSeason] |
| `player_season_stats-08` | match | 12/12 | `playercareerstats?PlayerID=2546&PerMode=Totals&LeagueID=00` [SeasonTotalsRegularSeason] |
| `player_season_stats-09` | match | 4/4 | `playercareerstats?PlayerID=1628983&PerMode=Totals&LeagueID=00` [SeasonTotalsRegularSeason] |
| `player_season_stats-10` | match | 3/3 | `playercareerstats?PlayerID=1717&PerMode=Totals&LeagueID=00` [SeasonTotalsRegularSeason] |
| `player_season_stats-11` | match | 4/4 | `playercareerstats?PlayerID=101108&PerMode=Totals&LeagueID=00` [SeasonTotalsRegularSeason] |
| `player_season_stats-12` | match | 4/4 | `playercareerstats?PlayerID=165&PerMode=Totals&LeagueID=00` [SeasonTotalsPostSeason] |
| `player_season_stats-13` | match | 4/4 | `playercareerstats?PlayerID=600015&PerMode=Totals&LeagueID=00` [SeasonTotalsRegularSeason] |
| `player_season_stats-14` | match | 4/4 | `playercareerstats?PlayerID=1630162&PerMode=Totals&LeagueID=00` [SeasonTotalsRegularSeason] |
| `player_season_stats-15` | match | 4/4 | `playercareerstats?PlayerID=23&PerMode=Totals&LeagueID=00` [SeasonTotalsRegularSeason] |
| `player_season_stats-16` | match | 12/12 | `playercareerstats?PlayerID=1495&PerMode=Totals&LeagueID=00` [SeasonTotalsPostSeason] |
| `player_season_stats-17` | match | 4/4 | `playercareerstats?PlayerID=1503&PerMode=Totals&LeagueID=00` [SeasonTotalsRegularSeason] |
| `player_season_stats-18` | match | 4/4 | `playercareerstats?PlayerID=201142&PerMode=Totals&LeagueID=00` [SeasonTotalsRegularSeason] |
| `team_records-01` | match | 6/6 | `teamyearbyyearstats?LeagueID=00&PerMode=Totals&SeasonType=Regular+Season&TeamID=1610612744` |
| `team_records-02` | match | 6/6 | `teamyearbyyearstats?LeagueID=00&PerMode=Totals&SeasonType=Regular+Season&TeamID=1610612741` |
| `team_records-03` | match | 9/9 | `leaguestandings?LeagueID=00&Season=2006-07&SeasonType=Regular+Season&SeasonYear=` |
| `team_records-04` | match | 9/9 | `leaguestandings?LeagueID=00&Season=1997-98&SeasonType=Regular+Season&SeasonYear=` |
| `team_records-05` | match | 8/8 | `leaguestandings?LeagueID=00&Season=1985-86&SeasonType=Regular+Season&SeasonYear=` |
| `team_records-06` | match | 6/6 | `teamyearbyyearstats?LeagueID=00&PerMode=Totals&SeasonType=Regular+Season&TeamID=1610612766` |
| `team_records-07` | match | 6/6 | `teamyearbyyearstats?LeagueID=00&PerMode=Totals&SeasonType=Regular+Season&TeamID=1610612760` |
| `team_records-08` | match | 6/6 | `teamyearbyyearstats?LeagueID=00&PerMode=Totals&SeasonType=Regular+Season&TeamID=1610612755` |
| `team_records-09` | match | 6/6 | `teamyearbyyearstats?LeagueID=00&PerMode=Totals&SeasonType=Regular+Season&TeamID=1610612752` |
| `team_records-10` | match | 6/6 | `teamyearbyyearstats?LeagueID=00&PerMode=Totals&SeasonType=Regular+Season&TeamID=1610612738` |
| `team_records-11` | match | 6/6 | `teamyearbyyearstats?LeagueID=00&PerMode=Totals&SeasonType=Regular+Season&TeamID=1610612763` |
| `team_records-12` | match | 6/6 | `teamyearbyyearstats?LeagueID=00&PerMode=Totals&SeasonType=Regular+Season&TeamID=1610612740` |
| `team_records-13` | match | 6/6 | `teamyearbyyearstats?LeagueID=00&PerMode=Totals&SeasonType=Regular+Season&TeamID=1610612758` |
| `team_records-15` | match | 6/6 | `teamyearbyyearstats?LeagueID=00&PerMode=Totals&SeasonType=Regular+Season&TeamID=1610612747` |
| `team_records-16` | match | 6/6 | `teamyearbyyearstats?LeagueID=00&PerMode=Totals&SeasonType=Regular+Season&TeamID=1610612762` |
| `season_leaders-01` | match | 6/6 | `leagueleaders?LeagueID=00&PerMode=PerGame&Scope=S&Season=1991-92&SeasonType=Regular+Season&StatCategory=REB&ActiveFlag=` |
| `season_leaders-02` | match | 6/6 | `leagueleaders?LeagueID=00&PerMode=PerGame&Scope=S&Season=1986-87&SeasonType=Regular+Season&StatCategory=PTS&ActiveFlag=` |
| `season_leaders-03` | match | 6/6 | `leagueleaders?LeagueID=00&PerMode=Totals&Scope=S&Season=2000-01&SeasonType=Regular+Season&StatCategory=STL&ActiveFlag=` |
| `season_leaders-04` | match | 6/6 | `leagueleaders?LeagueID=00&PerMode=Totals&Scope=S&Season=1990-91&SeasonType=Regular+Season&StatCategory=AST&ActiveFlag=` |
| `season_leaders-05` | match | 5/5 | `leagueleaders?LeagueID=00&PerMode=Totals&Scope=S&Season=2008-09&SeasonType=Regular+Season&StatCategory=FG3_PCT&ActiveFlag=` |
| `season_leaders-06` | match | 6/6 | `leagueleaders?LeagueID=00&PerMode=Totals&Scope=S&Season=1999-00&SeasonType=Regular+Season&StatCategory=FG_PCT&ActiveFlag=` |
| `season_leaders-07` | match | 6/6 | `leagueleaders?LeagueID=00&PerMode=PerGame&Scope=S&Season=2015-16&SeasonType=Playoffs&StatCategory=AST&ActiveFlag=` |
| `season_leaders-08` | match | 5/5 | `leagueleaders?LeagueID=00&PerMode=Totals&Scope=S&Season=2004-05&SeasonType=Regular+Season&StatCategory=BLK&ActiveFlag=` |
| `season_leaders-09` | match | 5/5 | `leagueleaders?LeagueID=00&PerMode=Totals&Scope=S&Season=1987-88&SeasonType=Regular+Season&StatCategory=FG3M&ActiveFlag=` |
| `season_leaders-10` | match | 5/5 | `leagueleaders?LeagueID=00&PerMode=Totals&Scope=S&Season=2011-12&SeasonType=Regular+Season&StatCategory=FTM&ActiveFlag=` |
| `season_leaders-11` | match | 6/6 | `leagueleaders?LeagueID=00&PerMode=PerGame&Scope=S&Season=2002-03&SeasonType=Playoffs&StatCategory=REB&ActiveFlag=` |
| `season_leaders-12` | match | 6/6 | `leagueleaders?LeagueID=00&PerMode=PerGame&Scope=S&Season=2013-14&SeasonType=Regular+Season&StatCategory=MIN&ActiveFlag=` |
| `season_leaders-13` | match | 6/6 | `leagueleaders?LeagueID=00&PerMode=Totals&Scope=S&Season=2005-06&SeasonType=Regular+Season&StatCategory=TOV&ActiveFlag=` |
| `season_leaders-14` | match | 6/6 | `leagueleaders?LeagueID=00&PerMode=PerGame&Scope=S&Season=2018-19&SeasonType=Regular+Season&StatCategory=DREB&ActiveFlag=` |
| `season_leaders-15` | match | 6/6 | `leagueleaders?LeagueID=00&PerMode=Totals&Scope=S&Season=1996-97&SeasonType=Regular+Season&StatCategory=OREB&ActiveFlag=` |
| `season_leaders-16` | match | 6/6 | `leagueleaders?LeagueID=00&PerMode=PerGame&Scope=S&Season=2024-25&SeasonType=Regular+Season&StatCategory=BLK&ActiveFlag=` |
| `season_leaders-17` | match | 6/6 | `leagueleaders?LeagueID=00&PerMode=PerGame&Scope=S&Season=1974-75&SeasonType=Regular+Season&StatCategory=PTS&ActiveFlag=` |
| `career_stats-01` | match | 4/4 | `playercareerstats?PlayerID=76127&PerMode=Totals&LeagueID=00` [CareerTotalsRegularSeason] |
| `career_stats-02` | match | 4/4 | `playercareerstats?PlayerID=304&PerMode=Totals&LeagueID=00` [CareerTotalsRegularSeason] |
| `career_stats-03` | match | 4/4 | `alltimeleadersgrids?LeagueID=00&PerMode=Totals&SeasonType=Regular+Season&TopX=250` [STLLeaders] |
| `career_stats-04` | match | 4/4 | `alltimeleadersgrids?LeagueID=00&PerMode=Totals&SeasonType=Regular+Season&TopX=250` [FG3MLeaders] |
| `career_stats-05` | match | 2/2 | `alltimeleadersgrids?LeagueID=00&PerMode=Totals&SeasonType=Regular+Season&TopX=250` [PTSLeaders] |
| `career_stats-06` | match | 4/4 | `playercareerstats?PlayerID=1495&PerMode=Totals&LeagueID=00` [CareerTotalsPostSeason] |
| `career_stats-07` | match | 8/8 | `playercareerstats?PlayerID=893&PerMode=Totals&LeagueID=00` [CareerTotalsRegularSeason] |
| `career_stats-08` | match | 3/3 | `playercareerstats?PlayerID=397&PerMode=Totals&LeagueID=00` [CareerTotalsRegularSeason] |
| `career_stats-09` | match | 4/4 | `alltimeleadersgrids?LeagueID=00&PerMode=Totals&SeasonType=Playoffs&TopX=250` [ASTLeaders] |
| `career_stats-10` | match | 4/4 | `alltimeleadersgrids?LeagueID=00&PerMode=Totals&SeasonType=Regular+Season&TopX=250` [OREBLeaders] |
| `career_stats-11` | match | 2/2 | `alltimeleadersgrids?LeagueID=00&PerMode=Totals&SeasonType=Regular+Season&TopX=250` [REBLeaders] |
| `career_stats-12` | match | 4/4 | `playercareerstats?PlayerID=252&PerMode=Totals&LeagueID=00` [CareerTotalsPostSeason] |
| `career_stats-13` | match | 4/4 | `playercareerstats?PlayerID=77142&PerMode=Totals&LeagueID=00` [CareerTotalsRegularSeason] |
| `career_stats-14` | match | 4/4 | `playercareerstats?PlayerID=87&PerMode=Totals&LeagueID=00` [CareerTotalsRegularSeason] |
| `career_stats-15` | match | 4/4 | `alltimeleadersgrids?LeagueID=00&PerMode=Totals&SeasonType=Regular+Season&TopX=250` [TOVLeaders] |
| `career_stats-16` | match | 4/4 | `alltimeleadersgrids?LeagueID=00&PerMode=Totals&SeasonType=Regular+Season&TopX=250` [FTMLeaders] |
| `career_stats-17` | match | 3/3 | `playercareerstats?PlayerID=959&PerMode=Totals&LeagueID=00` [CareerTotalsRegularSeason] |
| `career_stats-19` | match | 4/4 | `playercareerstats?PlayerID=1641705&PerMode=Totals&LeagueID=00` [CareerTotalsRegularSeason] |
| `team_records-21` | match | 6/6 | `teamyearbyyearstats?LeagueID=00&PerMode=Totals&SeasonType=Regular+Season&TeamID=1610612757` |
| `team_records-22` | match | 10/10 | `leaguestandings?LeagueID=00&Season=1992-93&SeasonType=Regular+Season&SeasonYear=` |
| `season_leaders-24` | match | 6/6 | `leagueleaders?LeagueID=00&PerMode=PerGame&Scope=S&Season=2006-07&SeasonType=Regular+Season&StatCategory=REB&ActiveFlag=` |
| `season_leaders-25` | match | 6/6 | `leagueleaders?LeagueID=00&PerMode=Totals&Scope=S&Season=2002-03&SeasonType=Regular+Season&StatCategory=FGM&ActiveFlag=` |
| `career_stats-27` | match | 2/2 | `alltimeleadersgrids?LeagueID=00&PerMode=Totals&SeasonType=Regular+Season&TopX=250` [BLKLeaders] |

## Keys moved to the exposed development file

These seven keys are now in `server/tests/ask/fixtures/answers/unseen-three-exposed-dev-answers.json`, with ids and contents unchanged, matching `server/tests/ask/fixtures/eval/unseen-three-exposed-dev.json`. Four existed before today; three (`postseason_summary-19`, `team_records-20`, `season_leaders-23`) were written today from stats.nba and Basketball-Reference before the questions were replaced. All seven match stats.nba (48 of 48 source checks). They are not part of the counts above.

| Case | Result | Source checks matched | stats.nba request |
|---|---|---|---|
| `game_search-11` | match | 7/7 | `scoreboardv3?GameDate=2016-03-07&LeagueID=00` |
| `team_records-14` | match | 6/6 | `teamyearbyyearstats?LeagueID=00&PerMode=Totals&SeasonType=Regular+Season&TeamID=1610612749` |
| `career_stats-18` | match | 2/2 | `alltimeleadersgrids?LeagueID=00&PerMode=Totals&SeasonType=Regular+Season&TopX=250` [PTSLeaders] |
| `season_leaders-19` | match | 6/6 | `leagueleaders?LeagueID=00&PerMode=PerGame&Scope=S&Season=2013-14&SeasonType=Regular+Season&StatCategory=PTS&ActiveFlag=` |
| `postseason_summary-19` | match | 10/10 | `leaguegamelog?Counter=0&Direction=ASC&LeagueID=00&PlayerOrTeam=T&Season=2020-21&SeasonType=Playoffs&Sorter=DATE` (+ leaguestandings for conference) |
| `season_leaders-23` | match | 7/7 | `leagueleaders?LeagueID=00&PerMode=Totals&Scope=S&Season=2018-19&SeasonType=Regular+Season&StatCategory=PF&ActiveFlag=` |
| `team_records-20` | match | 10/10 | `leaguestandings?LeagueID=00&Season=2015-16&SeasonType=Regular+Season&SeasonYear=` |
