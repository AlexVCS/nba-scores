# Search browser verification

Run Vite on port 5173, then run the fixture-backed browser checks. `stage2` verifies the current feature. `stage1` runs only the migration checks and detects whether hardwood search is inline or in the dialog:

```sh
PLAYWRIGHT_MODULE=/path/to/playwright/index.mjs node scripts/verify-ask-search.mjs stage1
PLAYWRIGHT_MODULE=/path/to/playwright/index.mjs node scripts/verify-ask-search.mjs stage2
BROWSER=webkit PLAYWRIGHT_MODULE=/path/to/playwright/index.mjs node scripts/verify-ask-search.mjs stage2
```

The default browser is installed Google Chrome. WebKit requires the browser matching the selected Playwright module. Screenshots and JSON measurements are saved under `/tmp/nba-ask-search-{stage}-{browser}`. Search and scoreboard API responses are deterministic browser fixtures.

Stage 1 passed in Google Chrome and desktop WebKit on September 11, 2026. Each engine checked 16 layout states: both designs and both themes at search content widths 599, 600, and 601 pixels, plus natural 640 and 667 pixel landscape viewports for both designs. Assertions cover the exact container breakpoint, generated table labels, actual game article width, dynamic team rule, and disabled pulse animation with reduced motion. No uncaught application errors occurred.

Stage 2 passed in Google Chrome and desktop WebKit on September 11, 2026. Each engine recorded 23 states and checked:

- Original and hardwood search in light and dark themes, including the 599/600/601 pixel table breakpoint.
- Dialogs at 390×844, 640×960, 667×375, 768×1024, and 1100×900. The 640 and 667 pixel desktop presentations use compact tables. Game articles fill the available result width. Desktop dialogs stop at 768 pixels and scrolling contents have 24 pixel horizontal padding.
- Input focus on reopening, native Escape dismissal, restoration to the keyboard-focused Search trigger, and contents unmounting. Mouse opening also focuses the input.
- Queries and results survive closing, query-only navigation, and design-switcher navigation between original and hardwood. Pending searches survive Escape and finish while closed. Clearing while pending leaves no late results.
- Local spoiler reveals reset after closing; global reveal remains respected after reopening.
- Backdrop clicks dismiss, while outside-to-inside and inside-to-outside pointer drags retain the dialog.
- Reduced motion, root scroll locking, inner overscroll containment, and no uncaught application errors.

Native focus restoration returns to the element focused before `showModal()`. On macOS WebKit, mouse clicks do not normally focus buttons, so keyboard activation verifies return to Search. The application retains native behavior.

The browser script supplements provider/component tests for cancellation, predecessor replacement, stale responses, errors, and location-key behavior.

Manual iOS Safari keyboard and scrolling verification remains **unverified**, assigned to **Codex** in **nba-scores-c20**. Desktop WebKit and viewport emulation do not complete this check. On an iPhone or iPad, verify keyboard appearance and search action on every opening, scroll containment with the keyboard visible, background scroll locking, dismissal, and scroll/focus restoration.
