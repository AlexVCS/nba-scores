# Ask Search UI finish review

Reviewed the local natural language search extension in `AskSearch`, `AskResult`, and `askSearch.css` against the current Hardwood/Arena Marquee design and the original scores surface. The supplied desktop and mobile captures show a coherent insertion into the existing toolbar, with responsive stacking, accessible sized controls, and the established warm scorecard/gold/chalk-line treatment.

The finish review initially found a spoiler-state issue: a locally revealed result stayed visible after global results were enabled and then disabled. `AskResult` now clears its local reveal when `showAllResults` becomes true, matching the reset behavior used by the Scores and Series surfaces. A regression test covers the global on/off sequence.

Verdict: conditional pass resolved to pass after the reset fix. Targeted AskSearch coverage passes (6 tests); the current full Vitest run also passes (172 tests). The detector's four font-ramp findings remain advisory; the 1rem input size is intentional for iOS zoom prevention.
