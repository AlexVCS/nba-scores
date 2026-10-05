# Ask Stage 2

Implemented locally on `ask/reviewed-components`, under the existing disabled
production feature flags. Stage 2 adds two tools to the existing four-family
registry, in the order specified by ADR 0010.

- `player_season_stats`: one player's season totals or per-game averages, regular
  season or playoffs. A named team restricts the answer to that season's stint.
  With no team, a traded player requires an authoritative combined-season row.
- `team_records`: one team's regular-season wins/losses or complete league or
  Eastern/Western conference standings for one season.

A missing season is clarified. The measure (totals or per game) is read by Python
from the question text (ADR 0014); with none stated, a player's season shows per-game
averages first with a totals toggle (see "Measure toggle" below). An ambiguous season
type has server-validated choices; uncertain standings scope offers league/east/west; explicit playoff wording cannot silently become a
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
one retry, both inside the shared retrieval deadline described below. The tool verifies player/team identity, season and league before
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

Conferences began in 1970-71. Earlier BAA/NBA seasons had divisions only (#212):
stats.nba returns those rows with no `Conference`, and the Basketball-Reference
season page has a single `divs_standings_` table with a sub-header per
division. League standings for those seasons are answered from either source,
with no conference on any row. A division is never relabeled as a conference,
and the `divs_standings_E`/`_W` tables are read as conferences only from
1970-71. An Eastern or Western request for an earlier season is answered as
`no_record` (`no_conferences_before_1970`) before any fetch. The notice says
conferences began in 1970-71 and suggests league standings. We chose this over
substituting the Eastern or Western Division, which is a different grouping
(1949-50 also had a Central Division). It is clearer than "not supported yet",
because the fact does not exist. Seasons through 1954-55 included franchises
that later folded. Those franchises are intentionally absent from the
franchise records, so their standings still fail the full-coverage check and
report unavailable. 1955-56 through 1969-70 are answerable.
Each answer carries source metadata, a restricted source link and a fetch time.
The Hardwood UI shows these answers immediately under ADR 0006. Suggestions,
clarification choices and unrequested links keep their existing spoiler rules.

## Measure toggle (ADR 0014)

Live testing showed Jev confidently choosing a measure the question never stated.
`server/ask/measure.py` now decides it from the text, for player season stats,
season leaders and career stats. It replaces the interpreter's `aggregation` read
before the normalizer and the cascade policy see it (diagnostics show
`aggregation` decided by `question`).

- Per-game wording: "per game", "a game"/"a night" (not "in a game"), "ppg",
  "rpg", "apg", "spg", "bpg", "mpg", "average(s/d)". Totals wording: "total(s)",
  "in total", "how many". "How many ... average" is per game. Both kinds together
  are ambiguous.
- **No measure stated** ("Kevin Durant stats 2015-16", "Jokic rebounds for Denver in
  2023-24"): per-game averages first, no clarification. The answer also carries
  season totals (`alternate`), and the Hardwood card shows a segmented
  **Per game | Totals** toggle (a labelled group of `aria-pressed` buttons).
- **Measure stated:** that measure is shown first. The toggle stays, because the
  other measure comes from the same verified row and asking is consent (ADR 0006).
- Both measures come from **one source row** (NBA or Basketball-Reference, never
  both). Per game is the exact total divided by games played, shown to one decimal
  (Python `format(value, ".1f")`, round-half-even on the binary value). It is never
  rebuilt from rounded averages. Shooting splits show made/attempted per game
  ("9.7/19.2") and in total ("698/1381"). Percentages are the same in both measures,
  so a percentage-only answer is requested as `total` and has no toggle. The stat
  line keeps its made/attempted splits; it does not add percentages.
- Career lines (`career_stats` `player_totals`) get the same toggle. With no stated
  measure, a full career line starts at per game and one career statistic starts at
  totals (ADR 0013, amended 2026-10-01).

## Verification and release boundary

`server/tests/ask/test_season_tools.py` covers identity, traded players,
aggregation, postseason separation, unavailable sources, missing facts,
partial/duplicate standings, source URLs, throttling and concurrency.
`AskSeasonResults.test.tsx` checks immediate display, season/measure context,
record values and accessible standings rows.

`server/tests/ask/fixtures/eval/stage2-dev.json` adds 22 development cases with
labels authored before any live run. Case 22 ("Kevin Durant stats 2015-16") and the
per-game relabeling of cases 4 and 6 come from live feedback on 2026-09-30 (ADR 0014).
`server/tests/ask/test_live_feedback_measures.py` covers measure detection, the toggle
values and the pipeline paths with fake interpreters. `AskMeasureToggle.test.tsx`
covers the toggle. These cases are exposed development data,
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

### Shared retrieval deadline (nba-scores-8ic)

Unbudgeted, an NBA attempt, its backoff and retry, plus the BRef fallback took
about 13.75 seconds, while interpretation leaves as little as five seconds.
The pipeline now creates one monotonic `Deadline` (`server/utils/deadline.py`)
per request. It ends with the response deadline, less a 0.25-second margin
for building the response. The deadline is passed explicitly through
`resolve(..., deadline=)` to the season tools, the NBA `_run` retry loop and
the Basketball-Reference transport. There is no global state.

- Each NBA attempt's timeout is capped to the time left. An attempt starts only
  if 1.5 seconds remain. A retry also needs room for its 0.75-second backoff.
  Otherwise it is skipped.
- The fallback runs only if a BRef request can still start (2 seconds). The
  transport checks this before it takes the shared start slot, so a request
  that cannot finish does not use up the six-second limit. Its timeout is
  capped to the time left. The limiter still never waits: when throttled, it
  fails immediately.
- A primary miss that has no time left for fallback reports
  `season_deadline_exceeded`, shown as `service_unavailable`. It never becomes
  a no-record answer.
- Joined waits in the season cache, BRef HTML cache and outer answer cache end
  at the earlier of five seconds and the deadline. Other tools' answer-cache
  waits now also end at the deadline. A cached answer needs no budget.
- Only `DEADLINE_EXECUTORS` receive the deadline: the two stage 2 season tools
  and the two stage 3 tools, `season_leaders` and `career_stats`
  (`server/ask/resolvers/__init__.py`). Other executors keep their `(request)`
  signature and existing source timeouts. Calls without a deadline behave
  exactly as before.
- The HTTP `run_bounded` deadline and the occupied-worker accounting are
  unchanged.

Tests: `server/tests/ask/test_retrieval_deadline.py`, using fake clocks and
slow fakes. They cover a slow primary that skips its retry and fallback, a
retry that fits (with a capped timeout), a fallback skipped as unavailable,
fallback timeout capping, fast limiter refusal inside the budget, a start that
cannot fit, and joined waits bounded at the season and answer layers
(including a real coalesced load).

**Slow-host measurement, still pending.** `scripts/ask/measure_retrieval_deadline.py`
calls only the two stage 2 season tools (`player_season_stats` and `team_records`),
with no interpreter or LLM; the stage 3 tools are covered only by offline tests. It prints one JSON
record per case: the capped timeout, duration and error of each attempt, and
whether retrieval finished within `--budget`. `--simulate` is offline and
only checks the budget decisions. Before enabling Ask, run it on the
production host, with the deployed deadline:
`server/venv/bin/python scripts/ask/measure_retrieval_deadline.py --live --budget 4.75 --repeats 3`,
plus a run with `--budget` equal to a typical post-interpretation remainder.
Keep the output with the deployment record. Then tune
`NBA_MIN_ATTEMPT_SECONDS`, `MIN_START_SECONDS` and the timeouts. Note that
`requests` timeouts limit each connect/read, not total transfer time. A slow
drip can outlast a capped attempt, and in that case the HTTP deadline remains
the final bound. Boxscore, playoff and game-search retrieval do not yet share
the deadline.

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
