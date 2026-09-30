# Ask Stage 2

Implemented locally on `ask/reviewed-components`, under the existing disabled
production feature flags. Stage 2 adds two tools to the existing four-family
registry, in the order specified by ADR 0010.

- `player_season_stats`: one player's season totals or per-game averages, regular
  season or playoffs. A named team restricts the answer to that season's stint.
  With no team, a traded player requires an authoritative combined-season row.
- `team_records`: one team's regular-season wins/losses or complete league or
  Eastern/Western conference standings for one season.

A missing season is clarified. Ambiguous totals/per-game or season type has
server-validated choices; uncertain standings scope offers league/east/west; explicit playoff wording cannot silently become a
regular-season answer. A bare calendar year outside playoff language
retains both overlapping seasons. The tools do not answer division standings,
home/away, opponent, month/date splits, advanced metrics, per-36/per-100 rates,
career totals, season leaders or records across seasons. Finals, rounds, individual
games, quarter/half/clutch/overtime splits, conditional player-dependent records,
multiple-player comparisons, combined regular-season/playoff totals and
conference-only win-loss records are rejected. The scope guard runs
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
tables. The season totals page has separate regular-season and postseason
tables; a saved current UTF-8 page excerpt covers both. Player matching requires a unique full-name identity in the independent
NBA catalog for that season. Historical team names must match dated franchise
records. Each answer uses one source; values from sources are never combined.

The shared Basketball-Reference transport allows one request start every six
seconds, uses a descriptive User-Agent, refuses redirects, and fails immediately
when throttled. Existing boxscore fallback uses the same transport. This limit
is process-wide, not shared across replicas. Multiple fallback workers need a
shared external limit before deployment. Successful completed-season tool data
is cached for a day; changing seasons and raw HTML use 30 seconds. Caches are
bounded and identical loads coalesce; joined callers at both season-cache
and outer answer-cache layers wait at most five seconds. Completed seasons use the long TTL only after the following
November, including the late 2020 playoffs. No provider error is stored as an answer.

Missing historical statistics show "Unavailable" and a coverage note, rather
than zero. Known pre-tracking gaps do not fetch or spend fallback capacity. A
shooting percentage requires positive, valid shot attempts. A specifically requested missing statistic tries fallback; it cannot
be replaced by a different stat. Percentages retain their percentage units.
League-wide standings sort by winning percentage across conferences, with
alphabetical ordering for ties; conference tables retain source ranks.
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

## Remaining deployment work from review

The interpreter reserves at most five seconds for retrieval, while an NBA retry
plus fallback can take about 13.75 seconds. The HTTP boundary still caps the
response deadline and keeps occupied-worker accounting. Before enabling Ask,
measure slow-host behavior and tune a shared retrieval deadline across calls.

A well-formed NBA season miss still tries BRef, as ADR 0010 requires fallback
when the primary lacks coverage. A miss is not proof that a historical record
does not exist. Structural gaps are skipped. If fallback is busy, Ask reports
unavailable rather than inventing a no-record result. The same global limit
can temporarily leave historical boxscore quarter scores unavailable. The game
summary then keeps its NBA scores and adds `periodScoreRetryAfter` seconds (and a
`Retry-After`, `no-store` header) when retrying can help. Views of one game share
one fallback fetch, and joined views wait at most its two-second timeout. A parsed
line score is cached for a day and a page without one for 15 minutes; failures are
not cached. Design 1 follows the hint up to three times, then offers "Try again".
