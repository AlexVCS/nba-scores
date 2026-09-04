# Historical bracket spacing

Audit date: September 4, 2026. Scope: the Hardwood `design-1` playoff preview shown in the supplied screenshot. The plan below records the original findings; the spacing fix has now been implemented locally.

Tracked as P2 bug `nba-scores-5k6`. Implementation and browser verification are documented in [bracket-spacing-verification.md](bracket-spacing-verification.md).

## Findings

Browser measurements across all 80 seasons from 1946-47 through 2025-26 found 33 seasons with only **2 CSS pixels** between the round divider and the first matchup card. Adjacent opening-round cards also have only 2px clearance when both are 126px tall. Other seasons have at least 16px below the divider in the measured all-results view.

| Affected seasons | Count | Crowded round |
| --- | ---: | --- |
| 1948-49 | 1 | Conf. Semifinals |
| 1950-51 through 1952-53 | 3 | Conf. Semifinals |
| 1962-63 | 1 | First Round |
| 1974-75 through 2001-02, inclusive | 28 | First Round |

These findings describe the current local API responses and renderer. The list is not a claim that all historical series-length metadata is correct. For example, some surrounding 1950s and 1960s seasons currently render shorter cards without a series-length strip. Fix the geometry based on content, rather than maintaining a list of years.

The complete per-season measurements are in [bracket-spacing-audit.json](bracket-spacing-audit.json). The sweep navigated the live React route and read rendered DOM bounds, using the local FastAPI data. Baseline: 1600 × 1000 CSS pixels, light theme, global results shown. The supplied 1952-53 case was also reproduced visually with dark theme and results hidden.

A second full 80-season sweep at 1440 × 1000, dark theme, results hidden, found the same 33 affected seasons. See [bracket-spacing-hidden-audit.json](bracket-spacing-hidden-audit.json). In 1952-53, the gap also remained 2px at 2048 × 1220. At 1439px and 390px, the app used its mobile bracket, with no visible desktop round dividers and no page-level horizontal overflow. Mobile was spot-checked on 1952-53, not swept across every season. Intermediate round reveal stages remain part of the implementation acceptance pass.

## Cause

- `src/designs/design-1/components/Design1PlayoffBracket.tsx:168` uses seven 58px tracks with 6px gaps. Slots center their contents vertically. Finals repeat these values at line 319.
- The round heading's 16px bottom margin and the slot grid's 20px top margin provide 36px before the first track. A 126px card overflows the 58px track upward by 34px, leaving only 2px under the yellow divider.
- `BracketSeriesCard.tsx:25` adds a 28px series-length strip for non-seven-game series. The ordinary two-team card is 98px tall; the historical card becomes 126px tall.
- Opening matchups occupy alternate tracks. Their centers are 128px apart, leaving only 2px between 126px cards.
- Connector junctions independently hard-code a 29px half-track inset at lines 173-174. Changing track height alone would misalign those lines.
- Locked cards can grow with wrapped prerequisite text. The sizing must cover both revealed cards and locked placeholders.

## Implementation plan

1. Define shared desktop bracket geometry in `Design1PlayoffBracket.tsx` and `hardwood.css`. Use explicit minimum clearances of 16px from divider to card and 16px between neighboring cards. Reserve space for the largest relevant card or locked placeholder at the current column width. Keep geometry stable when rounds are revealed.
2. Derive track spacing and top inset from that card envelope. For alternating tracks, require twice the track pitch to be at least the maximum card height plus 16px. Require the first card's top to remain at least 16px below its divider. Use shared CSS custom properties or a small sizing helper instead of repeating numeric Tailwind classes. Do not solve this by adding top margin alone, which leaves adjacent cards crowded.
3. Apply the same geometry to both conference groups and the Finals column. Derive connector half-track insets from the track height and keep stubs anchored at slot centers. Preserve the presentation planner's existing series identities, ordering, trusted edges, and historical fallback layouts.
4. Add browser layout regression coverage using real response fixtures for 1952-53, 1962-63, 1974-75, 1983-84, and 2001-02. Include 1949-50 and 1953-54 fallback layouts and 2002-03 and 2025-26 modern controls. Keep the existing jsdom behavior tests for reveal dependencies and Finals controls.
5. Verify at 1440, 1600, and 2048px widths, plus 1439px and 390px for the mobile layout. Cover hidden results, each reveal stage, bracket-level show/hide all, global results visibility, and both themes. Check text enlargement and wrapped lock messages. Run the 80-season browser sweep again, followed by relevant Vitest tests, `pnpm lint`, and `pnpm build`.

## Acceptance criteria

- Every visible desktop matchup card or locked placeholder has at least 16px clearance below its round divider.
- Adjacent matchup cards have at least 16px vertical clearance with results hidden or shown.
- Connector endpoints remain on the intended slot centers and junctions remain connected after resizing or revealing results. Connector lines should still touch card sides; the unwanted contact is at the heading divider.
- No card, lock message, or focus outline is clipped, and the bracket does not gain unintended horizontal overflow at desktop widths.
- Mobile rendering and historical fallback layouts retain their current behavior.

## Existing test result

`pnpm test:run src/designs/design-1/components/Design1PlayoffBracket.test.tsx src/utils/bracketPresentationPlanner.test.ts src/hooks/useBracketReveal.test.tsx` passed all 13 tests. These tests cover component behavior and planning, but jsdom does not calculate the browser geometry needed to catch this defect.
