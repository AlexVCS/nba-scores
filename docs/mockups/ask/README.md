# Ask mockups

Static visual references for Ask (#189, UI task #205). Each PNG overlays hand-written HTML on a live
Gold on Hardwood (`/design-1`) page. They show layout and tone only. **The written requirements in
#205 take precedence wherever an image differs**, and the images do not verify any interaction or API
behavior. The shipped UI lives in `src/components/ask/`.

| File | Scene |
| --- | --- |
| `01a-desktop-header-entry.png` | Desktop header entry with the ⌘K hint |
| `01b-mobile-header-entry.png` | Mobile "Ask" button |
| `01-desktop-ask-empty.png` | Desktop empty state: recent searches, examples, scope note |
| `01c-desktop-typeahead.png` | Typeahead for "knicks": games first, then Ask rows |
| `02-desktop-stat-answer.png` | Single-stat answer with its final score |
| `03-desktop-games-last-week.png` | Game search resolved to the previous Monday–Sunday |
| `04-desktop-dark-which-jalen.png` | Clarification with numbered candidates (dark) |
| `05a-mobile-ask-empty-keyboard.png` | Mobile empty state above a drawn keyboard |
| `05-mobile-series-hidden.png` | Series answer (drawn hidden; see below) |
| `06-mobile-postseason-revealed.png` | Postseason summary |
| `07-mobile-dark-unsupported.png` | Unsupported question with examples (dark) |

## Where the images are out of date

These differences are intentional; follow #205 and `docs/ask-contract.md`:

- `01c` shows a "2026 East First Round NYK vs ATL" row. While results are hidden, team-specific
  playoff series suggestions (including first-round series) must not appear. Only a generic season
  bracket link may.
- `01`, `05a`, and `07` use "Did the Pistons beat the Magic in the 2026 first round?" as an always-visible
  example. It reveals that both teams qualified and met, so the shipped examples avoid naming playoff
  matchups.
- `07` says an anonymous note is kept "for up to 7 days". The retention period is owned by #201 and
  is not confirmed; the shipped copy only says a note was kept when the response sets
  `diagnostics_recorded`.
- `02`, `05`, and `06` show reveal and hide controls and striped stand-ins for hidden values. Asking is
  consent (ADR 0006): the shipped UI shows every requested answer immediately and has no reveal or
  hide controls. The empty state says that answers show as soon as you ask.
- No mockup shows loading, service failure, budget exhaustion, missing historical records, or retry
  states. See the fixtures in `src/services/ask/fixtures/`.

## Fixture dates and data

- Every scene loads `/design-1/?date=2026-02-05` (Thursday, February 5, 2026) behind the overlay.
- Relative dates assume the question was asked on Wednesday, February 11, 2026, so "last week" is
  Monday, February 2 – Sunday, February 8, 2026 (America/New_York). "Last night" in `04` is Thursday,
  February 5.
- Scores, players, and matchups were typed into the generator from the local 2025-26 API at capture
  time. They are illustrative, not verified records, and must not be used as evaluation labels.

## Static-only controls

Nothing in the overlay is interactive. The search field, caret, clear and Cancel buttons, keyboard
hints (↑↓, ↵, esc, 1–4), reveal buttons, links, and the iOS keyboard in `05a` are drawn HTML. Scene
`03` clones the page's first game card and rewrites its team labels, so its logos, status, and links
belong to a different game.

## Regenerating

Prerequisites:

1. The app and API running locally: `pnpm dev` (port 5173) and the FastAPI server on port 8000
   (see the root `AGENTS.md`). The API needs network access to NBA data for 2026-02-05.
2. `playwright-core` and a Chromium build. It is not an app dependency, so install it outside the repo:

   ```bash
   mkdir -p /tmp/ask-mockup-tools
   npm --prefix /tmp/ask-mockup-tools install playwright-core@1.59.1
   (cd /tmp/ask-mockup-tools && npx playwright-core install chromium)
   ```

Run from the repository root:

```bash
ASK_MOCKUP_TOOLS=/tmp/ask-mockup-tools node docs/mockups/ask/generate-mockups.mjs
```

Optional environment variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `ASK_MOCKUP_TOOLS` | resolve from this folder | Folder where `playwright-core` is installed |
| `ASK_MOCKUP_CHROMIUM` | Playwright's downloaded Chromium | Path to another Chrome or Chromium binary |
| `ASK_MOCKUP_BASE_URL` | `http://localhost:5173` | App origin |
| `ASK_MOCKUP_OUT` | this folder | Where PNGs are written |

The script overwrites the PNGs in `ASK_MOCKUP_OUT`.

## Known capture limitations

- Team logos load from the NBA CDN. Without network access they fall back to placeholder images,
  and if the placeholder also fails the card shows its alt text.
- The script hides every `position: fixed` element that is not part of the overlay (the design
  switcher, floating counters) so they don't cover it.
- It clicks "Got it" on the spoiler onboarding hint and toggles dark mode through the header button,
  so a changed label breaks those steps.
- Fonts load from `@fontsource`; only the weights the app imports are available, so some overlay text
  renders at the nearest loaded weight.
- Timing uses fixed waits (2.5 s after load), not network idle, so a slow API can capture a loading
  state.

## Reference material

Scenes note the Mobbin patterns they borrow from in code comments. The Mobbin screenshots themselves
are licensed reference material and are **not** stored in this repository; keep them outside it.
