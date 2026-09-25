# Ask search UI cleanup plan

Reference: StatMuse answer pages, e.g. "Stephen Curry most threes in a game".
The pattern to borrow: one big illustrated answer card in team colors, a small
"Interpreted as" line that shows how the question was read, then a stats table
with the relevant column highlighted. Everything else is secondary.

Scope: `src/components/AskSearch.tsx`, `src/components/AskResult.tsx`,
`src/components/askSearch.css`, plus a small additive change to the `/ask`
response so the frontend has the data the new card needs. No changes to the
parser, retrieval, budget, or spoiler rules.

## What is wrong today

Observed on `/design-1?date=2024-06-17` with "How many points did Tatum score
in game 5 of the 2024 Finals?" (result: Jayson Tatum, Points 31).

1. **The search is hidden behind a disclosure.** A `<details>` row labelled
   "Search games and stats" with an "Open / Close" affordance. Nothing about it
   says "type a question here".
2. **The form is mostly instructions.** Label, input, button, a three-line hint
   paragraph about what is and isn't supported, then "Try an example:" with four
   underlined example links stacked vertically. That is roughly 370px of chrome
   before any answer.
3. **The answer is at the bottom and looks like a form readout.** "Search
   results" status line, a rule, a heading, a label/value pair ("Points / 31"),
   and an underlined "Game details" link. No headline sentence, no team colour,
   no logo, no sense of which number is the answer.
4. **Examples stay on screen after a search**, pushing the result further down.
5. **The hidden state is generic.** Title becomes "Boxscore statistics", each
   value becomes the word "Hidden", the link becomes "Reveal result to view
   link". Three separate placeholders for one hidden card.
6. **Raw field labels leak through.** Game items show "Away / Home / Away score
   / Home score" as four separate fields instead of a matchup line. Series items
   show "Team 1 / Team 1 wins / Team 2 / Team 2 wins / Series winner: DEN".
7. **No "interpreted as" line.** The server already produces a structured
   interpretation (intent, mentions, date, round, game number, statistics) but
   throws it away before responding, so the user never sees how the question was
   read. This is the single most useful trust signal on StatMuse.
8. **Design-1 tokens are only partially used.** Colours come through `--hw-*`
   variables, but the type scale (display uppercase tracking, condensed
   numerals) and card shadows from `hardwood.css` are not, so the panel reads as
   a foreign block dropped under the marquee.

## Target layout

Top to bottom, inside the existing page container:

```
[ 🔍  Ask about a game, a stat, a series...                 (Search) ]
     Try:  Tatum in G5 of the 2024 Finals · Thunder on Jan 2, 2024 · 2023 Finals

┌──────────────────────────────────────────────────────────────────┐
│ ▍ team-colour rule                                              │
│ Jayson Tatum scored 31 points in Game 5 of the 2024 NBA Finals. │  ← headline
│ Interpreted as: Jayson Tatum · Points · 2024 Finals · Game 5     │  ← muted
│                                                                  │
│  Player          PTS   REB   AST   MIN                           │  ← table,
│  Jayson Tatum   [31]    8     11   40:52                         │    PTS highlighted
│                                                                  │
│  Game details →                                                  │
└──────────────────────────────────────────────────────────────────┘
```

Hidden state is the same card with the headline, table, and link replaced by a
single veiled block and one "Reveal" button. The "Interpreted as" line stays
visible because it only echoes the question, never the answer.

## Phases

### Phase 1: entry and chrome (frontend only)

- Replace the `<details>` with an always-visible search bar. One rounded field
  with a leading search icon and the submit button inside the field on desktop,
  stacked on mobile. Enter submits. Keep `role="search"` and the label, but make
  the label visually hidden and move the prompt into the placeholder.
- Drop the three-line hint paragraph. Scope limits move into the
  `unsupported` and `needs_clarification` notices where they are relevant.
- Turn the four examples into a single wrapping row of short chips prefixed
  with "Try:". Shorten the copy (the full sentence is the placeholder, the chip
  can say "Tatum, G5 of the 2024 Finals"). Clicking a chip fills and submits.
- Hide the chip row once a result or error is showing. Show it again when the
  input is cleared.
- Move the status live region so it announces but does not render a visible
  "Search results" line when the status is `ok`.
- Apply design-1 type: the headline uses the marquee display face, numerals use
  tabular figures, section labels use the 11px uppercase tracked style already
  used for "1 GAME". Use `--hw-shadow-card` and `rounded-hw` on the card.

Files: `AskSearch.tsx`, `askSearch.css`, `AskSearch.test.tsx`.

### Phase 2: answer card (needs the Phase 4 response fields)

- New `AskAnswerCard` replaces `AskResult`. It renders one card per item.
- Headline sentence built client-side from the item kind:
  - statistic: "{player} scored {value} {stat} in {context}." For several
    stats: "{player}: {v1} {s1}, {v2} {s2} in {context}."
  - leaders: "{player} led the game with {value} {stat}."
  - game: "{away} {score} at {home} {score}, {status}." with logos.
  - series: "{winner} beat {loser} 4–1 in the {round}."
  - postseason: "{team} went {wins}–{losses} in the {year} playoffs."
- Team colour rule on the card's left edge from `TEAM_COLORS[teamId]`, falling
  back to `--hw-accent`. For two-team items use a split rule. Reuse the existing
  `--team-rule` pattern from `SeriesPage.tsx`.
- Logos via the existing `TeamLogos` component. Player headshot via
  `PlayerHeadshot` when a player id is present. No plates or backdrops behind
  logos.
- Below the headline, a compact stats table. Statistic items show the player row
  with all requested stats, the requested column marked with the accent
  background. Game items show two team rows with score. Series items show two
  team rows with wins and a check on the winner.
- Link row becomes one primary action styled with `hwActionLink`.

Files: new `AskAnswerCard.tsx`, delete `AskResult.tsx`, `askSearch.css`.

### Phase 3: "Interpreted as" and spoiler cover

- Under the headline, render "Interpreted as: " followed by the interpretation
  chips from the response (Phase 4). Muted, 12px, tracked uppercase label.
- For `needs_clarification`, render the same line with the missing field shown
  as an empty chip ("Interpreted as: Tatum · Points · [which game?]") so the
  user sees exactly what to add.
- Hidden state: keep the current rule that spoiler values are omitted from the
  DOM. Visually, replace the per-field "Hidden" words with one veiled block the
  height of the headline plus table, and one "Reveal" button aligned right in
  the card header. Keep `aria-pressed`, local reveal reset on new search, and
  the global show/hide reset already covered by tests.

Files: `AskAnswerCard.tsx`, `askSearch.css`, tests.

### Phase 4: response additions (backend, additive only)

Extend `AskResponse` in `server/models/ask_response.py`:

```
interpretation: list[str]        # e.g. ["Jayson Tatum", "Points", "2024 NBA Finals", "Game 5"]
```

Extend `AskItem`:

```
context: str | None              # "Game 5 · 2024 NBA Finals" or "Jan 2, 2024"
teams: list[AskTeam]             # [{id, tricode, name}] for colour and logos
player_id: int | None            # for headshot on statistic items
```

Build `interpretation` in `server/services/ask.py` from the validated
`AskInterpretation` (mentions, date expressions, round, game number, statistic
labels). It never includes resolved results, so it is safe to show unhidden.
Fill `teams`, `player_id`, and `context` in `ask_data._game_item`,
`ask_basketball.calculate_boxscore_stats`, `calculate_series_result`, and
`calculate_postseason_summary`. Mirror the types in `src/helpers/ask.ts`.

Tests: extend `test_ask.py` and `test_ask_basketball.py` for the new fields.

### Phase 5: states and placement

- Loading: skeleton in the card's shape instead of the "Finding matching
  basketball records..." sentence.
- Error, `unsupported`, `unavailable`: inline notice inside the card slot with
  the message and two example chips.
- Placement on design-1: keep it between the marquee and the game list, but
  pull it up to sit directly under the date with `mb-6`, and match the game-list
  container width. On the original design, keep the current position.
- Mobile: chips scroll horizontally, table becomes a two-column label/value
  list, headline wraps at 22 characters per line.

## Order and effort

| Phase | Depends on | Size |
|---|---|---|
| 1 entry and chrome | nothing | half a day |
| 4 response additions | nothing | half a day |
| 2 answer card | 4 | one day |
| 3 interpreted-as and cover | 2, 4 | half a day |
| 5 states and placement | 2 | half a day |

Phases 1 and 4 can run in parallel. Ship 1 on its own if the backend change is
delayed; it already removes most of the visual noise.

## Out of scope

- Illustrated player art. Headshots from the existing component are enough.
- Multi-turn follow-ups, streaming, or changes to what the parser supports.
- Changing the spoiler model or the DOM-omission rule for hidden values.
