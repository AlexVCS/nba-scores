# Bracket spacing verification

Verified September 4, 2026 against the running Hardwood preview and local API, using Chromium through Playwright.

## Results

- Both complete 80-season sweeps (1946–2025 starting years) pass: 1600 × 1000, light theme, global results shown; and 1440 × 1000, dark theme, results hidden.
- The representative matrix passes at 1440, 1600, and 2048px, in both themes. It checks hidden results, every available round reveal, bracket show/hide all, and the actual global results toggle in both directions.
- Real response fixtures cover 1949-50, 1952-53, 1953-54, 1962-63, 1974-75, 1977-78, 1983-84, 2001-02, 2002-03, and 2025-26. The 1977-78 case preserves the adjacent-track regression discovered during verification.
- Mobile checks at 1439px and 390px, both themes, show no page overflow and retain the mobile renderer.
- At 150% root text size, the 1952-53 and 2025-26 hidden brackets pass. Wrapped locked cards reach 287px tall in the modern case without colliding.
- Across the completed sweep, original nine-season matrix, and additional 1977-78 matrix: **688 browser states**, **4,128 round measurements**, minimum divider clearance **16px**, minimum adjacent-card clearance **16px**, connector endpoint error **0px**, cross-column grid offset **0px**, and page overflow **0px**. Exact-track centers remain stable through revealing and hiding results.
- A dark, hidden-results screenshot at 2048px was visually reviewed.
- Final application checks: all **101 Vitest tests** pass; `pnpm lint` and `pnpm build` pass.

The first implementation sweep exposed overlaps in 1976-77 through 1978-79, where consecutive occupied rows require a larger pitch than alternate rows. After that correction, both full 80-season sweeps were repeated successfully. The representative matrix also ran after the correction.

The dedicated BAA renderer is unchanged. Its seasons participate in route and page-overflow checks; the shared desktop round/card geometry assertions apply to the general bracket renderer, including its historical fallback layouts. Mobile checks cover hidden results; the full reveal-stage matrix covers desktop.

## Reproduce

Start the frontend and API using the repository's normal development commands. Supply a valid local preview playoffs URL; the script does not embed the preview token. Playwright and its Chromium browser must already be available.

```sh
PLAYWRIGHT_MODULE=/path/to/playwright/index.mjs \
  node scripts/check-bracket-spacing.mjs "$PREVIEW_PLAYOFFS_URL" /tmp/nba-bracket-spacing
```

`PLAYWRIGHT_MODULE` is optional when `playwright` is resolvable normally. The script adds no package or test-framework dependency. Fixtures in `scripts/fixtures/bracket-spacing` are used by default; other seasons use the local API. Output includes response snapshots, detailed measurements, failures, and a screenshot. A nonzero exit status indicates a failed assertion.

Optional environment settings:

- `SKIP_SWEEP=1`: run only the representative matrix and mobile/enlargement checks.
- `SWEEP_ONLY=1`: run the two full sweeps and mobile/enlargement checks.
- `BRACKET_SEASONS=1977-78`: select representative seasons (comma separated).
- `BRACKET_FIXTURES=/path/to/cache`: replay previously captured API responses, fetching missing seasons normally.

Local evidence from this session: `/tmp/nba-spacing-sweep-final`, `/tmp/nba-spacing-matrix-final`, and `/tmp/nba-spacing-adjacent-final`. These generated artifacts are not committed.
