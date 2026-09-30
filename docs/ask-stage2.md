# Ask Stage 2

Implemented locally on `ask/reviewed-components`, under the existing disabled
production feature flags. Stage 2 adds two tools to the existing four-family
registry, in the order specified by ADR 0010.

- `player_season_stats`: one player's season totals or per-game averages, regular
  season or playoffs. A named team restricts the answer to that season's stint.
  With no team, a traded player requires an authoritative combined-season row.
- `team_records`: one team's regular-season wins/losses or complete league or
  Eastern/Western conference standings for one season.

A missing season is clarified. A bare calendar year outside playoff language
retains both overlapping seasons. The tools do not answer division standings,
home/away, opponent, month/date splits, advanced metrics, per-36/per-100 rates,
career totals, season leaders or records across seasons. The scope guard runs
in both HTTP and interpretation evaluation, including clarification continuations.

## Data and answers

PlayerCareerStats season-total rows, TeamYearByYearStats team records, and
LeagueStandings are primary. Each NBA attempt has a four-second timeout and
one retry. The tool verifies player/team identity, season and league before
execution. Full standings must cover every franchise active that season; partial
or duplicate tables cannot produce an answer. Source conference ranks are used
when supplied; the tool does not invent a league tiebreak rank.

Basketball-Reference is a fallback only when NBA cannot supply the fact. It reads
a season totals table or season summary standings, including comment-wrapped
tables. Player matching requires a unique full-name identity in the independent
NBA catalog for that season. Historical team names must match dated franchise
records. Each answer uses one source; values from sources are never combined.

The shared Basketball-Reference transport allows one request start every six
seconds, uses a descriptive User-Agent, refuses redirects, and fails immediately
when throttled. Existing boxscore fallback uses the same transport. This limit
is process-wide, not shared across replicas. Multiple fallback workers need a
shared external limit before deployment. Successful completed-season tool data
is cached for a day; changing seasons and raw HTML use 30 seconds. Caches are
bounded and identical loads coalesce. No provider error is stored as an answer.

Missing historical statistics show "Unavailable" and a coverage note, rather
than zero. A specifically requested missing statistic tries fallback; it cannot
be replaced by a different stat. Percentages retain their percentage units.
Each answer carries source metadata, a restricted source link and a fetch time.
The Hardwood UI shows these answers immediately under ADR 0006. Suggestions,
clarification choices and unrequested links keep their existing spoiler rules.

## Verification and release boundary

`server/tests/ask/test_season_tools.py` covers identity, traded players,
aggregation, postseason separation, unavailable sources, missing facts,
partial/duplicate standings, source URLs, throttling and concurrency.
`AskSeasonResults.test.tsx` checks immediate display, season/measure context,
record values and accessible standings rows.

`server/tests/ask/fixtures/eval/stage2-dev.json` adds 21 development cases with
labels authored before any live run. These cases are exposed development data,
not independent unseen release evidence. Historical four-family artifacts and
labels are preserved. Deprecated unsupported reasons remain deserializable for
those artifacts, but current adapters do not offer them.

The release runner remains pinned to the older four-family commit. Before
production, freeze a new commit, independently author field labels and unseen
cases for the expanded scope, and meet ADR 0009's tier/system gates. Include
Laya shadow numbers when its development endpoint is available; Laya remains
excluded from production. Host-level NBA/BRef access and physical keyboard and
screen-reader checks also remain required. No production flags are changed here.
