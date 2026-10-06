# Ask test set three: review sheet

This is a list of 179 new questions that Ask has never seen. We'll use them to grade Ask
before release. Each row gives the question and what Ask should do with it. Ask can
answer it, ask a follow-up question, or say it can't answer.

**What to check:** would a fan expect that response? Are the facts in the last column
right? You don't need to check every row closely. The facts were checked against
basketball-reference.com and are marked ✅ verified, ❌ wrong, or ⚠️ couldn't verify.

**Status:** the owner decided items 1 and 3 under "Needs your decision" on 2026-10-01.
Item 2 (G-21) got no reply, so it is kept as recommended. The file, the tables and the
counts below already include those decisions. On 2026-10-06 seven questions were
replaced with new ones (see "Replaced on Oct 6" just below). **Those seven new rows still
need your review.**

**How to reply:** send case codes with a note, e.g. "B-15 swap date", "C-19 both OK",
"Y-11 should be season total". Any row you don't mention counts as approved.

**Case codes:** the letter is the question type and the number matches the file
(`server/tests/ask/fixtures/eval/unseen-three-draft.json`). B-16 is the file's
`boxscore_stat-16`. G = games on a date, B = box score, S = playoff series,
R = playoff run summary, Y = player season stats, T = team records, L = season leaders,
C = career stats.

Sources: date pages, box scores, schedules, playoff pages, league pages and player pages
on [basketball-reference.com](https://www.basketball-reference.com). Team nicknames
come from Wikipedia, and one game ID from nba.com. Everything was checked on
2026-10-01, except the seven rows added on 2026-10-06, whose facts are marked ⚠️.

---

## Replaced on Oct 6: seven new questions to review

Ask was changed on Oct 6 with seven of these questions in view, so they no longer count
as "never seen". They were taken out of this set and kept as ordinary regression tests
(`server/tests/ask/fixtures/eval/unseen-three-exposed-dev.json`). Each was replaced by a
new question of the same kind. The new questions have new numbers, and the old numbers
are not reused, so G-11, T-14, T-20, L-19, L-23, R-19 and C-18 no longer exist in the
tables. Older notes on this page that mention those codes describe the removed questions.

Nobody has tried the new questions on Ask. Their facts come from memory and were not
checked online (⚠️).

| New | Replaces | Question | What Ask should do | Please rule on |
| --- | --- | --- | --- | --- |
| G-23 | G-11 | Was there a Timberwoves game on April 11, 2018? | Timberwolves games on Apr 11, 2018, or ask which team (both OK) | Does the Sep 30 typo rule (answer, and asking also counts) apply here too? Is the date right? |
| T-21 | T-14 | Will you show me the Trail Blazers' record from 1990-91? | Blazers' record, 1990-91 | — |
| T-22 | T-20 | Who finished with the worst record in the NBA in 1992-93? | League standings, 1992-93 | Uses the Oct 6 "best record" rule for "worst record" |
| L-24 | L-19 | Who took the rebounding crown in 2006-07? | Top 10 in rebounds per game, 2006-07 | The Sep 30 ruling named only the "scoring title". Is "rebounding crown" also per game, or should Ask ask "per game or total?" |
| L-25 | L-23 | Who sank the most field goals in total in 2002-03? | Top 10 in total field goals made, 2002-03 | — |
| R-21 | R-19 | Take me through Sacramento's 2002 playoffs. | Kings' 2002 playoff run | — |
| C-27 | C-18 | What is Hakeem Olajuwon's ranking on the career blocks list? | Hakeem Olajuwon's rank on the all-time blocks list | — |

---

## Needs your decision (items 1 and 3 decided 2026-10-01)

### 1. Seven questions point at a game that didn't happen or a player who didn't play ❌

**Decided 2026-10-01: Option B, with G-02 kept.** G-02 stays as a deliberate "no games
that day" test. The other six were swapped in the file: G-04 is now March 4, 1983;
G-10 is now asked on Wed Jan 8, 2025 (last week = Dec 30, 2024–Jan 5, 2025); G-11 is now
March 7, 2016; G-12 is now 2/2/2019; B-15 is now asked on Dec 8, 2023 (last night =
Dec 7, 2023); B-19 is now February 21, 2014. The table shows the questions as they were
before the swap.

None of this changes what Ask should do. Ask still has to understand the question, and
the answer would be "no games that day" or "he didn't play." The trouble is that the
question doesn't match real events, so the answers can't be spot-checked against a
real game. It also means seven questions all test an empty result.

| Code | Question | What's wrong | Suggested swap |
| --- | --- | --- | --- |
| G-02 | Show NBA games played in Salt Lake City on April 20, 1997. | No game in Salt Lake City that day. The Jazz won at Sacramento ([date](https://www.basketball-reference.com/boxscores/?month=4&day=20&year=1997), [Jazz schedule](https://www.basketball-reference.com/teams/UTA/1997_games.html)) | **April 19, 1997** (Jazz hosted Minnesota) |
| G-04 | Games in Kansas City on March 3, 1983 | No game in Kansas City. The Kings played at Detroit ([date](https://www.basketball-reference.com/boxscores/?month=3&day=3&year=1983), [Kings schedule](https://www.basketball-reference.com/teams/KCK/1983_games.html)) | **March 4, 1983** (Kings hosted Indiana) |
| G-10 | Games in Oklahoma City last week (asked Wed Jan 15, 2025) | The Thunder were on the road all of Jan 6–12 (at CLE, NYK, WAS), so there were no games in OKC ([Thunder schedule](https://www.basketball-reference.com/teams/OKC/2025_games.html)) | Change the ask date to **Wed Jan 8, 2025**. "Last week" is then Dec 30–Jan 5, with 4 Thunder home games |
| G-11 | Warriros games on March 8, 2016 | The Warriors didn't play Mar 8 ([date](https://www.basketball-reference.com/boxscores/?month=3&day=8&year=2016), [Warriors schedule](https://www.basketball-reference.com/teams/GSW/2016_games.html)) | **March 7, 2016** (vs Orlando) or **March 9** (vs Utah) |
| G-12 | Pelicans games on 2/1/2019 | The Pelicans didn't play Feb 1 ([date](https://www.basketball-reference.com/boxscores/?month=2&day=1&year=2019), [Pelicans schedule](https://www.basketball-reference.com/teams/NOP/2019_games.html)) | **2/2/2019** (at San Antonio) |
| B-15 | Haliburton's dimes last night? (asked Jan 11, 2024) | The Pacers played Jan 10, but Haliburton was listed inactive (injured) ([box score](https://www.basketball-reference.com/boxscores/202401100IND.html)) | Change the ask date to **Dec 8, 2023**. "Last night" is then Dec 7, the in-season tournament semifinal vs the Bucks, where he had 15 assists ([box score](https://www.basketball-reference.com/boxscores/202312070MIL.html)) |
| B-19 | How many rebounds did Gasol grab on February 20, 2014? | Neither the Lakers (Pau) nor the Grizzlies (Marc) played that day ([date](https://www.basketball-reference.com/boxscores/?month=2&day=20&year=2014)) | **February 21, 2014**. Both played that night: Pau had 7 rebounds vs Boston ([box](https://www.basketball-reference.com/boxscores/201402210LAL.html)) and Marc had 10 vs the Clippers ([box](https://www.basketball-reference.com/boxscores/201402210MEM.html)). The "ask which Gasol" label gets stronger |

- **Option A, keep as is.** The labels are still correct, and Ask is graded on how it
  understood the question, not on the answer.
- **Option B, swap to the dates above.** The intended response stays the same, and the
  answers become checkable.
- **Recommendation: B.** It's cheap, and the file isn't frozen yet. If you want to keep
  one deliberate "nothing that day" question, G-02 is the most natural one to keep.

### 2. G-21: the game in the question didn't exist ❌ (low stakes)

"Will the Lakers beat the Suns tonight?" is asked on Jan 8, 2025. The Lakers didn't play
that day ([date](https://www.basketball-reference.com/boxscores/?month=1&day=8&year=2025)).
It doesn't matter, because Ask should refuse to predict either way. **Recommendation:
keep.**

### 3. C-19: "How many blocks has Victor Wembanyama recorded?" (label unclear)

**Decided 2026-10-01: Ask answers with his career total blocks.** "Has recorded", "has
had", "has scored" and similar wording about a player's count means career. Asking
"career or one season?" no longer counts as correct for this question. The text below
is the question as it was put to the owner.

- **Current label:** Ask asks "career or one season?"
- **Alternative:** answer with his career total. "Has recorded" reads like "so far in
  his career" to most fans.
- **Recommendation: both OK.** Asking is the cautious house rule from earlier rounds,
  but answering with the career total is reasonable and shouldn't be marked wrong.

### Also decided 2026-10-01: full career lines show per game first

C-07 "Michael Jordan career stats" now expects Jordan's career line as per-game
averages, with totals on the toggle. A single career stat with no measure ("Magic
Johnson's lifetime assists") stays a total.

### Already decided on Sep 30 (no action needed)

These are listed so you don't re-review them. They're marked "(decided Sep 30)" in the
tables.
- The three typo questions (G-11, B-16, Y-18) answer with the obvious team or player,
  and asking which one also counts as correct.
- L-19 "scoring title" now answers points per game.
- These five keep their labels: R-18, B-20, B-21, Y-22 and B-23.

### Decided on Oct 6

These three questions were later removed from the set (see "Replaced on Oct 6"). The
rulings still stand as rules.

- R-19 "New York's 2021 postseason" answers with the Knicks.
- T-20 "best record in 2015-16" answers with the league standings.
- L-23 "personal fouls in 2018-19" answers with the season-total fouls leaders.

### ⚠️ items: only the Oct 6 replacements

Every fact below was confirmed or found wrong, except in the seven rows added on Oct 6
(G-23, T-21, T-22, L-24, L-25, R-21, C-27). Their facts were written from memory and
were not checked online.

---

## Rules Ask follows (so you don't flag these row by row)

- **No "per game" or "total" in the question:** one season gives per game, a full
  career line gives per game (totals on the toggle), one career stat gives its total,
  and a season leaderboard for a counting stat makes Ask ask which one. Percentages are
  neither.
- **"Has recorded" / "has had" / "has scored"** about one named player, with no season
  or date, means his career total. "How many points does LeBron have?" still makes Ask
  ask "career or one season?".
- **Top N:** no number means top 10. Over 25 shows the top 25 with a note that 25 is
  the max. Ties are always shown.
- **Years:** a year with playoff words ("2019 Finals", "'98 playoff run") means the
  season ending that year (2018-19). A year without playoff words ("in 2018") makes Ask
  ask which season.
- **Relative dates** use New York time:
  - "Last week" is the previous Monday–Sunday.
  - "Last Tuesday" is the most recent Tuesday before today.
  - "Last five days" is today plus the four days before.
  - "This Saturday" is the Saturday of the current Monday–Sunday week.
- **Game searches** cover at most 7 days.
- **No season or date given:** Ask asks. It never guesses.
- **Old team names** count as today's franchise. The Buffalo Braves are the Clippers.
- **Cities:** "in/at <city>" means games played in that city. A city used as a team
  ("Brooklyn's run") means that team.
- **Season type:** regular season unless the question says playoffs or postseason.

## Counts (checked against the file)

| Question type | Answer | Follow-up | Can't answer | Total |
| --- | --- | --- | --- | --- |
| Games on a date (G) | 17 | 3 | 2 | 22 |
| Box score stats (B) | 18 | 3 | 3 | 24 |
| Playoff series (S) | 16 | 2 | 1 | 19 |
| Playoff summaries (R) | 19 | 0 | 1 | 20 |
| Player season stats (Y) | 18 | 4 | 3 | 25 |
| Team records & standings (T) | 17 | 2 | 1 | 20 |
| Season leaders (L) | 19 | 2 | 2 | 23 |
| Career stats (C) | 19 | 1 | 6 | 26 |
| **All** | **143** | **17** | **19** | **179** |

These match the file and its header. The seven Oct 6 replacements are all answerable
questions, like the seven they replaced, so the counts did not change. Their rows sit in
the answerable sections below, at the place of the question they replaced where that
question was listed there, otherwise at the end of the section.

---

## Games on a date

| Code | Question | What Ask should do | Facts |
| --- | --- | --- | --- |
| G-01 | What games did the Dubs play between November 2 and November 5, 2016? | Warriors games, Nov 2–5, 2016 | ✅ "Dubs" = Warriors ([wiki](https://en.wikipedia.org/wiki/Golden_State_Warriors)). ✅ They played Nov 3 vs OKC ([date](https://www.basketball-reference.com/boxscores/?month=11&day=3&year=2016)) and Nov 4 at the Lakers ([date](https://www.basketball-reference.com/boxscores/?month=11&day=4&year=2016)) |
| G-02 | Show NBA games played in Salt Lake City on April 20, 1997. | All games played in Salt Lake City (Jazz home games) on Apr 20, 1997 | ✅ No game in Salt Lake City that day (the Jazz won at Sacramento, [date](https://www.basketball-reference.com/boxscores/?month=4&day=20&year=1997)). Kept on purpose as the "no games that day" test *(decided Oct 1)* |
| G-03 | Any games at Madison Square Garden on February 2, 2009? | Games at MSG (Knicks home games) on Feb 2, 2009 | ✅ Lakers at Knicks, Kobe's 61-point game ([date](https://www.basketball-reference.com/boxscores/?month=2&day=2&year=2009)) |
| G-04 | Games in Kansas City on March 4, 1983 | Games played in Kansas City (the Kings' home then) on Mar 4, 1983 *(date swapped Oct 1)* | ✅ The Kings were in Kansas City in 1982-83 ([season](https://www.basketball-reference.com/leagues/NBA_1983.html)). ✅ Kings hosted Indiana ([Kings schedule](https://www.basketball-reference.com/teams/KCK/1983_games.html)) |
| G-05 | Did the Buffalo Braves play on January 10, 1975? | Buffalo Braves (today's Clippers) games on Jan 10, 1975 | ✅ Braves beat Cleveland at home ([date](https://www.basketball-reference.com/boxscores/?month=1&day=10&year=1975)) |
| G-06 | Rockets results from the last five days *(asked Fri Feb 14, 2025)* | Rockets games, Feb 10–14, 2025 | ✅ Rockets played Feb 12 and 13 ([schedule](https://www.basketball-reference.com/teams/HOU/2025_games.html)) |
| G-07 | What was on the schedule last Tuesday for Memphis? *(asked Thu Nov 21, 2024)* | Grizzlies games on Tue Nov 19, 2024 | ✅ Grizzlies hosted Denver ([date](https://www.basketball-reference.com/boxscores/?month=11&day=19&year=2024)) |
| G-08 | Is there anything on tonight involving the Spurs? *(asked Jan 8, 2025, 3pm)* | Spurs games on Jan 8, 2025 | ✅ Spurs at Milwaukee ([date](https://www.basketball-reference.com/boxscores/?month=1&day=8&year=2025)) |
| G-09 | Is the Heat playing this Saturday? *(asked Wed Mar 5, 2025)* | Heat games on Sat Mar 8, 2025 | ✅ Heat hosted Chicago ([date](https://www.basketball-reference.com/boxscores/?month=3&day=8&year=2025)) |
| G-10 | Games in Oklahoma City last week *(asked Wed Jan 8, 2025)* | Games played in Oklahoma City, Mon Dec 30, 2024–Sun Jan 5, 2025 *(ask date swapped Oct 1)* | ✅ 4 Thunder home games that week ([Thunder schedule](https://www.basketball-reference.com/teams/OKC/2025_games.html)) |
| G-23 | Was there a Timberwoves game on April 11, 2018? | Timberwolves games on Apr 11, 2018, or ask which team (both OK) *(added Oct 6, replaces G-11; needs review)* | ✅ Timberwolves hosted Denver and won 112-106 in overtime ([date](https://www.basketball-reference.com/boxscores/?month=4&day=11&year=2018)) |
| G-12 | Pelicans games on 2/2/2019 | Pelicans games on Feb 2, 2019 *(date swapped Oct 1)* | ✅ Pelicans at San Antonio ([Pelicans schedule](https://www.basketball-reference.com/teams/NOP/2019_games.html)) |
| G-13 | Were the Bullets in action on January 5, 1985? | Washington Bullets (today's Wizards) games on Jan 5, 1985 | ✅ Bullets hosted Detroit ([date](https://www.basketball-reference.com/boxscores/?month=1&day=5&year=1985)) |
| G-14 | Philadelphia Warriors games on March 2, 1962 | Philadelphia Warriors (today's Golden State) games on Mar 2, 1962 | ✅ Wilt's 100-point game vs the Knicks (played in Hershey, PA) ([date](https://www.basketball-reference.com/boxscores/?month=3&day=2&year=1962)) |
| G-15 | Show games from April 1 to April 3, 2015 in Chicago | Games played in Chicago, Apr 1–3, 2015 | ✅ Bulls hosted Detroit on Apr 3 ([date](https://www.basketball-reference.com/boxscores/?month=4&day=3&year=2015)) |
| G-16 | Show the Lakers games on the date I'm looking at *(scores page showing Feb 7, 2023)* | Lakers games on Feb 7, 2023 (date taken from the page) | ✅ Lakers vs OKC, the night LeBron passed Kareem ([date](https://www.basketball-reference.com/boxscores/?month=2&day=7&year=2023)) |
| G-17 | Who is playing tonight? *(asked 10:30pm New York time, Jan 8, 2025)* | All games on Jan 8, 2025 (New York date, even though it's already Jan 9 in UTC) | ✅ 8 games that night ([date](https://www.basketball-reference.com/boxscores/?month=1&day=8&year=2025)) |

## Box score stats

| Code | Question | What Ask should do | Facts |
| --- | --- | --- | --- |
| B-01 | How many points did Devin Booker drop on the Celtics on March 24, 2017? | Booker's points in the Mar 24, 2017 game vs Boston | ✅ Booker scored 70 at Boston ([box](https://www.basketball-reference.com/boxscores/201703240BOS.html)) |
| B-02 | Klay's field goals on January 23, 2015 | Klay Thompson's field goals made on Jan 23, 2015 | ✅ 16 FG and 52 pts vs Sacramento, the 37-point quarter ([box](https://www.basketball-reference.com/boxscores/201501230GSW.html)) |
| B-03 | Dame's three-pointers made on February 26, 2023 | Damian Lillard's 3-pointers made on Feb 26, 2023 | ✅ "Dame" = Lillard ([player](https://www.basketball-reference.com/players/l/lillada01.html)). ✅ 13 threes and 71 pts vs Houston ([box](https://www.basketball-reference.com/boxscores/202302260POR.html)) |
| B-04 | What was Luka's full stat line against Atlanta on January 26, 2024? | Luka Dončić's full line in the game vs Atlanta on Jan 26, 2024 | ✅ 73 pts at Atlanta ([box](https://www.basketball-reference.com/boxscores/202401260ATL.html)) |
| B-05 | Wilt's rebounds on March 2, 1962 | Wilt Chamberlain's rebounds on Mar 2, 1962 | ✅ 25 rebounds in the 100-point game ([box](https://www.basketball-reference.com/boxscores/196203020NYK.html)) |
| B-06 | How many offensive rebounds did the Spurs grab in Game 7 of the 2005 Finals? | Spurs' team offensive rebounds, 2005 Finals Game 7 | ✅ The 2005 Finals went 7 (Spurs over Pistons), Game 7 on Jun 23 ([playoffs](https://www.basketball-reference.com/playoffs/NBA_2005.html), [date](https://www.basketball-reference.com/boxscores/?month=6&day=23&year=2005)) |
| B-07 | Greek Freak blocks, Game 6, 2021 NBA Finals | Giannis's blocks, 2021 Finals Game 6 | ✅ "Greek Freak" = Giannis ([player](https://www.basketball-reference.com/players/a/antetgi01.html)). ✅ Game 6 on Jul 20, 2021: 50 pts, 5 blocks ([box](https://www.basketball-reference.com/boxscores/202107200MIL.html)) |
| B-08 | Kawhi Leonard points in Game 7 of the 2019 Eastern Conference semifinals | Kawhi's points in that Game 7 (Raptors vs 76ers) | ✅ The series went 7, Game 7 on May 12: 41 pts ([box](https://www.basketball-reference.com/boxscores/201905120TOR.html)) |
| B-09 | Top shot-blocker in Game 7 of the 2013 Finals | Blocks leaders for 2013 Finals Game 7 | ✅ The 2013 Finals went 7, Game 7 on Jun 20 ([playoffs](https://www.basketball-reference.com/playoffs/NBA_2013.html)) |
| B-10 | Who dished out the most assists here? *(on a box score page)* | Assist leaders for the game on screen | ✅ The page's game is 2023 Finals Game 5, Jun 12, 2023 (nba.com game ID 0042200405, [box](https://www.basketball-reference.com/boxscores/202306120DEN.html)) |
| B-11 | Raptors three-point percentage on June 13, 2019 | Raptors' team 3-point % on Jun 13, 2019 | ✅ 2019 Finals Game 6 at Golden State ([box](https://www.basketball-reference.com/boxscores/201906130GSW.html)) |
| B-12 | How many free throws did the Bucks make against Phoenix on July 17, 2021? | Bucks' team free throws made in that game (Suns are the opponent) | ✅ Finals Game 5, Bucks won at Phoenix ([box](https://www.basketball-reference.com/boxscores/202107170PHO.html)) |
| B-13 | What was Draymond's plus/minus on June 16, 2016? | Draymond Green's +/- on Jun 16, 2016 | ✅ Finals Game 6 at Cleveland, he played 41 min ([box](https://www.basketball-reference.com/boxscores/201606160CLE.html)) |
| B-14 | How many minutes did Larry Legend play on May 22, 1988? | Larry Bird's minutes on May 22, 1988 | ✅ "Larry Legend" = Bird ([player](https://www.basketball-reference.com/players/b/birdla01.html)). ✅ Game 7 vs the Hawks, 47 min ([box](https://www.basketball-reference.com/boxscores/198805220BOS.html)) |
| B-15 | Haliburton's dimes last night? *(asked Dec 8, 2023)* | Tyrese Haliburton's assists on Dec 7, 2023 *(ask date swapped Oct 1)* | ✅ In-season tournament semifinal vs the Bucks, 15 assists ([box](https://www.basketball-reference.com/boxscores/202312070MIL.html)) |
| B-16 | Joel Embid's points on January 22, 2024 | Joel Embiid's points on Jan 22, 2024, or ask which player (both OK) *(decided Sep 30)* | ✅ 70 pts vs San Antonio ([box](https://www.basketball-reference.com/boxscores/202401220PHI.html)) |
| B-17 | Moses Malone defensive rebounds on May 31, 1983 | Moses Malone's defensive rebounds on May 31, 1983 | ✅ 1983 Finals Game 4 at the Lakers, 15 defensive rebounds ([box](https://www.basketball-reference.com/boxscores/198305310LAL.html)) |
| B-18 | Dwight Howard free throw percentage on January 12, 2012 | Dwight Howard's free throw % on Jan 12, 2012 | ✅ 21-of-39 FT at Golden State ([box](https://www.basketball-reference.com/boxscores/201201120GSW.html)) |

## Playoff series

| Code | Question | What Ask should do | Facts |
| --- | --- | --- | --- |
| S-01 | Show the Bad Boys against the Bulls in the 1990 East finals. | Pistons vs Bulls, 1990 East finals | ✅ "Bad Boys" = Pistons ([wiki](https://en.wikipedia.org/wiki/Bad_Boys_(Detroit_Pistons))). ✅ Pistons beat the Bulls 4-3 ([playoffs](https://www.basketball-reference.com/playoffs/NBA_1990.html)) |
| S-02 | Kansas City Kings vs Rockets, 1981 West finals | Kansas City Kings (today's Sacramento) vs Rockets, 1981 West finals | ✅ Rockets beat the Kings 4-1 ([playoffs](https://www.basketball-reference.com/playoffs/NBA_1981.html)) |
| S-03 | Thunder-Heat 2012 title matchup | Thunder vs Heat, 2012 Finals | ✅ Heat won 4-1 ([playoffs](https://www.basketball-reference.com/playoffs/NBA_2012.html)) |
| S-04 | Which series did the Clippers play in the 2014 conference semis? | Clippers' 2014 second-round series | ✅ vs OKC, lost 4-2 ([playoffs](https://www.basketball-reference.com/playoffs/NBA_2014.html)) |
| S-05 | Find Denver's opening-round series in the 2012 playoffs. | Nuggets' 2012 first-round series | ✅ vs the Lakers, lost 4-3 ([playoffs](https://www.basketball-reference.com/playoffs/NBA_2012.html)) |
| S-06 | Open the West finals from the postseason I'm viewing. *(playoffs page showing 2019)* | 2019 West finals (season taken from the page) | ✅ Warriors over Portland ([playoffs](https://www.basketball-reference.com/playoffs/NBA_2019.html)) |
| S-07 | Celtics vs 76ers 1982 conference finals | Celtics vs 76ers, 1982 conference finals | ✅ 76ers won 4-3 in the East finals ([playoffs](https://www.basketball-reference.com/playoffs/NBA_1982.html)) |
| S-08 | Sixers-Nets first round 2019 | 76ers vs Nets, 2019 first round | ✅ 76ers won 4-1 ([playoffs](https://www.basketball-reference.com/playoffs/NBA_2019.html)) |
| S-09 | St. Louis Hawks vs Celtics 1958 Finals | St. Louis Hawks (today's Atlanta) vs Celtics, 1958 Finals | ✅ Hawks won 4-2 ([playoffs](https://www.basketball-reference.com/playoffs/NBA_1958.html)) |
| S-10 | The series between the Jazz and Rockets in the 1997 playoffs | Jazz vs Rockets, 1997 (no round given) | ✅ They met once, in the West finals ([playoffs](https://www.basketball-reference.com/playoffs/NBA_1997.html)) |
| S-11 | The Warriors' 2007 upset of Dallas in the first round | Warriors vs Mavericks, 2007 first round | ✅ Warriors won 4-2 ([playoffs](https://www.basketball-reference.com/playoffs/NBA_2007.html)) |
| S-12 | Who did the Mavericks face in the 2006 championship round? | Mavericks' 2006 Finals series (shows the opponent) | ✅ vs Miami ([playoffs](https://www.basketball-reference.com/playoffs/NBA_2006.html)) |
| S-13 | Pull up the Lakers' second-round series in 2023 | Lakers' 2023 second-round series | ✅ vs the Warriors ([playoffs](https://www.basketball-reference.com/playoffs/NBA_2023.html)) |
| S-14 | Show me the Knicks' 1999 first-round series with Miami. | Knicks vs Heat, 1999 first round | ✅ Knicks won 3-2 ([playoffs](https://www.basketball-reference.com/playoffs/NBA_1999.html)) |
| S-15 | Rockets-Sonics 1996 West semifinals | Rockets vs Seattle SuperSonics, 1996 West semifinals | ✅ "Sonics" = SuperSonics ([wiki](https://en.wikipedia.org/wiki/Seattle_SuperSonics)). ✅ Sonics swept ([playoffs](https://www.basketball-reference.com/playoffs/NBA_1996.html)) |
| S-16 | Open the 1971 Finals between Milwaukee and Baltimore | Bucks vs Baltimore Bullets (today's Wizards), 1971 Finals | ✅ Bucks swept ([playoffs](https://www.basketball-reference.com/playoffs/NBA_1971.html)) |

## Playoff summaries

| Code | Question | What Ask should do | Facts |
| --- | --- | --- | --- |
| R-01 | How did the Baltimore Bullets fare in the 1971 postseason? | Baltimore Bullets' 1971 playoff run | ✅ Reached the Finals ([playoffs](https://www.basketball-reference.com/playoffs/NBA_1971.html)) |
| R-02 | Summarize the Buffalo Braves' 1976 playoffs. | Buffalo Braves' 1976 playoff run | ✅ Beat the 76ers, lost to Boston ([playoffs](https://www.basketball-reference.com/playoffs/NBA_1976.html)) |
| R-03 | Give me the Philadelphia Warriors' 1956 postseason. | Philadelphia Warriors' 1956 playoff run | ✅ Won the title ([playoffs](https://www.basketball-reference.com/playoffs/NBA_1956.html)) |
| R-04 | San Diego Rockets 1969 playoff recap | San Diego Rockets (today's Houston) 1969 playoff run | ✅ Lost to Atlanta in the first round ([playoffs](https://www.basketball-reference.com/playoffs/NBA_1969.html)) |
| R-05 | Recap every round of the 2017 playoffs. | Whole-league summary of the 2017 playoffs | — |
| R-06 | Who won each round of the 1970 playoffs? | Whole-league summary of the 1970 playoffs (shows every series winner) | — |
| R-07 | Give me the Magic's 1995 playoff run | Magic's 1995 playoff run | ✅ Reached the Finals ([playoffs](https://www.basketball-reference.com/playoffs/NBA_1995.html)) |
| R-08 | Summarize Indiana's run for the playoff year I'm on. *(playoffs page showing 2014)* | Pacers' 2014 playoff run (year from the page) | ✅ Reached the East finals ([playoffs](https://www.basketball-reference.com/playoffs/NBA_2014.html)) |
| R-09 | Walk me through the 2004 Pistons' postseason. | Pistons' 2004 playoff run | ✅ Won the title ([playoffs](https://www.basketball-reference.com/playoffs/NBA_2004.html)) |
| R-10 | How did the Heat's 2006 playoff run go? | Heat's 2006 playoff run | ✅ Won the title ([playoffs](https://www.basketball-reference.com/playoffs/NBA_2006.html)) |
| R-11 | Recap the Hawks' 2021 postseason | Hawks' 2021 playoff run | ✅ Reached the East finals ([playoffs](https://www.basketball-reference.com/playoffs/NBA_2021.html)) |
| R-12 | Tell me how the 1984 NBA playoffs played out. | Whole-league summary of the 1984 playoffs | — |
| R-13 | Utah Jazz '98 playoff run | Jazz's 1998 playoff run | ✅ Reached the Finals ([playoffs](https://www.basketball-reference.com/playoffs/NBA_1998.html)) |
| R-14 | Rip City's 1990 playoff run | Trail Blazers' 1990 playoff run | ✅ "Rip City" = Portland ([wiki](https://en.wikipedia.org/wiki/Rip_City)). ✅ Reached the Finals ([playoffs](https://www.basketball-reference.com/playoffs/NBA_1990.html)) |
| R-15 | Summarize the Cincinnati Royals' 1964 postseason. | Cincinnati Royals (today's Sacramento) 1964 playoff run | ✅ Beat the 76ers, lost to Boston ([playoffs](https://www.basketball-reference.com/playoffs/NBA_1964.html)) |
| R-16 | Brooklyn's 2021 playoff showing | Nets' 2021 playoff run | ✅ Lost to the Bucks in round 2 ([playoffs](https://www.basketball-reference.com/playoffs/NBA_2021.html)) |
| R-17 | Recap OKC's run in last season's playoffs. *(asked Jan 20, 2025)* | Thunder's 2024 playoff run | ✅ Lost to Dallas in round 2 ([playoffs](https://www.basketball-reference.com/playoffs/NBA_2024.html)) |
| R-18 | What was the Bucks' playoff record in 2018-19? | Bucks' 2019 playoff run (it includes their playoff win-loss record) *(decided Sep 30)* | ✅ Went 10-5 and lost the East finals ([playoffs](https://www.basketball-reference.com/playoffs/NBA_2019.html)) |
| R-21 | Take me through Sacramento's 2002 playoffs. | Kings' 2002 playoff run *(added Oct 6, replaces R-19; needs review)* | ✅ Kings beat Utah 3-1 and Dallas 4-1, then lost the West finals to the Lakers in seven games ([playoffs](https://www.basketball-reference.com/playoffs/NBA_2002.html)) |

## Player season stats

| Code | Question | What Ask should do | Facts |
| --- | --- | --- | --- |
| Y-01 | Steph's threes per game in 2015-16 | Curry's 3-pointers made per game, 2015-16 | ✅ Played 79 games for GSW ([player](https://www.basketball-reference.com/players/c/curryst01.html)) |
| Y-02 | Russell Westbrook's total rebounds in 2016-17 | Westbrook's season total rebounds, 2016-17 | ✅ OKC, 81 games ([player](https://www.basketball-reference.com/players/w/westbru01.html)) |
| Y-03 | What was Wilt's scoring average in 1961-62? | Wilt's points per game, 1961-62 | ✅ 50.4 ppg ([player](https://www.basketball-reference.com/players/c/chambwi01.html)) |
| Y-04 | Kawhi's steals per game in the 2019 playoffs | Kawhi's steals per game, 2019 playoffs | ✅ 24 playoff games for Toronto ([player](https://www.basketball-reference.com/players/l/leonaka01.html)) |
| Y-05 | How many blocks did Mark Eaton have in 1984-85? | Eaton's season total blocks, 1984-85 | ✅ Utah, 82 games ([player](https://www.basketball-reference.com/players/e/eatonma01.html)) |
| Y-06 | Giannis's free throw percentage in 2020-21 | Giannis's free throw %, 2020-21 | ✅ Played 61 games ([player](https://www.basketball-reference.com/players/a/antetgi01.html)) |
| Y-07 | Jimmy Butler's minutes per game for the Heat in 2019-20 | Butler's minutes per game with Miami, 2019-20 | ✅ Was with Miami that season ([player](https://www.basketball-reference.com/players/b/butleji01.html)) |
| Y-08 | Carmelo Anthony stats for the Knicks in 2010-11 | Melo's per-game line for his Knicks games only, 2010-11 | ✅ Traded from Denver to the Knicks mid-season, 27 games with NY ([player](https://www.basketball-reference.com/players/a/anthoca01.html)) |
| Y-09 | Shai Gilgeous-Alexander's points per game this season *(asked Feb 10, 2025)* | SGA's points per game, 2024-25 | ✅ ([player](https://www.basketball-reference.com/players/g/gilgesh01.html)) |
| Y-10 | Dirk's 3-point percentage in 2006-07 | Dirk Nowitzki's 3-point %, 2006-07 | ✅ "Dirk" = Nowitzki, and he played 78 games ([player](https://www.basketball-reference.com/players/n/nowitdi01.html)) |
| Y-11 | Chris Paul assists in 2007-08 | CP3's assists per game, 2007-08 (the default when "total" isn't said) | ✅ New Orleans, 11.6 apg ([player](https://www.basketball-reference.com/players/p/paulch01.html)) |
| Y-12 | Hakeem's blocks in the 1994 playoffs | Hakeem's blocks per game, 1994 playoffs (default) | ✅ 23 playoff games ([player](https://www.basketball-reference.com/players/o/olajuha01.html)) |
| Y-13 | Oscar Robertson assists per game 1961-62 | Oscar's assists per game, 1961-62 | ✅ 11.4 apg, the triple-double season ([player](https://www.basketball-reference.com/players/r/roberos01.html)) |
| Y-14 | Anthony Edwards total points last season *(asked Mar 1, 2025)* | Edwards's season total points, 2023-24 | ✅ 79 games ([player](https://www.basketball-reference.com/players/e/edwaran01.html)) |
| Y-15 | Total offensive rebounds for Dennis Rodman in 1991-92 | Rodman's season total offensive rebounds, 1991-92 | ✅ Detroit, 82 games ([player](https://www.basketball-reference.com/players/r/rodmade01.html)) |
| Y-16 | Stat line for Tim Duncan in the 2003 postseason | Duncan's per-game line, 2003 playoffs (default) | ✅ 24 playoff games ([player](https://www.basketball-reference.com/players/d/duncati01.html)) |
| Y-17 | Tracy McGrady ppg 2002-03 | T-Mac's points per game, 2002-03 | ✅ 32.1 ppg ([player](https://www.basketball-reference.com/players/m/mcgratr01.html)) |
| Y-18 | Kevin Duarnt points per game 2013-14 | Kevin Durant's points per game, 2013-14, or ask which player (both OK) *(decided Sep 30)* | ✅ 32.0 ppg ([player](https://www.basketball-reference.com/players/d/duranke01.html)) |

## Team records & standings

| Code | Question | What Ask should do | Facts |
| --- | --- | --- | --- |
| T-01 | What was the Warriors' record in 2015-16? | Warriors' regular-season record, 2015-16 | — |
| T-02 | Bulls win-loss 1995-96 | Bulls' record, 1995-96 | — |
| T-03 | How did the West standings look at the end of 2006-07? | Final West standings, 2006-07 | — |
| T-04 | Eastern Conference table for 1997-98 | East standings, 1997-98 | — |
| T-05 | Show the full NBA standings from 1985-86. | Full league standings, 1985-86 | — |
| T-06 | How many games did the Bobcats win in 2011-12? | Charlotte Bobcats' record, 2011-12 (includes wins) | ✅ They were the Bobcats that season ([season](https://www.basketball-reference.com/leagues/NBA_2012.html)) |
| T-07 | Seattle SuperSonics record 1995-96 | SuperSonics' (today's OKC) record, 1995-96 | ✅ ([season](https://www.basketball-reference.com/leagues/NBA_1996.html)) |
| T-08 | Sixers' record in 1966-67 | 76ers' record, 1966-67 | ✅ "Sixers" = 76ers ([wiki](https://en.wikipedia.org/wiki/Philadelphia_76ers), [season](https://www.basketball-reference.com/leagues/NBA_1967.html)) |
| T-09 | What was the Knicks' record this season? *(asked Feb 10, 2025)* | Knicks' record, 2024-25 | — |
| T-10 | Celtics wins and losses last season *(asked Nov 15, 2025)* | Celtics' record, 2024-25 | — |
| T-11 | Vancouver Grizzlies' 1998-99 record | Vancouver Grizzlies' (today's Memphis) record, 1998-99 | ✅ ([season](https://www.basketball-reference.com/leagues/NBA_1999.html)) |
| T-12 | What did the Hornets finish with in 2005-06? | New Orleans/Oklahoma City Hornets' (today's Pelicans) record, 2005-06 | ✅ The only "Hornets" that season. Charlotte were the Bobcats ([season](https://www.basketball-reference.com/leagues/NBA_2006.html)) |
| T-13 | Record of the Kansas City-Omaha Kings in 1973-74 | KC-Omaha Kings' (today's Sacramento) record, 1973-74 | ✅ ([season](https://www.basketball-reference.com/leagues/NBA_1974.html)) |
| T-21 | Will you show me the Trail Blazers' record from 1990-91? | Blazers' record, 1990-91 *(added Oct 6, replaces T-14; needs review)* | — |
| T-15 | Minneapolis Lakers record 1949-50 | Minneapolis Lakers' record, 1949-50 | ✅ ([season](https://www.basketball-reference.com/leagues/NBA_1950.html)) |
| T-16 | Utah's record in 1997-98 | Jazz's record, 1997-98 | — |
| T-22 | Who finished with the worst record in the NBA in 1992-93? | League standings, 1992-93 *(added Oct 6, replaces T-20; needs review)* | — |

## Season leaders

| Code | Question | What Ask should do | Facts |
| --- | --- | --- | --- |
| L-01 | Rebounding leaders per game, 1991-92 | Top 10 in rebounds per game, 1991-92 | — |
| L-02 | Top 5 scorers per game in 1986-87 | Top 5 in points per game, 1986-87 | — |
| L-03 | Top three in total steals in 2000-01, including anyone tied | Top 3 in total steals, 2000-01 (ties are always shown) | — |
| L-04 | Who had the most assists in total in 1990-91? | Top 10 in total assists, 1990-91 | — |
| L-05 | Which qualified shooters led in three-point percentage in 2008-09? | Top 10 in 3-point %, 2008-09 | — |
| L-06 | Top 15 in field goal percentage in 1999-2000 | Top 15 in field goal %, 1999-2000 | — |
| L-07 | Who averaged the most assists in the 2016 playoffs? | Top 10 in assists per game, 2016 playoffs | — |
| L-08 | List the top 40 shot blockers by total blocks in 2004-05 | Top 25 in total blocks, 2004-05, with a note that 25 is the max | — |
| L-09 | Who led the NBA in total three-pointers made in 1987-88? | Top 10 in total 3-pointers made, 1987-88 | ✅ 3-point stats exist for 1987-88 ([season](https://www.basketball-reference.com/leagues/NBA_1988.html)) |
| L-10 | Top twenty free throw makers in total, 2011-12 | Top 20 in total free throws made, 2011-12 | — |
| L-11 | Playoff rebounding leaders per game, 2003 postseason | Top 10 in rebounds per game, 2003 playoffs | — |
| L-12 | Minutes per game leaders in 2013-14 | Top 10 in minutes per game, 2013-14 | — |
| L-13 | Who led the league in turnovers in total in 2005-06? | Top 10 in total turnovers, 2005-06 | — |
| L-14 | Most defensive rebounds per game in 2018-19 | Top 10 in defensive rebounds per game, 2018-19 | — |
| L-15 | Top 7 offensive rebounders in total, 1996-97 | Top 7 in total offensive rebounds, 1996-97 | — |
| L-16 | Who led in blocks per game this season? *(asked Mar 15, 2025)* | Top 10 in blocks per game, 2024-25 | — |
| L-17 | Highest scoring average in 1974-75 | Top 10 in points per game, 1974-75 | — |
| L-24 | Who took the rebounding crown in 2006-07? | Top 10 in rebounds per game, 2006-07 *(added Oct 6, replaces L-19; needs review)* | ✅ The rebounding title goes to the rebounds-per-game leader; Kevin Garnett led in 2006-07 with 12.8 ([leaders](https://www.basketball-reference.com/leagues/NBA_2007_leaders.html)) |
| L-25 | Who sank the most field goals in total in 2002-03? | Top 10 in total field goals made, 2002-03 *(added Oct 6, replaces L-23; needs review)* | — |

## Career stats

| Code | Question | What Ask should do | Facts |
| --- | --- | --- | --- |
| C-01 | Elgin Baylor's career points total | Baylor's career total points | — |
| C-02 | John Stockton career assists per game | Stockton's career assists per game | — |
| C-03 | All-time steals leaders | All-time top 10 in total steals | — |
| C-04 | Top five all-time three-point makers | All-time top 5 in 3-pointers made | — |
| C-05 | Where does Dirk rank on the all-time scoring list? | Dirk's rank on the all-time points list | ✅ "Dirk" = Nowitzki ([player](https://www.basketball-reference.com/players/n/nowitdi01.html)) |
| C-06 | Tim Duncan career playoff rebounds | Duncan's career playoff total rebounds | — |
| C-07 | Michael Jordan career stats | Jordan's career line as per-game averages (Ask's default for a full career line; totals are a toggle) *(decided Oct 1)* | — |
| C-08 | Reggie Miller's career free throw percentage | Reggie's career free throw % | — |
| C-09 | All-time playoff assists leaders | All-time top 10 in playoff assists | — |
| C-10 | Top 20 all-time in offensive rebounds | All-time top 20 in offensive rebounds | ✅ Offensive rebounds were first recorded in 1973-74 (none in [1972-73](https://www.basketball-reference.com/leagues/NBA_1973.html), present in [1973-74](https://www.basketball-reference.com/leagues/NBA_1974.html)), so the answer should note that |
| C-11 | Where does Kevin Garnett rank all-time in career rebounds? | KG's rank on the all-time rebounds list | — |
| C-12 | The Mailman's career playoff points per game | Karl Malone's career playoff points per game | ✅ "The Mailman" = Karl Malone ([player](https://www.basketball-reference.com/players/m/malonka01.html)) |
| C-13 | Magic Johnson's lifetime assists | Magic's career total assists | — |
| C-14 | How many career blocks did Dikembe Mutombo have? | Mutombo's career total blocks | — |
| C-15 | Top 40 all-time in career turnovers | All-time top 25 in turnovers, with a note that 25 is the max | — |
| C-16 | Who is the NBA's all-time leader in free throws made? | All-time top 10 in free throws made (the leader is first) | — |
| C-17 | Steve Nash career three point percentage | Nash's career 3-point % | — |
| C-27 | What is Hakeem Olajuwon's ranking on the career blocks list? | Hakeem Olajuwon's rank on the all-time blocks list *(added Oct 6, replaces C-18; needs review)* | — |
| C-19 | How many blocks has Victor Wembanyama recorded? | Wembanyama's career total blocks ("has recorded" means career) *(decided Oct 1)* | — |

---

## Ask should ask a follow-up

| Code | Question | What Ask should do | Facts |
| --- | --- | --- | --- |
| G-18 | Show every Knicks game from March 1 to March 20, 2024. | Ask for a shorter range (7 days max) | — |
| G-19 | Were the Grizzlies playing on the 4th of April? | Ask: which year? | — |
| G-20 | Which games were played at the Barclays Center? | Ask: which date? | — |
| B-19 | How many rebounds did Gasol grab on February 21, 2014? | Ask: Pau or Marc? *(date swapped Oct 1)* | ✅ Both played that night: Pau had 7 rebounds vs Boston ([box](https://www.basketball-reference.com/boxscores/201402210LAL.html)) and Marc had 10 vs the Clippers ([box](https://www.basketball-reference.com/boxscores/201402210MEM.html)) |
| B-20 | Who led Game 3 of the 2019 Finals? | Ask: led in which stat? *(decided Sep 30)* | ✅ Game 3 was Jun 5, 2019 ([date](https://www.basketball-reference.com/boxscores/?month=6&day=5&year=2019)) |
| B-21 | What did Antetokounmpo score on December 13, 2023? | Ask: Giannis or Thanasis? *(decided Sep 30)* | ✅ Both played that night. Giannis scored 64, Thanasis played 1 minute ([box](https://www.basketball-reference.com/boxscores/202312130MIL.html)) |
| S-17 | Bring up a Spurs playoff series from 2014. | Ask: which round? | ✅ The Spurs played 4 series in 2014 ([playoffs](https://www.basketball-reference.com/playoffs/NBA_2014.html)) |
| S-18 | Open a 2015 conference semifinal. | Ask: which teams? | ✅ There were 4 conference semifinals ([playoffs](https://www.basketball-reference.com/playoffs/NBA_2015.html)) |
| Y-19 | Ball's assists per game in 2021-22 | Ask: Lonzo or LaMelo? | ✅ Both played that season. Lonzo played 35 games for Chicago ([player](https://www.basketball-reference.com/players/b/balllo01.html)) and LaMelo 75 for Charlotte ([player](https://www.basketball-reference.com/players/b/ballla01.html)) |
| Y-20 | Karl-Anthony Towns rebounds per game in 2018 | Ask: 2017-18 or 2018-19? | ✅ KAT played both seasons ([player](https://www.basketball-reference.com/players/t/townska01.html)) |
| Y-21 | Malone's rebounds per game in 1985-86 | Ask: which Malone? | ✅ Three Malones played that season: Karl with Utah ([player](https://www.basketball-reference.com/players/m/malonka01.html)), Moses with Philadelphia ([player](https://www.basketball-reference.com/players/m/malonmo01.html)) and Jeff with Washington ([player](https://www.basketball-reference.com/players/m/malonje01.html)) |
| Y-22 | Jayson Tatum stats this season *(asked Sep 30, 2026, offseason)* | Ask: 2025-26 (just ended) or 2026-27 (upcoming)? *(decided Sep 30)* | ✅ Tatum played 16 games in 2025-26 ([player](https://www.basketball-reference.com/players/t/tatumja01.html)) |
| T-17 | What was LA's record in 2012-13? | Ask: Lakers or Clippers? | ✅ Both were in LA that season ([season](https://www.basketball-reference.com/leagues/NBA_2013.html)) |
| T-18 | What's the Heat's win-loss record? | Ask: which season? | — |
| L-18 | Steals leaders for 2016-17 | Ask: per game or total? | — |
| L-20 | Blocks per game leaders | Ask: which season? | — |
| C-20 | Show the all-time leaders | Ask: which stat? | — |

## Ask should say it can't answer

| Code | Question | What Ask should do | Facts |
| --- | --- | --- | --- |
| G-21 | Will the Lakers beat the Suns tonight? *(asked Jan 8, 2025)* | Can't answer: predictions | ❌ There was no Lakers–Suns game that day. This doesn't change the response; see Needs your decision |
| G-22 | What time does the Super Bowl start? | Can't answer: not basketball | — |
| B-22 | Who had the highest field-goal percentage in the Heat-Spurs game on June 18, 2013? | Can't answer: Ask doesn't rank players by a percentage within one game | ✅ 2013 Finals Game 6 ([box](https://www.basketball-reference.com/boxscores/201306180MIA.html)) |
| B-23 | What were Kawhi Leonard's per-game averages over the 2019 Finals? | Can't answer: averages over several games of one series *(decided Sep 30)* | — |
| B-24 | And how many rebounds did he have? | Can't answer: it's a follow-up to an earlier question, and Ask doesn't remember the conversation | — |
| S-19 | Show every playoff series the Spurs won from 1999 to 2014. | Can't answer: lists across many seasons | — |
| R-20 | Was the 2017 Warriors' playoff run better than the 2001 Lakers'? | Can't answer: "who was better" comparisons | — |
| Y-23 | Jaylen Brown's points per game at home in 2023-24 | Can't answer: home/away splits | — |
| Y-24 | Luka's true shooting percentage in 2022-23 | Can't answer: advanced stats | — |
| Y-25 | LeBron's points per game in the regular season and playoffs combined, 2012-13 | Can't answer: regular season and playoffs combined | — |
| T-19 | Pacers' record in overtime games 2019-20 | Can't answer: records in game subsets (overtime, home, etc.) | — |
| L-21 | Top Spurs scorer in 2013-14 | Can't answer: leaders within one team | — |
| L-22 | Which rookie averaged the most points in 2022-23? | Can't answer: rookie-only leaders | — |
| C-21 | Who has the most career triple-doubles? | Can't answer: triple-double counts | — |
| C-22 | Top 10 in career rebounds per game, all-time | Can't answer: all-time lists are totals only | — |
| C-23 | Where does Larry Bird rank all-time in career free throw percentage? | Can't answer: no rankings on percentage lists | — |
| C-24 | Dirk's career high in rebounds | Can't answer: career highs | — |
| C-25 | Who has scored the most points in Knicks franchise history? | Can't answer: franchise leaders | — |
| C-26 | How tall is Victor Wembanyama? | Can't answer: bio and trivia questions | — |
