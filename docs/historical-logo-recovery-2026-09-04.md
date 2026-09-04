# Historical logo recovery

Reviewed by Codex on 2026-09-04.

Nine historical team identities now have app-served logos that were absent from the active mapping. Seven already had candidate files in the ignored backup directory but were never enabled. Waterloo and Sheboygan are new downloads. This closes eight of the nine missing tricodes in the June audit, plus the Washington Capitols case. Indianapolis Jets remains unresolved.

## Added to the app

These are representative archive images, not a claim that every mark was used in every season listed. Source sites sometimes use later redrawings. No artwork was generated or upscaled. All files live in `public/images/historical-team-logos/`, with matching recovery copies under ignored `.logo-backups/historical-team-logos/`.

| Team | Lookup | NBA/BAA seasons covered | Image | Dimensions | Source and discovery |
|---|---|---|---|---|---|
| Indianapolis Olympians | INO | 1949-50 through 1952-53 | [View ino-indianapolis-olympians-1949-1953.png](../public/images/historical-team-logos/ino-indianapolis-olympians-1949-1953.png) | 250x250 | [Source page](https://sportslogohistory.com/indianapolis-olympians-primary-logo/); Candidate already in local backups |
| Milwaukee Hawks | MIH | 1951-52 through 1954-55, representative 1952-54 mark | [View mih-milwaukee-hawks-1952-1954.png](../public/images/historical-team-logos/mih-milwaukee-hawks-1952-1954.png) | 250x250 | [Source page](https://sportslogohistory.com/milwaukee-hawks-primary-logo/); Candidate already in local backups |
| Cleveland Rebels | CLR | 1946-47 | [View clr-cleveland-rebels-1946-1947.png](../public/images/historical-team-logos/clr-cleveland-rebels-1946-1947.png) | 250x250 | [Source page](https://sportslogohistory.com/cleveland-rebels-primary-logo/); Candidate already in local backups |
| Detroit Falcons | DEF / DTF | 1946-47 | [View def-detroit-falcons-1946-1947.png](../public/images/historical-team-logos/def-detroit-falcons-1946-1947.png) | 250x250 | [Source page](https://sportslogohistory.com/detroit-falcons-primary-logo-nba/); Candidate already in local backups |
| Pittsburgh Ironmen | PIT | 1946-47 | [View pit-pittsburgh-ironmen-1946-1947.png](../public/images/historical-team-logos/pit-pittsburgh-ironmen-1946-1947.png) | 250x250 | [Source page](https://sportslogohistory.com/pittsburgh-ironmen-primary-logo/); Candidate already in local backups |
| Washington Capitols | team ID 1610610036, not a global WAS override | 1946-47 through 1950-51 | [View was-washington-capitols-1946-1951.png](../public/images/historical-team-logos/was-washington-capitols-1946-1951.png) | 250x250 | [Source page](https://sportslogohistory.com/washington-capitols-primary-logo/); Candidate already in local backups |
| Anderson Packers | AND | 1949-50 | [View and-anderson-packers-1949-1950.webp](../public/images/historical-team-logos/and-anderson-packers-1949-1950.webp) | 519x718 | [Source page](https://commons.wikimedia.org/wiki/File:Anderson_Packers_logo.PNG); Candidate already in local backups |
| Sheboygan Red Skins | SHE | 1949-50 | [View she-sheboygan-red-skins-1949-1950.png](../public/images/historical-team-logos/she-sheboygan-red-skins-1949-1950.png) | 375x125 | [Source page](https://www.statmuse.com/nba/team/sheboygan-red-skins-20/history); New download |
| Waterloo Hawks | WAT | 1949-50 | [View wat-waterloo-hawks-1949-1950.png](../public/images/historical-team-logos/wat-waterloo-hawks-1949-1950.png) | 160x132 | [Source page](https://nbahoopsonline.com/teams/Xdefunct/WaterlooHawks/index.html); New download |

## What changed

- `TeamLogos` resolves the Capitols by NBA team ID `1610610036`. The local 1946-47 playoff API confirms this ID. Today's Wizards, ID `1610612764`, still use their own CDN logo despite sharing `WAS`.
- Added mappings for AND, CLR, DEF, INO, MIH, PIT, SHE and WAT, plus DTF as an alias for DEF used by boxscore data.
- A historical tricode can now render its local image even when the team ID is zero. Previously the component forced a placeholder in that case.
- Current teams try the other NBA CDN theme variant if the preferred variant fails. The fallback stops after the placeholder, and a change of team or theme resets the failed request state.
- Historical image failures retain the placeholder as a last resort. Substituting an active franchise's modern logo can identify the wrong city or team.
- Seattle and Vancouver already had active logos. Their archived SVGs are now served locally instead of hotlinked from Wikimedia. They are reliability improvements, not newly recovered identities.
- Scores and boxscores already supplied tricodes in the current working tree. No call-site edits were needed. The shared resolver applies to both original and Gold on Hardwood views.

## Sources and quality limits

SportsLogoHistory.com supplied the six 250x250 PNGs. Credit belongs to that archive and the respective logo owners. Anderson uses the existing 519x718 WebP backup, visually matching the [Commons media-guide scan](https://commons.wikimedia.org/wiki/File:Anderson_Packers_logo.PNG). The original Commons download could not be revalidated in this session because requests returned 403, then 429 with a descriptive user agent. The smaller StatMuse Anderson candidate was discarded in favor of the existing larger backup.

Sheboygan uses a 375x125 wordmark from StatMuse. It is an intentional exception to the old 128-pixel minimum on both axes. At 70px wide it displays about 23px tall, so it has ample source resolution. Its lettering is small at 18px, where it serves mainly as a recognizable color/shape beside the team abbreviation. Waterloo's 160x132 image is sufficient for the contained 70px display, though it is a rough historical raster and falls slightly short of 2x resolution in the 88px series header. Neither image was enlarged.

Direct downloaded assets, all HTTP 200 and decoded locally:

- INO: [Original image](https://sportslogohistory.com/wp-content/uploads/2025/07/indianapolis_olympians_1949-1953.png). SHA-256 `b4d322782112779d51cfc398811cce6482353aaa34889f9617200469033695c0`.
- MIH: [Original image](https://sportslogohistory.com/wp-content/uploads/2021/01/milwaukee_hawks_1952-1954.png). SHA-256 `e9b4c8286e3c0751b3abd6ff7d3f3d8e085c4926fbb8e69c75b280a9dc0fd56c`.
- CLR: [Original image](https://sportslogohistory.com/wp-content/uploads/2018/12/cleveland_rebels_1946-1947.png). SHA-256 `5eda73f1e8ca8d6dfcbab946fccc0b44267f89589c22d8f1cbe1150be74377b7`.
- DEF: [Original image](https://sportslogohistory.com/wp-content/uploads/2018/12/detroit-falcons-1946-1947.png). SHA-256 `653466d02e257337ac6f73c2746ffc8429fb0e56d8846cc204f3981a382c085f`.
- PIT: [Original image](https://sportslogohistory.com/wp-content/uploads/2018/12/pittsburgh_ironmen_1946-1947.png). SHA-256 `165edaf57181d6c17056a835af275e4da650567b748090f948e978ba2f734d22`.
- WAS: [Original image](https://sportslogohistory.com/wp-content/uploads/2018/12/washington_capitols_1946-1951.png). SHA-256 `4c6b551e16e9b8148e68649fcbc3af0f2e2219d13184b297bde909c6737797a1`.
- SHE: [Original image](https://cdn.statmuse.com/img/nba/players/defunct_nba_she--ytam1y0r.png). SHA-256 `d3aa051705ac58c11614fc2118bde09255de18d5840f8f6eb0e1e6d6ea9a3c53`.
- WAT: [Original image](https://nbahoopsonline.com/teams/Xdefunct/WaterlooHawks/Waterloo_hawks_logo.png). SHA-256 `5350152dbe590dd3ddfdff4224091e25afb8b967bd99bb8c4f25bac2d6276493`.

## Remaining gaps

- **Indianapolis Jets, JET, 1948-49:** no acceptable team mark verified. [StatMuse](https://www.statmuse.com/nba/team/indianapolis-jets-14/history) serves `sm-basketball-team-lg--eq9w71rj.png`, a generic basketball image despite its team-specific alt text. [TheSportsDB](https://www.thesportsdb.com/team/136392-indianapolis-jets) also lacks a logo. Neither was accepted. Do not substitute the Olympians or Pacers, which are different teams.
- **Exact era selection:** Charlotte Bobcats versus Hornets and Washington Bullets versus Wizards still need season-aware selection. Their IDs persist across those name changes. Existing backup candidates are available for Bobcats and Bullets, but were not enabled as global overrides.
- The previously documented representative mappings spanning several logo eras remain representative. This work covers the earlier missing-logo inventory, not a fresh audit of every game or every current CDN response.
- A missing local deployment asset, an unknown team, or failure of both current CDN variants can still reach the placeholder. This is not a guarantee that placeholders can never appear.

## Verification

- `pnpm test:run src/components/TeamLogos.test.tsx`: 17 tests passed, including Capitols/Wizards isolation, DTF aliasing, missing IDs, fallback exhaustion and team changes after failure.
- `pnpm lint`: passed.
- `pnpm build`: passed with the existing large-bundle advisory.
- Browser fixture: all 54 image instances decoded with nonzero natural dimensions. Visually inspected all nine additions at 18, 28, 70 and 88px on light and dark backgrounds. Fixture removed after review.
- All 44 mapped local image files passed raster decoding or SVG XML parsing.
- April 2, 1947 scores page: Capitols and Rebels loaded their local assets with nonzero natural dimensions.
- Live 1946-47 bracket: Cleveland and Washington images loaded from local paths. Both desktop and mobile markup report decoded images. Capitols series header also renders the recovered local image.
- The supplied `league-first-round-1` link returns “Series not found” in the current working tree. The current Capitols/Stags link is [division-winners-semifinal-1](http://localhost:5173/preview/219697fa704dd0bd0b90d6978ae2a48ce9ebc080202d8f00/design-1/playoffs/1947/division-winners-semifinal-1).

Changes remain local and uncommitted. Existing unrelated working-tree edits were preserved.

## Follow-up: the 1946-47 bracket

Inspected the linked Gold on Hardwood bracket again after the layout changed. All six participating teams have decoded images; none currently uses the NBA placeholder.

| Team | What the page currently shows | Remaining issue |
|---|---|---|
| Washington Capitols | Newly enabled 250x250 local PNG | Loads correctly |
| Chicago Stags | Existing 379x409 historical GIF | Raster edges and background are rough |
| Cleveland Rebels | Newly enabled 250x250 local PNG | Wide, detailed artwork becomes small inside the square slot |
| New York Knicks | Current NBA CDN logo, 150x150 | Loads, but is not the 1946-47 logo |
| Philadelphia Warriors | Existing 231x250 historical GIF | Raster artwork looks rough at small sizes |
| St. Louis Bombers | Existing 492x150 historical GIF wordmark | At a 28px square display, the artwork is only about 8.5px high and can look almost absent |

The Knicks need a season-aware override before adding their original Father Knickerbocker logo. [SportsLogos.Net dates that mark to 1946-47 through 1963-64](https://www.sportslogos.net/logos/view/6031/New-York-Knicks-Logo/1947/Primary-Logo). A global NYK mapping would incorrectly replace the logo on modern games.

This follow-up changed documentation only. The missing-image recovery did not solve exact-era selection or the readability of wide historical wordmarks. In particular, the Bombers logo is present but too short to read comfortably at bracket scale.
