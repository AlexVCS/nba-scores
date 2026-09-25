# Video playlist verification for #187

Verification date: September 10, 2026. [Issue #187](https://github.com/AlexVCS/nba-scores/issues/187). The full feature remains gated. No backend playlist endpoint, boxscore interactions, media proxy, or production deployment was added.

## Decision

The retrieval approach in #187 needs to change. `nba_api.stats.endpoints.videodetails.VideoDetails` did not retrieve either requested target playlist. Both returned HTTP 500 with an empty response body, which nba_api surfaced as `JSONDecodeError`. The upstream response does not identify the server-side cause. It is not evidence of a CORS failure, an authentication requirement, or absent clips.

A separate diagnostic using `VideoDetailsAsset` retrieved the expected events and direct HTTPS MP4 URLs. This is a proposed replacement metadata endpoint, not a successful test of `VideoDetails` and not a media proxy. Native playback works in the local desktop browser. The user reports successful local Safari tests on a physical iPhone and iPad. Deployed-origin checks remain open; mobile event logs and individual control results were not supplied.

Sources: installed nba_api 1.11.4; [VideoDetails source](https://github.com/swar/nba_api/blob/master/src/nba_api/stats/endpoints/videodetails.py); [VideoDetailsAsset source](https://github.com/swar/nba_api/blob/master/src/nba_api/stats/endpoints/videodetailsasset.py); [season parameter definitions](https://github.com/swar/nba_api/blob/master/src/nba_api/stats/library/parameters.py). Runtime evidence below takes precedence over parameter names or old documentation.

## Method and evidence

Used Python 3.12.8 and the project's `.venv`, `NBA_STATS_HEADERS`, explicit season/team/player/game/stat parameters, and 12-second request timeouts. Each sample's player and team were resolved from `BoxScoreTraditionalV3` before the video request. The primary player is James Harden, ID `201935`, Cleveland team ID `1610612739`, in game `0022500931`. The independent boxscore records 6 FGM, 5 AST and 21 PTS. A generic "7 AST" example in #187 is not this player's total.

- [VideoDetails requests and raw responses](verification/video-2026-09-10/retrieval.json): 38 playlist calls, 28 HTTP 500, 8 HTTP 200, 2 HTTP 400.
- [VideoDetailsAsset comparison](verification/video-2026-09-10/asset-comparison/retrieval.json): the same 38 selections, 36 HTTP 200, 2 HTTP 400.
- [Event validation and range responses](verification/video-2026-09-10/asset-validation.json): event ID, game, description, player/team and stat checks against independently retrieved `PlayByPlayV3`; raw PBP files are in the same directory. All 30 nonempty asset playlists passed metadata identity checks. This does not mean every media file has been watched.
- One medium-quality MP4 from each of the 26 playlists with usable URLs returned HTTP 206, `video/mp4`, and byte-range support. These were Python HTTP requests with the deployed site's Referer, without authentication headers or a media proxy. They do not establish browser playback or deployed-origin behavior.

Additional target FGM diagnostics with numeric range values, blank LeagueID, and the library's default headers also returned empty HTTP 500 responses. No retry or header variation is claimed as a fix.

The original endpoint's eight HTTP 200 responses were historical playlists. Their media records contain an HTTP `manifest.f4m` URL and legacy time offsets, not direct per-event MP4 URLs. JSON success is insufficient to classify those responses as playable with the required native element.

## Target game categories

These results are for `VideoDetailsAsset` with `SeasonType=Regular Season`. Every corresponding `VideoDetails` request returned HTTP 500. Positive-stat players were chosen so zero boxscore values cannot explain empty playlists.

| Stat | Player | Boxscore value | Events | Non-null, matching MP4 URLs | Finding |
| --- | --- | ---: | ---: | ---: | --- |
| FGM | James Harden | 6 | 6 | 6 | All made field goals; excludes misses |
| AST | James Harden | 5 | 5 | 5 | Harden is the assister; a teammate is the scorer |
| FGA | Quentin Grimes | 13 | 13 | 11 | Makes and misses; events 358 and 533 have null media |
| FG3M | Keon Ellis | 4 | 4 | 4 | Made three-pointers |
| FG3A | James Harden | 8 | 8 | 8 | Three makes and five misses |
| FTM | Donovan Mitchell | 9 | 0 | 0 | Empty despite nine made free throws |
| FTA | Donovan Mitchell | 9 | 0 | 0 | Empty despite nine attempts |
| REB | Dean Wade | 10 | 10 | 10 | Offensive and defensive rebounds |
| OREB | Dean Wade | 4 | 4 | 4 | Events 8, 40, 365, 371 increment offensive rebound totals |
| DREB | Evan Mobley | 7 | 7 | 7 | Events 27, 333, 378, 397, 438, 548, 617 increment defensive totals |
| STL | Donovan Mitchell | 2 | 2 | 2 | Steal credit matches selected player |
| BLK | Evan Mobley | 3 | 3 | 3 | Block credit matches selected player |
| TOV | Trendon Watford | 4 | 4 | 4 | Selected player's turnovers |
| PTS | James Harden | 21 | 6 | 6 | Same six events as FGM, worth 15 points; excludes his six free throws |

FGM event IDs are `114, 263, 318, 376, 379, 383`. AST IDs are `101, 404, 413, 417, 439`. Each matches the requested game, the PBP description, and the game/event path in its media URL. The assist scorer's `personId` is not Harden's ID; verification checks the Harden assist credit and Cleveland team. Blocks and steals can share an event number with the opponent's shot or turnover, so event number alone is insufficient to validate player identity.

Keep FTM and FTA disabled pending more evidence. This single empty sample does not establish a universal upstream prohibition. Keep PTS disabled for the initial feature, or explicitly describe it as available scoring clips with incomplete free-throw coverage. Never equate clip count with point total.

## Game types and season mappings

| Game type and sample | SeasonType tested | VideoDetails | VideoDetailsAsset |
| --- | --- | --- | --- |
| Regular, PHI at CLE, `0022500931`, 2025-26 | `Regular Season` | FGM/AST 500 | Harden 6 FGM / 5 AST, matching MP4s |
| Playoffs, IND at OKC, `0042400407`, 2024-25 | `Playoffs` | FGM/AST 500 | Gilgeous-Alexander 8 FGM / 12 AST, matching MP4s |
| Play-in, ATL at ORL, `0052400101`, 2024-25 | `PlayIn` | FGM/AST 500 | Anthony 10 FGM / Banchero 7 AST, matching MP4s |
| Same play-in game and players | `Playoffs` | FGM/AST 500 | HTTP 200, empty playlists |
| Same play-in game and players | `Regular Season` | FGM/AST 500 | HTTP 200, empty playlists |
| Same play-in game and players | `Play-In` | FGM/AST 400 | FGM/AST 400 |
| Preseason, BOS at DEN, `0012400001`, 2024-25 | `Pre Season` | FGM/AST 500 | Pritchard 6 FGM / Westbrook 8 AST, matching MP4s |

The verified mapping is for **VideoDetailsAsset**: `002 → Regular Season`, `004 → Playoffs`, `005 → PlayIn`, `001 → Pre Season`. `PlayIn` is the working upstream value for the tested play-in game. No working play-in mapping was established for VideoDetails itself.

Preseason is not universally unsupported: this sample has clips. All-Star, Summer League, NBA Cup championship games with a distinct game-type prefix, unknown prefixes, and exceptional historical play-in conventions remain outside verified coverage. They must not silently fall back to Regular Season. The tested 2023-24 Cleveland/Indiana game is within the regular-season sample, not evidence for the separate Cup championship game type.

## Historical samples

Each row has independent boxscore and PBP evidence. Counts are FGM / AST; the players can differ by stat.

| Season | Game | Matchup | VideoDetails media | VideoDetailsAsset events | Matching MP4 URLs |
| --- | --- | --- | --- | --- | --- |
| 2023-24 | `0022300001` | CLE at IND | HTTP 500 | 13 / 13 | 13 / 13 |
| 2020-21 | `0022000001` | GSW at BKN | HTTP 500 | 10 / 10 | 10 / 10 |
| 2015-16 | `0021500001` | DET at ATL | Legacy F4M manifest | 8 / 5 | 8 / 5 |
| 2014-15 | `0021400001` | ORL at NOP | Legacy F4M manifest | 10 / 7 | 10 / 7 |
| 2013-14 | `0021300001` | ORL at IND | Legacy F4M manifest | 8 / 7 | 0 / 0 |
| 2012-13 | `0021200001` | WAS at CLE | Legacy F4M manifest | 11 / 9 | 0 / 0 |

The first sampled usable season is 2014-15. This is not proof that all games since 2014-15 work, or that all earlier games fail. The evidence does disprove a rolling ten-year exclusion rule: 2014-15 media is still returned and responds to byte-range requests in September 2026.

## Coverage policy

The current implementation plan is [video-feature-plan.md](video-feature-plan.md), published to [#187](https://github.com/AlexVCS/nba-scores/issues/187). It replaces the earlier tuple-level pilot proposal.

1. The video feature remains gated on deployed Chrome and physical Safari verification. Local mobile results are user-reported overall successes without individual control logs.
2. The proposed initial scope is completed regular-season, playoff, play-in and preseason games from 2014-15 onward. Mid-season and late-season checks in 2013-14 and 2014-15 remain required before selecting that floor; it may move earlier or later. This is product eligibility, not guaranteed continuous footage coverage.
3. Apply eligibility by game type and season, without individual player/event allowlists or a rolling ten-year cutoff. The backend supplies `statVideoEligible` and enforces the same policy in the playlist endpoint. The frontend combines it with supported categories and positive stat values.
4. Initially eligible categories are FGM, FGA, FG3M, FG3A, REB, OREB, DREB, AST, STL, BLK and TOV, subject to further category sampling. Defer FTM, FTA and PTS. Every category may have partial coverage.
5. Null media URLs and legacy non-MP4 responses are unavailable media even when event metadata exists. Preserve usable clips and show available clip counts in the dialog; boxscore buttons retain the actual stat values.
6. Upstream errors are not permanent lack of coverage. Cache eligible nonempty playlists for 24 hours; valid empty results for 15 minutes for completed games within 72 hours, or 24 hours for older games. Unknown dates use the short empty-result lifetime. Do not renew expiration on reads.
7. Retrieve playlists only on user selection. No per-cell video requests during initial boxscore loading. Use one native video element with metadata preload and only the selected media source.

## Playback checks

The diagnostic uses a bare `<video controls playsinline>` and sets its `src` to the returned HTTPS MP4. No custom media authentication headers, proxy, autoplay, JavaScript media player, blob conversion or `crossorigin` attribute. JavaScript only selects sources and records native playback events.

| Environment | Status |
| --- | --- |
| Desktop browser identified as Chrome by the browser connector, local macOS machine, `http://localhost:5173` | Direct FGM and AST playback observed. Pause/resume, native seeking and source switching exercised; local only. Exact browser version was not manually checked; the downloaded log records the browser-reported user agent. |
| Desktop Chrome, `https://nbascorez.com` | Not tested. Deployed app was opened, but the diagnostic has not been deployed. |
| Physical iPhone 12 mini, iOS 26.5, Safari | User reports that the local test worked. Detailed control results/log pending; deployed test still pending. |
| Physical 2018 iPad Pro, iPadOS 26.5, Safari | User reports that the local test worked. Detailed control results/log pending; deployed test still pending. |

The [local desktop playback log](verification/video-2026-09-10/local-desktop-playback.json) records native events and the browser-reported user agent. It is local-origin evidence only.

Local page: `http://localhost:5173/video-verification.html`. For the phone and tablet on the Mac's Wi-Fi: `http://192.168.1.80:5173/video-verification.html`. The server is already bound to all interfaces and the LAN URL returned HTTP 200. The LAN address may change. Target deployed path, not yet published: `https://nbascorez.com/video-verification.html`.

Use native play, pause/resume and seek forward/backward. Switch clips while playing, then switch FGM to AST. Visually confirm player, teams, play and period/clock. The two mobile results are user-reported overall local passes, not agent-observed per-control passes. Record the device, OS/browser version, origin, network and each result in the page and download its JSON log. Repeat on the deployed origin. Mobile emulation and local playback do not satisfy the deployed physical-device requirement.

No deployed playback failure has been observed because that test has not run. Do not attribute a hypothetical failure to CORS or add a proxy. If a test fails, capture the native `MediaError`, browser network status and relevant response headers, media format, range behavior, and the deployed page's CSP. Distinguish an upstream media refusal from CSP, format, autoplay, expired URL and network problems before choosing an alternative.

## Revised delivery approach and estimate for #187

[#187](https://github.com/AlexVCS/nba-scores/issues/187) now specifies VideoDetailsAsset, backend-owned eligibility, partial-playlist handling, deferred free-throw/PTS categories and the remaining deployed-playback gate. See [the local plan](video-feature-plan.md) for its complete acceptance criteria.

The existing boxscore route is uncached. [#190](https://github.com/AlexVCS/nba-scores/issues/190), mirrored as beads issue `nba-scores-j3j`, now owns the shared cache and authoritative game-context work. See [the cache plan](boxscore-cache-plan.md). It should land as a standalone PR and can proceed alongside video verification. The playlist implementation depends on that service. The cache PR preserves public response contracts; `statVideoEligible` belongs to #187.

The cache plan requires bounded storage, thread safety, per-process request coalescing, failure cleanup, mutation isolation and lifetime selection from freshly retrieved authoritative status at insertion. Live/scheduled or uncertain metadata uses 15 seconds, recent completed games use 15 minutes, and older completed games use 24 hours. Cache hits never extend expiration.

Provisional remaining effort is 0.5–1 engineering day for video verification, 0.5–1 for the separate cache PR including focused tests, and 3–5 for video implementation and remaining QA. Combined effort is 4–7 engineering days, excluding scheduling delays and upstream outages.

If deployed direct MP4 playback fails, pause the embedded-player work and diagnose first. Re-estimate after a supported approach is demonstrated. An external NBA.com link is a possible reduced-scope option requiring a product decision. Media proxying, transcoding and authenticated media delivery are separate proposals; none is included here.

## Reproduction and local handoff

```sh
.venv/bin/python scripts/verify-video-retrieval.py --output docs/verification/video-2026-09-10
.venv/bin/python scripts/verify-video-retrieval.py --endpoint VideoDetailsAsset --output docs/verification/video-2026-09-10/asset-comparison
.venv/bin/python scripts/verify-video-evidence.py
pnpm build
pnpm lint
```

Build and lint passed. The existing Vite large-chunk warning remains. The diagnostic and evidence are local, uncommitted, and unpushed. Existing unrelated edits were left in place. Beads issue `nba-scores-cv2` tracks the unfinished verification. GitHub issue #187 was updated and #190 was created at the user's request. The plans are saved locally as `docs/video-feature-plan.md` and `docs/boxscore-cache-plan.md`. No implementation, deployment or git push was performed during the ticket split.
