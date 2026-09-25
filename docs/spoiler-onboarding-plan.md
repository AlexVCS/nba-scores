# Spoiler onboarding implementation plan

Add the approved [label and hint mockup](../output/design-mockups/onboarding/01-label-and-hint.png) to the Hardwood design. New visitors should understand why results are hidden and how to reveal them. After either hint action on mobile, the hint and its extra space disappear, moving the logo back beneath the preference controls.

## Scope and visual direction

- Update the shared Hardwood header, covering scores, playoffs, series, and boxscores. Use the existing court backgrounds, Poppins typography, warm card surfaces, gold accents, and light/dark tokens.
- Show a text label beside the global eye icon only while the onboarding hint is visible. Use `Results hidden` on the Playoffz bracket and `Scorez hidden` elsewhere. After dismissal or reveal, return to the compact icon-only control in both preference states, retaining its accessible name and action tooltip. The preference remains global.
- Add a one-time, nonmodal hint anchored to that control. Keep the page usable throughout.
- Preserve the existing date-specific `Reveal scores` button and round-specific reveal behavior. The header control and hint's reveal action use the existing global preference.
- No backend work, new dependencies, welcome screen, or multi-step tour.

## Copy and actions

Hint heading: **Results start hidden** on the Playoffz bracket; **Scorez start hidden** on scores, series, and boxscore pages.

Body: **Avoid spoilers while you browse. Use this button to show all results.**

| Interaction | Results preference | Hint behavior |
| --- | --- | --- |
| First visit with results hidden and no saved dismissal | Stay hidden | Show hint |
| Select `Show all results` in the hint | Explicitly set global preference to true | Dismiss and remember |
| Select `Got it` | Leave results preference unchanged | Dismiss and remember |
| Activate the labeled header control | Toggle the existing global preference | Dismiss and remember |
| Press Escape while focus is inside the hint | Leave results preference unchanged | Dismiss and remember |
| Reload or navigate after dismissal | Honor saved results preference | Keep hint closed |
| Arrive with global results already enabled | Honor saved results preference | Skip onboarding and treat it as acknowledged |

Ordinary page clicks do not reveal results or dismiss the hint. Existing users with hidden results and no onboarding dismissal receive the hint once when this feature ships. Clearing browser storage resets that behavior. A date- or round-specific reveal does not enable the global preference.

## Layout and accessibility

- Widen the results control only while onboarding is visible. Afterward, restore its 44px square icon-only shape. Keep the theme control separate.
- On wide desktop layouts, place the hint below and right-aligned with the results control, with a small pointer. It must not overlap the logo, navigation, or date controls.
- On mobile and widths without room beside the logo, render the hint in normal document flow between the preference row and logo. Let its height follow its content, including text wrapping and zoom.
- Render the hint, its wrapper, and all hint-only spacing conditionally as one unit. Both actions remove that entire unit immediately. Do not leave a fixed-height placeholder, minimum height, empty grid row, or padding behind. The logo retains only its ordinary header spacing.
- Use one hint instance across breakpoints so resizing cannot reset dismissal or duplicate accessible content. Keep its contents within the viewport at 320px and above.
- Use a labeled help region with real buttons, not an interactive `role="tooltip"`. Do not steal focus on page load, trap focus, dim the page, or block scrolling. Associate the visible hint with the results control through `aria-describedby`.
- Keep `aria-pressed` tied to the global preference and provide an accessible name containing the visible label and intended action. When an action removes the focused hint button, return focus to the global results control with scrolling suppressed.
- Avoid a competing hover tooltip while onboarding is open. A short action tooltip may remain afterward. Do not require animation for dismissal; the collapse should be immediate and work with reduced motion.

## Implementation sequence

1. **Extend the existing preference state.** In `src/providers/ResultsVisibilityProvider.tsx` and `src/context/ResultsVisibilityContext.tsx`, add acknowledged/dismissed onboarding state and a dismissal action. Store it independently under a versioned key such as `nba-scorez:design-1:spoiler-onboarding:v1:dismissed`. Reuse `setShowAllResults(true)` for the hint action, rather than toggling blindly. Preserve the current results key, legacy-key fallback, and results synchronization.
2. **Make initialization and persistence predictable.** Read dismissal in the lazy initializer so returning visitors do not see a flash of the hint. A saved enabled-results preference counts as prior acknowledgment. Keep dismissal in provider memory so route changes do not repeat it, even when localStorage writes fail. Catch storage errors using the project's existing pattern. Synchronize acknowledgment across tabs and dismiss an active hint if another tab enables global results. If storage is unavailable, persistence is limited to the current application session.
3. **Update the labeled control.** Modify `src/designs/design-1/components/HardwoodResultsToggle.tsx` to show the state label only while its hint is visible, expose the control ref for focus restoration, and acknowledge onboarding on direct activation. Derive the wording in `HardwoodHeader.tsx` from its existing `section` prop: use `results` when `section === "playoffs"` and `Scorez` otherwise. Pass that wording to the control and hint so the visible label, accessible name, and hint heading agree. Preserve existing pressed styling and global toggle semantics.
4. **Add the hint and place it in the header.** Create `src/designs/design-1/components/HardwoodSpoilerHint.tsx` with the agreed copy and actions. Integrate it through `HardwoodHeader.tsx`, using the same provider state on every Hardwood page. Use existing Tailwind utilities and tokens; add a small scoped rule in `hardwood.css` only if needed for placement or the pointer. Select the desktop placement breakpoint based on available logo/control space, falling back to the mobile flow whenever they would overlap.
5. **Verify behavior and layout.** Add focused React Testing Library/Vitest coverage for disclosure and persistence, run the quality gates, and inspect the approved initial and dismissed states in the browser. Keep all changes local unless separately asked to commit or push.

## Acceptance checks

- A fresh visitor sees the label and hint with results still hidden.
- While onboarding is open, the Playoffz bracket displays `Results hidden` and `Results start hidden`; other pages use `Scorez hidden` and `Scorez start hidden`. Verify that the label disappears with the hint and stays absent after reveal, hide, reload, and navigation.
- `Got it` dismisses without changing results; `Show all results` enables the global preference and removes the onboarding label. Neither action can accidentally invert an already-updated preference.
- Dismissal persists through reloads, header remounts, and navigation between Hardwood pages. Existing enabled-results and legacy preferences are respected. Storage failures do not break either action or repeatedly reopen the hint during navigation.
- The existing date and round controls retain their scope; global results still propagate to scores, brackets, series, and boxscores.
- Keyboard users can reach both actions, dismiss with Escape from within the hint, and retain sensible focus afterward. Opening the hint does not move focus.
- Browser checks cover mobile at 320px and 390px, an intermediate width, and desktop around 1440px, in both themes. Check text zoom, pointer placement, and initial versus dismissed layout. Confirm both mobile actions restore the same normal logo position with no leftover gap.
- Add component/provider tests for the behavior above, including cross-tab acknowledgment and Strict Mode initialization. Verify actual spacing in the browser because jsdom cannot prove layout collapse.
- Run the focused new tests, `pnpm test:run`, `pnpm lint`, and `pnpm build`. Report unrelated pre-existing failures separately. Run Impeccable's detector once against the changed UI files after implementation. Inspect desktop and mobile in one bounded pass, fix findings together, and perform at most one confirmation pass.

## Completion criteria

The approved hint works on every Hardwood header, respects saved preferences, and never reveals results through dismissal. Both mobile actions remove the extra hint space. Hand off the changed-file summary, checks run, and screenshots of the initial and dismissed mobile states.

Implemented locally on September 11, 2026. See the [verification record](verification/spoiler-onboarding.md) for checks, screenshots, and the remaining manual zoom check.
