# Historical Team Logo Acceptance

This document defines the acceptance checklist for new entries in
`src/constants/historicalTeamLogos.ts`.

`HISTORICAL_TEAM_LOGOS` exists for team tricodes whose current NBA CDN logo is
historically inaccurate, missing, or misleading for older seasons. A logo URL is
not acceptable just because it returns `200 OK`; it must be a real, visible
image when rendered by the app.

Accepted logos should also have a backup outside normal repo history. Remote
URLs can disappear, change content, block hotlinking, or replace assets without
warning; the backup is the fallback source of truth if that happens.

## Current Logo Rendering Path

- Historical logos live in `src/constants/historicalTeamLogos.ts`.
- `src/components/TeamLogos.tsx` checks `HISTORICAL_TEAM_LOGOS[tricode]`.
- If no historical URL exists, `TeamLogos` falls back to
  `https://cdn.nba.com/logos/nba/${teamId}/global/L/logo.svg`.
- If the image load errors, `TeamLogos` falls back to `placeholderTeamLogoUrl`.

Current limitation:

- Playoff views pass `tricode` into `TeamLogos`, so historical logos are active
  there.
- The scores list and boxscore summary currently call `TeamLogos` without
  `tricode`, so historical mappings cannot be visually verified there until
  those call sites pass tricodes.

## Required Metadata For Each Candidate

Record this metadata before accepting a candidate logo:

- Team tricode, for example `SEA`.
- Historical team name, for example `Seattle SuperSonics`.
- Season range the logo is meant to cover.
- Candidate URL.
- Source site.
- Image format, for example `svg`, `png`, `webp`, or `gif`.
- Intrinsic dimensions if raster.
- Backup location outside normal repo history.
- Reviewer name/date.

## Network And Image Validation Checklist

A candidate logo must pass these checks:

- URL returns `200 OK`.
- Response `Content-Type` is an image type, or the downloaded body clearly
  decodes as an image.
- Response is not an HTML page, redirect warning page, blank page, hotlink
  placeholder, tracking page, or search-result wrapper.
- Image has non-zero file size.
- Image decodes in a browser tab.
- Browser reports `naturalWidth > 0` and `naturalHeight > 0`.
- Transparent logos have actual visible pixels, not only an empty transparent
  canvas.
- Remote host allows browser usage from the local app; the logo is not blocked
  by CORS, anti-hotlinking, referrer restrictions, or mixed-content rules.
- URL is stable enough for app use. Prefer canonical static asset URLs over
  proxy, search, or cache URLs.
- A backup copy has been saved outside normal repo history.

## Local Backup Requirements

Every accepted historical logo should have a backup copy, but backup images do
not need to be committed to this repo. Keep the remote source URL in
`src/constants/historicalTeamLogos.ts` only after the backup exists and has been
verified.

Recommended backup locations:

- Durable off-repo storage, such as a cloud drive, object storage bucket, or
  asset archive controlled by the project owner.
- Local ignored workspace storage under:

```text
.logo-backups/historical-team-logos/
```

`.logo-backups/` is ignored by git and should not be committed. It is useful for
local recovery, but durable off-repo storage is safer if another machine or
deployment needs access later.

Use predictable lowercase filenames:

```text
{tricode}-{team-slug}-{start-season}-{end-season}.{ext}
```

Examples:

```text
sea-supersonics-1967-2008.svg
van-grizzlies-1995-2001.svg
noh-hornets-2002-2013.png
```

Backup acceptance rules:

- Save the original accepted asset when possible, not a screenshot.
- Keep the same image format unless conversion is needed for browser
  compatibility or quality.
- Do not upscale raster images to make them appear to meet the minimum size.
- Re-run the same image quality checks against the backup file.
- Record the backup location in the acceptance notes.
- Do not place backup images under `public/` unless intentionally promoting them
  to app-served assets. Files under `public/` are repo/deploy assets and should
  be treated as part of the application.
- If the remote URL changes, disappears, or starts rendering the wrong image,
  recover the asset from backup and either upload it to a stable source or
  intentionally add it under `public/images/historical-team-logos/`, then switch
  the app to that stable URL/path. A local app path would look like
  `/images/historical-team-logos/sea-supersonics-1967-2008.svg`.
- If the remote source is intentionally kept as the primary URL, record the
  matching backup location in the review notes.

## Quality Requirements

- SVG is preferred because it scales cleanly at every app size.
- Raster images are acceptable only if they remain crisp at the largest current
  display size.
- Raster images should be at least `128x128` intrinsic pixels, because the
  largest current CSS display is `64x64` and high-density screens need 2x source
  pixels.
- Image should have a transparent or visually clean background.
- Logo should not be tightly cropped in a way that touches the image edge.
- Logo must remain recognizable at `18x18`, the smallest playoff bracket size.
- Animated GIFs should be avoided unless no better static asset exists.
- Avoid remote image proxy URLs such as search-result or CDN indirection links
  when a canonical image URL is available.

## Existing App Logo Sizes

| App Area | Component | Viewport/Context | Logo Size |
|---|---|---:|---:|
| Scores game cards | `src/routes/games/GameCard.tsx` | all current card layouts | `48x48` |
| Boxscore/game summary | `src/components/GameSummary.tsx` | mobile | `48x48` |
| Boxscore/game summary | `src/components/GameSummary.tsx` | desktop | `48x48` |
| Playoff bracket node | `src/components/BracketSeriesNode.tsx` + `src/utils/bracketSizing.ts` | `sm` | `18x18` |
| Playoff bracket node | `src/components/BracketSeriesNode.tsx` + `src/utils/bracketSizing.ts` | `md` | `28x28` |
| Playoff bracket node | `src/components/BracketSeriesNode.tsx` + `src/utils/bracketSizing.ts` | `lg` | `48x48` |
| Mobile playoff series card | `src/components/MobileSeriesCard.tsx` | mobile list/card | `28x28` |
| Playoff series detail header | `src/routes/playoffs/SeriesDetail.tsx` | all current layouts | `64x64` |

`TeamLogos` uses `objectFit: "contain"`, so the full logo should fit inside a
square without distortion.

## Manual App Verification Checklist

Run the app locally:

```bash
source server/venv/bin/activate
uvicorn server.main:app --reload
pnpm dev
```

Before accepting a new logo:

1. Add the candidate temporarily to `src/constants/historicalTeamLogos.ts`.
2. Save the accepted image to an off-repo backup location or
   `.logo-backups/historical-team-logos/`.
3. Verify the backup file opens directly in the browser.
4. Open a playoff season where the historical tricode appears.
5. Verify the logo is visible in the playoff bracket.
6. Resize the browser or use responsive devtools to check bracket sizes:
   - small bracket logo: `18x18`
   - medium bracket logo: `28x28`
   - large bracket logo: `48x48`
7. Open the matching series detail page and verify the header logo at `64x64`.
8. On mobile-width viewport, verify the mobile series card logo at `28x28`.
9. Confirm the logo does not show the NBA fallback placeholder.
10. Confirm the image does not collapse to an empty square, broken-image icon,
   blank white/transparent area, or unrelated hotlink placeholder.
11. Confirm light and dark modes both remain legible where relevant.
12. If scores or boxscore call sites are updated later to pass `tricode`, verify
    the logo there at `48x48`.

## Acceptance Template

Copy this template into the issue, PR, or review notes for each candidate logo:

```markdown
## Historical Logo Acceptance

- Team/tricode:
- Historical team name:
- Season range:
- Candidate URL:
- Source:
- Format:
- Intrinsic size:
- Backup location:
- Reviewer/date:

### Network/image checks

- [ ] Returns HTTP 200
- [ ] Response is an actual image, not HTML or a blank/interstitial page
- [ ] Decodes in browser
- [ ] `naturalWidth` and `naturalHeight` are greater than 0
- [ ] Visible pixels are present
- [ ] Host allows rendering inside the app
- [ ] URL is stable/canonical enough for app use
- [ ] Backup file is saved outside normal repo history
- [ ] Backup file opens directly in the browser

### Quality checks

- [ ] SVG, or raster image is at least 128x128
- [ ] Looks clear at 64x64
- [ ] Remains recognizable at 18x18
- [ ] Background/cropping works in the app's square logo container
- [ ] Does not look distorted with `object-fit: contain`

### App checks

- [ ] Playoff bracket renders the logo at 18/28/48px as applicable
- [ ] Mobile playoff series card renders the logo at 28px
- [ ] Series detail renders the logo at 64px
- [ ] Logo is visible in both light and dark themes where relevant
- [ ] Fallback placeholder is not shown
- [ ] Scores/boxscore 48px check completed if those views pass `tricode`
```
