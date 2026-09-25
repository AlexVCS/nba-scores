# Spoiler onboarding verification

Implemented September 11, 2026 by two Codex subagents using the inherited model, with integration review and browser verification by the supervising agent. Changes remain local and uncommitted.

## Delivered

- Shared Hardwood header with Scorez hidden and bracket-specific Results hidden labels only while onboarding is visible. After acknowledgment, the control returns to its 44px icon-only shape in both preference states, with an accessible name and action tooltip.
- First-visit hint with explicit global reveal, safe dismissal, keyboard Escape within the hint, and focus restoration without scrolling.
- Versioned dismissal storage, legacy results preference support, cross-tab synchronization, and in-session fallback when storage is unavailable.
- One conditional hint wrapper. It participates in mobile layout and sits beside the desktop logo at 1280px and above. Removing it removes its extra spacing.

## Checks

- Full suite: 21 test files, 144 tests passed, including 23 new provider/component tests.
- `pnpm lint`: passed.
- `pnpm build`: passed. Vite reports a bundle-size warning for a chunk over 500 kB.
- Impeccable detector: no findings in the three changed UI components.
- `git diff --check`: passed.
- Browser inspection: light and dark themes, 320px, 390px, 900px, and desktop around 1440–1504px. No hint/control overflow; desktop hint does not overlap the logo.
- At 390px, both Show all results and Got it moved the logo's top from 273.25px to 103px. No hint element or hint-only spacing remained. Focus returned to the header control.
- Show all results revealed the game scores. Got it kept the global preference false and scores hidden. Reload and another open tab both retained dismissal.
- Playoffz showed Results start hidden before acknowledgment and Results shown/hidden afterward, while preserving the global preference across navigation.
- Native browser text zoom remains a manual check. The automation surface rejected the zoom shortcut; responsive width checks above succeeded.

## Original implementation screenshots

These captures predate the follow-up change to onboarding-only labels and the Scorez spelling. The dismissed control now shows only its icon.

Follow-up verification: all nine updated onboarding tests, lint, build, the design detector, and whitespace checks pass. Browser inspection at 390px confirms empty visible button text and a 44px square control in both hidden and shown states. The tests confirm Scorez/Results wording appears only with the hint and disappears after either action and on returning visits.

- [Current icon-only mobile header](../../output/verification/spoiler-onboarding/icon-only-mobile.png)

- [Mobile before dismissal, light](../../output/verification/spoiler-onboarding/mobile-before-got-it.png)
- [Mobile after Got it, light](../../output/verification/spoiler-onboarding/mobile-after-got-it.png)
- [Mobile before reveal, dark](../../output/verification/spoiler-onboarding/mobile-before.png)
- [Mobile after Show all results, dark](../../output/verification/spoiler-onboarding/mobile-after-show.png)
- [Playoffz bracket hint](../../output/verification/spoiler-onboarding/playoffz-mobile.png)

## Changed implementation files

- `src/context/ResultsVisibilityContext.tsx`
- `src/providers/ResultsVisibilityProvider.tsx`
- `src/providers/ResultsVisibilityProvider.test.tsx`
- `src/designs/design-1/components/HardwoodHeader.tsx`
- `src/designs/design-1/components/HardwoodResultsToggle.tsx`
- `src/designs/design-1/components/HardwoodSpoilerHint.tsx`
- `src/designs/design-1/components/HardwoodSpoilerOnboarding.test.tsx`
- `src/designs/design-1/components/Design1PlayoffBracket.test.tsx`, context mock updated to include onboarding fields.

Existing unrelated workspace edits were preserved. No backend, dependency, or stylesheet changes were needed for this feature.
