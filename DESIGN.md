---
name: NBA Scorez
description: Spoiler-safe NBA scores with deep history — championship gold signage on a real court
colors:
  gold-day: "#d7a500"
  gold-night: "#ffd524"
  gold-ink: "#7c5a00"
  scoreboard-ink: "#131210"
  hardwood-tan: "#e1bb79"
  night-court-green: "#143c31"
  scorecard-white: "#fffcf3"
  scorecard-black: "#161815"
  surface-muted-day: "#f2e8d2"
  surface-muted-night: "#101310"
  court-shadow: "#55492f"
  bench-gray-day: "#6e6555"
  bench-gray-night: "#98a290"
  chalk-line-day: "#ddd2b4"
  chalk-line-night: "#2b2f28"
typography:
  display:
    fontFamily: "Poppins, sans-serif"
    fontSize: "clamp(2rem, 5vw, 4.8rem)"
    fontWeight: 800
    lineHeight: 0.98
    letterSpacing: "-0.02em"
  headline:
    fontFamily: "Poppins, sans-serif"
    fontSize: "25px"
    fontWeight: 800
    lineHeight: 1
  score:
    fontFamily: "Poppins, sans-serif"
    fontSize: "42px"
    fontWeight: 800
    lineHeight: 0.9
    letterSpacing: "-0.02em"
  body:
    fontFamily: "Poppins, sans-serif"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Poppins, sans-serif"
    fontSize: "10px"
    fontWeight: 800
    letterSpacing: "0.14em"
rounded:
  card: "10px"
  chip: "7px"
  pill: "999px"
spacing:
  chip: "8px"
  card-pad: "14px"
  card-gap: "16px"
  section: "24px"
components:
  spoiler-toggle:
    backgroundColor: "{colors.gold-day}"
    textColor: "{colors.scoreboard-ink}"
    rounded: "{rounded.card}"
    padding: "7px 14px 7px 8px"
  game-card:
    backgroundColor: "{colors.scorecard-white}"
    textColor: "{colors.scoreboard-ink}"
    rounded: "{rounded.card}"
  picker-card:
    backgroundColor: "{colors.scorecard-white}"
    textColor: "{colors.scoreboard-ink}"
    rounded: "{rounded.card}"
    padding: "12px 14px 8px"
  stat-toggle-active:
    backgroundColor: "{colors.gold-day}"
    textColor: "{colors.scoreboard-ink}"
    rounded: "{rounded.card}"
---

# Design System: NBA Scorez

## Overview

**Creative North Star: "The Arena Marquee"**

Scores as stadium signage. The one thing this system does that neighbors don't: the most important fact on any screen — tonight's date, a final score, a leader's stat line — is rendered like the giant lettering over an arena entrance: Poppins 800, uppercase, tight-tracked, and (at night) championship gold. Everything else recedes to let the marquee speak. The ground is a real court: hardwood tan by day, forest-green floodlit court by night, with painted lines and a center circle drawn faintly into the page background itself.

The component philosophy is **loud marquee, quiet cards**. Display moments shout; chrome whispers. Cards are scorecards — warm-white (day) or near-black (night) surfaces with 1px chalk-line borders, 10px corners, and soft offset shadows — and they never compete with the signage. The second voice of the system is the tiny tracked label: 8–11px, weight 800, uppercase, letter-spaced 0.08–0.26em, used for wayfinding, statuses, and column heads.

This world is spoiler-safe by construction: scores hide behind the gold reveal toggle, and nothing in the visual system leaks a result before the fan asks.

**Key Characteristics:**
- One accent: championship gold (`#d7a500` day / `#ffd524` night); no second hue anywhere
- Poppins-only; voice comes from weight (800 vs 400/600) and scale, never from a second family
- Court texture lives on the page ground only, never inside cards
- Dark mode is not an inversion — it's the night game: green court, gold-lit type
- Tabular numerals on every score and stat

## Colors

A two-scene palette — day hardwood and night court — sharing one gold accent and one warm ink family.

### Primary
- **Championship Gold — day** (#d7a500): the accent on light ground; spoiler toggle fill, active states, score emphasis, bracket markers.
- **Championship Gold — night** (#ffd524): the same accent lifted for dark ground; in dark mode it also becomes the display-type color (marquee h1, scores, leader numbers) — gold is the light source of the night scene.
- **Gold Ink** (#7c5a00): gold that must read as text on light surfaces (hover links, small gold labels on white).

### Neutral
- **Scoreboard Ink** (#131210): primary text on light surfaces; `#fff` is its night equivalent.
- **Hardwood Tan** (#e1bb79): the day page ground, wearing the painted-court texture.
- **Night Court Green** (#143c31): the night page ground; the only non-gold color with real chroma, and it belongs exclusively to the ground.
- **Scorecard White** (#fffcf3) / **Scorecard Black** (#161815): card surfaces day/night. Muted variants #f2e8d2 / #101310 for wells and inset panels.
- **Court Shadow** (#55492f day / #aab5a1 night): secondary text sitting directly on the court ground (nav, eyebrows, footer).
- **Bench Gray** (#6e6555 day / #98a290 night): muted text inside cards.
- **Chalk Line** (#ddd2b4 day / #2b2f28 night): every border and divider; always 1px.

### Named Rules
**The One Gold Rule.** Gold is the only interface accent, kept under ~10% of any screen. Team colors may appear as content only in the design-4 series hero: one 4px × 56px rule between each modern team's tricode and name, using the raw team color by day and a fixed 65% team-color/white mix at night. If either team has no known color, both rules are omitted. Team-color washes, gradients, and accent side-borders remain prohibited. Any other second saturated hue (violet, blue, red) is a system violation — the stock react-aria purple palette is the canonical counter-example and has been rejected.
**The Ground Stays Ground Rule.** Court green and hardwood tan never appear inside a card or control; they are the floor the scorecards sit on.

## Typography

**Display Font:** Poppins 800 (with sans-serif fallback)
**Body Font:** Poppins 400/600
**Numbers:** Poppins 800, `font-variant-numeric: tabular-nums`

**Character:** One family, two voices. The marquee voice is 800-weight uppercase with tight tracking (-0.02em) and line-height under 1 — signage, not paragraphs. The service voice is small, quiet 400/600 text and micro-labels tracked wide open (0.08–0.26em).

### Hierarchy
- **Display / Marquee** (800, clamp(2rem, 5vw, 4.8rem), lh 0.98, ls -0.02em, uppercase): the date marquee and playoff intros; gold in dark mode, ink in light.
- **Score** (800, 42–48px, lh 0.9, tabular): team scores on cards; gold in dark mode. Boxscore hero scores scale to clamp(3rem, 8vw, 6rem).
- **Headline** (800, 25–30px, lh 1, uppercase in this theme): card team names, section headers, ledger titles.
- **Body** (400/600, 12–13px): supporting copy, table cells (11px, tabular, right-aligned).
- **Label** (800, 8–11px, ls 0.08–0.26em, uppercase): eyebrows, statuses, column heads, nav, footer — the system's connective tissue.

### Named Rules
**The Two Voices Rule.** Every text element is either marquee (800/large/tight) or service (small/tracked/quiet). Mid-size medium-weight text is a smell — promote it or demote it.

## Layout

Single centered column, `min(1180px, calc(100% - 48px))`, on the textured court ground. The scores page stacks: masthead (logo centered, nav beneath) → marquee intro band (generous `clamp(34px, 6vw, 78px)` top padding) → hairline toolbar → two-up game-card grid (16px gap, single column under ~700px) → tracked-label footer. Wider artifacts (bracket 1320px, boxscore tables 1180px, series hero 980px) keep the same centering. Density is comfortable: cards carry 14–24px internal padding; the ground is allowed to breathe around the marquee. Vertical rhythm favors more space above headings than below.

## Elevation & Depth

Soft, offset, ambient. Cards float on the court with `0 10px 26px rgb(43 29 6 / 14%)` (day) or `0 18px 42px rgb(0 0 0 / 50%)` (night); small controls use the lighter `0 5px 14px` / `0 8px 22px` equivalents. Depth responds to state: game cards lift `-3px` on hover with a deeper shadow over 180ms ease. No glows, no zero-offset halos, no hard neobrutalist blocks.

### Shadow Vocabulary
- **card** (`0 10px 26px rgb(43 29 6 / 14%)` day / `0 18px 42px rgb(0 0 0 / 50%)` night): game cards, pickers, panels.
- **small** (`0 5px 14px rgb(43 29 6 / 14%)` day / `0 8px 22px rgb(0 0 0 / 45%)` night): toggles, chips, sticky switchers.

## Shapes

Rounded-rectangle scorecards: 10px radius on every card and control (`--radius`), 7px on nested chips (spoiler icon tile), full-round only for the day-cell circles in calendars and the floating design switcher. Borders are always 1px chalk line; emphasis comes from the 3–4px gold bottom rule under major section headers (player ledger, series games) — the one place a thick line is allowed. No accent side-borders on cards.

## Components

### Spoiler Toggle (signature)
The brand's promise as a control. Gold fill, scoreboard-ink text, 800/11px uppercase, 10px radius, 42px min-height, leading 27px icon tile in the contrast color. `role="switch"`; pressed state persists. It is deliberately the loudest control on the page.

### Game Cards
- **Corner:** 10px; **border:** 1px chalk line; **background:** scorecard white/black; **shadow:** card.
- Three bands: status strip (9px tracked labels, center game state), matchup grid (team designations 8px tracked, names 24-25px 800 uppercase, scores 42-48px tabular — gold at night), footer links (10px tracked, gold on hover).
- Hover: translateY(-3px) + deeper shadow, 180ms ease; suppressed under reduced-motion.
- Entrance: staggered 70ms fade-up per card index.

### Marquee Intro / Date Picker Band
The h1 marquee (display spec above) with the date control. Direction of travel (per the confirmed shape brief): the marquee itself is the picker trigger — centered, flanked by day steppers, opening a calendar popover (desktop) or bottom sheet (mobile) themed as a scorecard: dark/warm surface, gold focus ring and selected day, non-italic placeholder, no-game days struck through in muted ink.

### Inputs / Fields
- **Style:** surface-muted field on a scorecard, 1px chalk-line border, 10px radius, white/ink text.
- **Focus:** 2px gold ring; focused date segment fills gold with ink text.
- **Never:** violet/purple states, italic placeholders, white fields inside dark cards.

### Stat Toggle / Team Switch
Segmented controls on a scorecard well: 1px border container (radius +3px), transparent buttons in bench gray, active segment gold with ink text, 800/10-12px uppercase tracked.

### Tables (Player Ledger)
Scorecard surface, 1px row rules, right-aligned tabular 11px cells, 9px tracked column heads in bench gray, sticky first column, 3-4px gold rule under the ledger header with a 36px gold index numeral.

### Navigation
Centered under the logo masthead: 12px 800 uppercase tracked links in court shadow; active link in full ink with a 3-4px gold underline bar.

## Do's and Don'ts

### Do:
- **Do** reserve gold for the marquee, scores, active states, and the spoiler toggle — and let it be the display color in dark mode.
- **Do** keep every border 1px chalk line; express emphasis through the gold bottom rule (3–4px) under major headers only.
- **Do** use tabular numerals and 800 weight for every number that is a score or stat.
- **Do** keep the court texture on the page ground and let cards float over it with soft offset shadows.
- **Do** keep spoiler-hidden as the default state of anything that could reveal a result.

### Don't:
- **Don't** introduce a second accent hue; the react-aria demo violet/purple is the named anti-pattern.
- **Don't** put mid-size, mid-weight type on screen — every element speaks marquee or service, per The Two Voices Rule.
- **Don't** use italic placeholders, white fields inside dark cards, or gray-on-color secondary text (tint from the surface's own family instead).
- **Don't** decorate cards with accent side-borders, glows, or gradient text.
