## Overview

Add clickable player stats to the Hardwood boxscore so users can watch the corresponding available plays in a video dialog, similar to [NBA.com](https://www.nba.com/game/phi-vs-cle-0022500931/box-score#box-score).

For example, selecting James Harden's `5 AST` in game `0022500931` opens his available assist clips. Boxscore values remain the actual recorded statistics; the dialog shows the usable clip count.

## Verification findings — September 10, 2026

- `VideoDetails` returned HTTP 500 with empty bodies for the target FGM/AST requests and several prior-season samples. Older samples returned legacy F4M manifests. The recent-game failures remain unexplained; the endpoint is not universally dead.
- `VideoDetailsAsset` returned matching FGM and AST clips for `0022500931`. Independent boxscore and play-by-play checks confirmed game/player/team/stat event identity. Harden had six FGM clips and five AST clips.
- Across the comparison samples, all 30 nonempty playlists passed metadata identity checks. Twenty-six playlists contained 197 matching HTTPS MP4 URLs. One medium-quality URL from each of those 26 playlists responded to a byte-range request with HTTP 206. These requests do not establish browser playback or universal coverage.
- Local desktop playback, pause/resume, seeking and clip switching worked with native controls. The desktop browser was identified as Chrome by the browser connector; the saved local log contains its reported user agent.
- The user reported successful local Safari playback on a physical iPhone 12 mini running iOS 26.5 and a 2018 iPad Pro running iPadOS 26.5. Mobile event logs and individual control results were not recorded; these are overall user reports, not recorded per-control passes.
- Deployed-origin playback remains unverified.

Detailed evidence currently exists locally in `docs/video-playlist-verification.md` and `docs/verification/video-2026-09-10/`. It has not been pushed as part of this ticket update.

## Dependencies and delivery order

Shared boxscore/game-metadata caching is separate work in #190. Land it as a standalone PR with its own review, freshness checks and rollback. It can proceed alongside the verification below and does not depend on video playback succeeding.

This issue's playlist implementation depends on #190's cached service. The video feature remains gated on completing verification. Add video-specific eligibility fields in this issue, not in the cache PR.

## Implementation plan

### 1. Finish verification and establish launch coverage

- [ ] Sample mid-season and late-season games from both 2013–14 and 2014–15 before selecting the historical floor.
- [ ] Record playable media, null URLs and partial coverage separately rather than inferring a universal CDN retirement date.
- [ ] Sample REB, OREB, DREB, STL, BLK and TOV in additional seasons and game types.
- [ ] Deploy the bare-video diagnostic.
- [ ] Verify playback, pause/resume, forward/backward seeking and clip switching from the deployed frontend in desktop Chrome and Safari on an actual iPhone or iPad.
- [ ] Record browser/device versions, origin, selected clips, visual identity checks and individual control results.

The proposed initial scope is completed regular-season, playoff, play-in and preseason games from 2014–15 onward, subject to these checks. Additional historical results may move the proposed floor earlier or later. Recheck game-ID conventions if the floor moves outside the verified range.

Usable URLs were found for sampled 2014–15 and 2015–16 games; sampled 2012–13 and 2013–14 games returned null media through VideoDetailsAsset. This is not proof of continuous season coverage or a universal availability boundary.

Eligibility is a product policy based on sampling, not a guarantee that every eligible game has footage. Apply it by game type and season, without individual player/event allowlists or a rolling ten-year cutoff.

Use a bare `<video controls playsInline>` with returned media URLs, without a media proxy or custom authentication headers. If deployed playback fails, capture the observed media/browser/network error and revise the delivery approach and estimate before implementing the full feature. Do not presume CORS or authentication is the cause. Media proxying is not an automatic fallback.

### 2. Centralize eligibility and add the playlist endpoint

```http
GET /games/{game_id}/players/{player_id}/videos?stat=FGM
```

- [ ] Use `nba_api.stats.endpoints.videodetailsasset.VideoDetailsAsset`.
- [ ] Validate game/player identifiers and supported stat values.
- [ ] Resolve the player's team through the shared cached game-context service from #190; return `404` when the player is absent from the requested game.
- [ ] Derive season and game type from validated game-ID conventions using an explicit prefix mapping.
- [ ] Centralize the launch eligibility policy in the backend.
- [ ] Add `statVideoEligible: boolean` to the boxscore response without making video requests.
- [ ] Enforce that same eligibility policy in the playlist endpoint. Handle valid but ineligible games explicitly, distinct from eligible games with empty playlists.

`statVideoEligible` means the game qualifies for an on-demand lookup. It does not promise available clips. The frontend combines it with the supported-category mapping and a positive stat value; it does not duplicate the season/game-type policy.

| Game-ID prefix | Game type | Upstream SeasonType |
| --- | --- | --- |
| `001` | Preseason | `Pre Season` |
| `002` | Regular season | `Regular Season` |
| `004` | Playoffs | `Playoffs` |
| `005` | Play-in | `PlayIn` |
| `003` | All-Star | Ineligible |
| Anything else | Unverified type | Ineligible |

Known historical exceptions require explicit handling and verification before eligibility. Do not silently default unsupported cases to regular season.

The verified mappings are for VideoDetailsAsset. For play-in game `0052400101`, `PlayIn` returned matching FGM/AST clips; `Playoffs` and `Regular Season` returned empty playlists; `Play-In` returned HTTP 400.

- [ ] Normalize game/player/team/stat identity, event descriptions, clip IDs, usable media URLs, and thumbnails where available.
- [ ] Match media to event identity and omit null or unusable URLs while preserving valid clips. Account for shared event numbers for steals/turnovers and blocks/shots when validating identity.
- [ ] Return an empty playlist for a valid eligible lookup without usable footage.
- [ ] Reuse existing NBA headers, timeout, retry, logging and upstream error handling.
- [ ] Preserve `503` timeout and `502` bad-upstream-response conventions without exposing internal exception details.
- [ ] Keep upstream failures distinct from valid empty results.
- [ ] Do not add automatic fallback to VideoDetails.

The response contains JSON metadata and media URLs, not video bytes. [VideoDetailsAsset source](https://github.com/swar/nba_api/blob/master/src/nba_api/stats/endpoints/videodetailsasset.py).

### 3. Define categories and partial-coverage behavior

Use one explicit frontend category mapping. The API stat parameter uses the upstream context-measure value.

| Displayed stat | API / upstream value |
| --- | --- |
| FG made / attempted | `FGM` / `FGA` |
| 3PT made / attempted | `FG3M` / `FG3A` |
| REB | `REB` |
| Off boards | `OREB` |
| Def boards | `DREB` |
| AST | `AST` |
| STL | `STL` |
| BLK | `BLK` |
| TO | `TOV` |

Defer FTM/FTA: tested playlists were empty despite positive free-throw totals. Defer PTS: Harden's playlist duplicated his six made-field-goal events, representing 15 of his 21 points, and omitted his free throws. These samples do not establish universal upstream prohibitions.

- [ ] Keep minutes, percentages, fouls, plus/minus, deferred categories and zero values as plain text.
- [ ] Treat every category as potentially partial. The target FGA sample contained 13 events but only 11 usable URLs.
- [ ] Count usable clips separately from upstream events and boxscore totals; describe results as available clips.
- [ ] Handle empty, partial and failed retrievals without breaking the boxscore.
- [ ] Keep ineligible games as plain stats without playlist requests.

### 4. Cache playlists and limit requests

- [ ] Fetch only when the user selects a stat, never during initial boxscore loading.
- [ ] Use #190's shared cache utility with bounded storage and keys covering the complete playlist selection.
- [ ] Cache nonempty playlists for 24 hours.
- [ ] Cache valid empty playlists for 15 minutes when the completed game's authoritative game datetime is within the last 72 hours.
- [ ] Cache valid empty playlists for 24 hours for older completed games.
- [ ] Determine recency from authoritative metadata retained by #190. If the date is unavailable or uncertain, use the short empty-result lifetime rather than assuming the game is old.
- [ ] Coalesce identical requests already in flight within each server process.
- [ ] Use bounded retries with exponential backoff; honor Retry-After when provided.
- [ ] Never cache upstream failures as permanent lack of coverage. Cache hits must not extend expiration.

These durations are initial implementation choices. Older footage can be repaired or backfilled, so negative results must expire.

### 5. Add boxscore interactions and the video dialog

- [ ] Keep the actual boxscore value on each stat button, such as `13 FGA`.
- [ ] Use accessible labels such as "View available field-goal attempt clips."
- [ ] Show the fetched count in the dialog, such as "11 available clips." Do not fetch counts merely to label boxscore buttons.
- [ ] Make supported stats selectable in HardwoodScorersBook, including expanded player details and the existing Off boards / Def boards values without adding columns.
- [ ] Make made and attempted shooting values separately selectable.
- [ ] Keep stat buttons as siblings of the player expansion button; selecting a stat must not toggle the row.
- [ ] Fetch through TanStack Query on selection.
- [ ] Provide selected player/stat, native controls, clip list and previous/next navigation.

Use exactly one media element:

```tsx
<video controls playsInline preload="metadata" />
```

Assign only the selected clip's returned media URL. Do not create hidden video elements, preload adjacent clips or fetch every clip's media when the dialog opens. Metadata-only preload is a browser hint; attaching only the selected source prevents playlist-wide downloads.

- [ ] Follow the React Aria modal pattern in MarqueeDatePicker, including keyboard access, Escape and focus restoration.
- [ ] Support mobile, desktop and comparison layouts.
- [ ] Stop previous playback on source changes and stop playback when closing.
- [ ] Include loading, empty-playlist, fetch-error and playback-error states.

## Relationship to other video work

This feature coexists with beads issue `nba-scores-1bk`, which proposes a specific game/event lookup through VideoEvents for a future per-play interaction. Neither supersedes or depends on the other. Shared upstream-request or normalization utilities may be reused where appropriate.

Per-play endpoints, play-by-play UI, team-total playlists, media proxying and transcoding remain outside this issue's scope. Cache infrastructure and existing-route integration belong to #190.

## Acceptance criteria

- [ ] #190 supplies reusable cached boxscore/game context; this issue does not create a duplicate boxscore cache.
- [ ] Eligibility comes from the backend and is enforced by the playlist route.
- [ ] Selecting an eligible positive stat opens available clips for the correct player, game and category.
- [ ] Made-shot playlists exclude misses; attempt playlists include available makes and misses.
- [ ] Partial media coverage is reflected in usable clip counts without changing displayed boxscore statistics.
- [ ] Initial boxscore loading triggers no playlist or clip-media lookups.
- [ ] Row expansion and stat controls work independently across mobile, desktop and comparison layouts.
- [ ] Backend tests cover context resolution, prefix/season eligibility, stat validation, normalization, null media, empty/partial results, playlist cache policy and upstream errors.
- [ ] Frontend tests cover backend eligibility, on-demand fetching, labels, selection, independent row behavior, one selected media source, dialog cleanup and loading/error/empty states.
- [ ] Recorded deployed Chrome and physical Safari checks cover direct playback, pause/resume, seeking and clip switching.
- [ ] Existing lint, build and relevant tests pass.

## Provisional estimate

| Work | Estimate |
| --- | ---: |
| Remaining video verification | 0.5–1 engineering day |
| This issue's video implementation, tests and QA after verification passes | 3–5 engineering days |
| Separate cache PR, #190 | 0.5–1 engineering day |
| Combined remaining effort | 4–7 engineering days |

The cache PR can proceed alongside verification. These are effort estimates, not elapsed delivery dates; they exclude scheduling delays and upstream outages. Re-estimate the video work if deployed direct playback fails.
