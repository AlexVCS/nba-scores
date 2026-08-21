# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

NBA fans — real consumer users checking scores, reading boxscores, and exploring playoff history. The core scene: a fan who recorded or will watch a game later and wants to browse scores without having results spoiled, plus fans digging into historical seasons and playoff runs.

## Product Purpose

NBA Scorez (nbascorez.com) surfaces NBA scores, boxscores, and playoff data going back to the 1946/47 season. Success means fans can follow the league — current and historical — quickly and on their own terms (spoiler-free by default).

## Positioning

Two claims neighboring score sites don't truthfully make together:

- **Spoiler-safe viewing.** Scores are hidden by default with a reveal toggle (persisted via localStorage), so fans can navigate games without ruined results.
- **Deep history.** Boxscores and interactive playoff brackets for every season back to the league's founding in 1946/47, with round-by-round reveal to avoid bracket spoilers.

## Operating Context

- Live site: https://nbascorez.com (Playoffs page at /playoffs).
- Frontend: React 18 + TypeScript + Vite + Tailwind CSS 4, TanStack Query, React Router 7, react-aria / React Aria Components, Framer Motion, React Flow (desktop playoff bracket). Dark mode toggle exists.
- Backend: FastAPI (Python) serving games, boxscore, and playoff data; dev server at http://127.0.0.1:8000 (`uvicorn server.main:app --reload`), frontend via `pnpm dev` at http://localhost:5173.
- Date navigation via a date picker; during off-season a date with games (e.g. `?date=2026-02-05`) is needed to see populated game cards.
- Watch links on playoff series exist for 2012/13 onward, depending on League Pass availability.

## Capabilities and Constraints

- Core surfaces: daily scores (game cards), boxscores with player tables, playoff brackets (React Flow on desktop, mobile-specific bracket/series cards), series detail with game-by-game breakdown.
- Season/year picker covers 1946/47 to present; playoff results toggle round by round.
- A token-gated design preview system (`/preview/<token>/design-N/`) hosts four design variants, each a folder in `src/designs/` with page wrappers plus a `theme.css`.
- **Undecided:** the final UI direction. The four previews are exploration — the owner intends to take pieces they like from several variants into one new overall redesign. No single variant is the chosen winner; future design work should help converge on that direction, not assume one.

## Brand Commitments

- Name: NBA Scorez (playful "z" spelling carries into feature names: Scorez, Playoffz).
- Existing logo assets in `public/images/` (including a dark-mode logo).
- Owner: Alex Curtis-Slep (AlexVCS on GitHub).

## Evidence on Hand

- Real NBA data via the FastAPI backend (games, boxscores, playoffs back to 1946/47); example API responses in repo root (`exampleGamesResponse.json`, `exampleBoxScoreResponse.json`, `examplePlayoffGamesResponse.json`).
- Screenshots of current UI in `public/images/`.
- No testimonials, press, or usage metrics on hand — do not fabricate any.

## Product Principles

1. **Never spoil by default.** Any surface showing results must respect hidden-scores-first; reveal is always the user's explicit choice.
2. **History is a first-class feature, not an archive.** Browsing 1954 should feel as intentional as browsing last night.
3. **Fast, focused, fan-first.** A scores check is a quick ritual; no clutter between the fan and the game.
4. **Converge the design exploration.** New visual work should draw from the strongest pieces of the four previews toward one coherent identity rather than adding more divergence.

## Accessibility & Inclusion

The codebase commits to accessible primitives (react-aria / React Aria Components, Adobe React Spectrum); interactive controls like the spoiler toggle use proper ARIA roles (`role="switch"`). Future work should keep this bar. No additional user-specific requirement established.
