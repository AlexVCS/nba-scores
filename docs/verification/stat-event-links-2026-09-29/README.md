# Stat event link verification (issue #187)

Retrieved 2026-09-29. Evidence for linking Hardwood boxscore counting stats to
NBA.com event pages with the same rule NBA.com's own box score uses.

- `contract.json`: the backend/frontend contract (`statEvents` shape and three
  observed URLs for 0022500868).
- `games/<gameId>.json`: one fixture per game with the summary inputs, the
  expected `statEvents`, linked and unlinked cells for players and team totals,
  and exact URLs for a representative player and that player's team totals.
  Games without links record empty URL lists. The backend tests
  (`server/tests/test_stat_events.py`) load every fixture.

## Sources

Box score pages, `https://www.nba.com/game/<gameId>/box-score`, fetched with a
desktop Chrome user agent. Each page's `__NEXT_DATA__` supplies `game.whStatus`,
`game.videoAvailableFlag`, `game.period`, the players, team totals and
`periodOptions[0].json` (the All Periods range passed to the link component).

NBA.com scripts, as referenced by those pages:

| Script | SHA-256 |
| --- | --- |
| `https://www.nba.com/_next/static/chunks/78871-15eeb23af882c3f1.js` (module 35677, stat link; module 34631, league check; box score table) | `922c2e0b6e6a834627566ad084bbca4cee047be4d2e2c120bf71c22100b7bfc2` |
| `https://www.nba.com/_next/static/chunks/pages/_app-f31363c7185906d8.js` (module 3133, query builder and game-ID parser) | `4cb7414ec0a209b63ddec30249a0fff9bd3bfb3fefdabba06e6c1f3ec56b71a6` |

The build manifest (`_buildManifest.js`) returned Access Denied to curl.

## How the fixtures were produced

The two chunks were loaded into Node with a minimal webpack `require`, and
module 35677 was called with NBA.com's real modules 3133 and 34631 (React,
class names and analytics stubbed). For every player row and both team-total
rows, each traditional column was passed through the component exactly as the
box score table does (`personId: 0` for totals, links only when
`whStatus === 1`). Every href in the fixtures is the component's output
prefixed with `https://www.nba.com`; `statEvents` is read back from those
hrefs. The generator also checked that no measure links for some positive
values but not others. The three URLs in `contract.json` match the generated
ones byte for byte.

`observed: true` marks games whose rendered NBA.com box score was checked
during the 2026-09-29 investigation. The links are rendered client side, so
the saved HTML contains no `/stats/events` anchors.

## Code excerpts (trimmed, minified names kept)

Stat link component, chunk 78871, module 35677:

```js
const d = new Set(["fieldGoalsMade","FGM","fieldGoalsAttempted","FGA","threePointersMade","FG3A",
  "threePointersAttempted","FG3M","reboundsOffensive","OREB","reboundsDefensive","DREB","reboundsTotal",
  "REB","assists","AST","steals","STL","blocks","BLK","BLKA","turnovers","TOV", /* ...team/matchup stats */]),
  m = new Set(["fieldGoalsMade","FGM","fieldGoalsAttempted","FGA","threePointersMade","FG3A",
  "threePointersAttempted","FG3M","PTS_OFF_TOV","PTS_2ND_CHANCE","PTS_FB"]);
const p = {fieldGoalsMade:"FGM", fieldGoalsAttempted:"FGA", threePointersMade:"FG3M",
  threePointersAttempted:"FG3A", reboundsOffensive:"OREB", reboundsDefensive:"DREB",
  reboundsTotal:"REB", assists:"AST", steals:"STL", blocks:"BLK", turnovers:"TOV", /* ... */}, g = 2014, f = 2001;
const y = X$(function (e) { // "{rangeType:..}" -> {RangeType, StartPeriod, EndPeriod, StartRange, EndRange}
  if (!e) return {};
  return JSON.parse(e.replace(/range/g,"Range").replace(/start/g,"Start").replace(/end/g,"End"));
});
function x({children:e, gameId:a, personId:t, teamId:r="", statName:u, statValue:x, videoAvailableFlag:T=0,
            gameEventId:b, period:_, extraParams:w={}, cfid:k, cfparams:C, /* ... */}) {
  const L = null != b, B = useMemo(() => rT(a || ""), [a]), Z = !!B && Object.keys(B).length > 0;
  const R = Z ? B.Season : N, E = B?.isPlayIn;
  let G = Z ? B?.SeasonType : j;
  G = E ? G?.replace(/ /g,"") ?? null : G;             // "Play In" -> "PlayIn"
  const F = Number(Z ? B.seasonyear : M), D = Z ? B.isPre : "Pre Season" === j,
        H = !Z || isLeague00(a || "");                 // module 34631: "00" === id.slice(0, 2)
  if (!H) return e;
  const $ = 1 === +T, W = L || d.has(u || ""),
        U = $ && W && F >= g && (!D || D && F >= g),    // video
        V = m.has(u || "") && F >= f && (!D || D && F > 2016); // shot chart
  if (!U && !V) return e;
  if (!L && (!x || 0 === +x)) return e;                // zero values stay plain text
  let z = 0;
  [{state: U, value: 1}, {state: !L && V, value: 2}].forEach(e => { e.state === true && (z += e.value) });
  let q = {flag: z, GameID: a || "", Season: R, CFID: k || "", CFPARAMS: C || "", ...w};
  q = {...q, ...(Number(t) > 0 ? {PlayerID: t} : {}), TeamID: r, ContextMeasure: p[u] || u,
       SeasonType: G, ...y(_), section: "game", sct: "plot"};
  return <a href={`/stats/events/?${UK(q)}`}>{e}</a>;
}
```

Box score table (same chunk): links render only with warehouse data, and
totals pass `personId: 0`:

```js
const {videoAvailableFlag: u, whStatus: h} = e, f = 1 === h;   // hasWarehouseData
// player cell
n ? <Link gameId={t} personId={i.personId} teamId={e.teamId} statName={l}
          statValue={i.statistics[l]} videoAvailableFlag={r} period={o} /> : plainValue
// totals cell
n ? <Link gameId={t} personId={0} teamId={e.teamId} statName={i} statValue={e.statistics[i]} ... /> : plainValue
```

Query builder and game-ID parser, `_app`, module 3133:

```js
function r(e, t = !1) {                 // exported as UK
  let n = Object.keys(e).sort();
  if (!t) return n.map(t => `${t}=${encodeURI(e[t])}`).join("&");
  return new URLSearchParams(n.map(t => [t, e[t]])).toString();
}
function R(e) { return `${e}-${(Number(e) + 1).toString().slice(-2)}` }
N = {options: [{val:"Pre Season",st:1}, {val:"Regular Season",st:2}, {val:"Playoffs",st:4},
               {val:"All Star",st:3}, {val:"Play In",st:5}]};
function M(e) {                         // exported as rT
  if (!(e = `${e}`) || !/^\d{10}$/.test(e)) return null;
  let o = Number(e.slice(2, 3)), a = e.slice(3, 5);
  let h = N.options.find(t => Number(t.st) === o)?.val ?? "";   // 006 (Cup final) -> ""
  let v = +((Number.parseInt(a, 10) >= 45 ? "19" : "20") + a);
  return {Season: `${R(v)}`, SeasonType: h, isPre: 1 === o, isPlayIn: 5 === o, st: o, seasonyear: v, /* ... */};
}
```

`periodOptions[0]` in `__NEXT_DATA__` ends at 28800 for regulation games and
31800 for 0020500001 (`period: 5`), matching `28800 + 3000 * overtimePeriods`.

## Video CDN placeholder

On 2026-09-26 the tested `videos.nba.com` clip URLs, including known clip URLs,
fabricated paths and every tested resolution, all returned HTTP 200 with the
same 15-second "VIDEO NOT AVAILABLE" MP4: ETag
`"2dd8e05a98fc6949fa7ec979b0905464:1754501139.183376"`, Content-Length
`31580089`. A 2026-09-29 recheck returned the same response. Status codes
cannot tell real clips from the placeholder; compare ETag or duration.

An NBA.com event page was heard playing audio on 2026-09-29. Visual playback
verification is still pending, so a link means NBA.com offers an event page for
that stat, not that footage exists for every play.
