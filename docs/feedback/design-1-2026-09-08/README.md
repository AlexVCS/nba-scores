# Design One feedback review

Collected 2026-09-08 from Aman, Andy, Alex, Brian, and Abhi.

This is a source and decision document. No suggestions have been accepted by the owner yet, and no implementation tickets have been created from this review. Recommendations below are the assistant's proposed disposition, not the owner's decisions. Feedback IDs identify observations; implementation tracking belongs in Beads once scope is agreed.

## Sources and confidence

| Source | Evidence | Limits |
| --- | --- | --- |
| Aman, Alex, Brian | [Original messages](messages.md) | Platforms, original dates, device details, and exact build not supplied. |
| Andy | [Visual review with comparisons](andy-visual-review.md), [timestamped transcript](andy-transcript.md), [Loom](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304) | Reviewed selected frames alongside the full transcript, not continuous playback of every interaction. Recording compares older site and Design One. |
| Abhi | [Locally generated audio transcript](abhi-transcript.md) | Machine transcription of 2:39.7 attachment. No screen recording; exact UI targets and uncertain wording need confirmation when relevant. |

The screenshots preserve the version Andy reviewed. Current files were already modified when this review started; no claim is made that the recording matches the working tree or current deployment. PRODUCT.md identifies spoiler protection as a core principle. It also records design exploration as unresolved, so the latest preference still belongs to the owner.

## Suggested review order

1. Finding and opening games: offseason recovery, calendar use, card actions, and the reported adblocker failure.
2. Spoiler protection: what stays hidden, how to explain it, and where reveal controls belong.
3. Visual treatment: scale, contrast, court movement, and card depth.
4. Historical accuracy, logo questions, and possible product expansion.

For each observation, record **accept, adapt, investigate, defer, or decline**, then a sentence explaining the chosen behavior. Accepting a problem does not commit us to the reviewer's proposed fix. Repeated themes are grouped below, while different requests remain distinct.

## Finding and opening games

| ID | Observation and source | Proposed disposition | Decision still needed |
| --- | --- | --- | --- |
| F01 | Aman wants one-click access to the most recently played games. Andy struggles to reach populated dates during the offseason, 04:23–04:59. His older-site frame already has Last Game of the Season. | Accept the problem; adapt the shortcut to the intended destination. | Latest completed game day across the league, last game of the season, or both? |
| F02 | Aman wants to pick a favorite team and see its recent games. | Consider separately from F01; team selection adds scope. | Simple team filter, or a remembered favorite? Show a list of recent games or jump to its latest game day? |
| F03 | Andy wants to jump to the next season's start without knowing the date, 04:23–04:59. | Consider a next scheduled game shortcut alongside recent games. | Does the product need both past and future destinations? What happens before a schedule is available? |
| F04 | Alex reports that finding a game and random selection fail with an adblocker enabled and work when disabled. | Investigate first because the report concerns core functionality. Cause is unverified. | Browser, blocker/filter list, URL, and failed request are missing. Reproduce before selecting a fix. |
| F05 | Andy reports empty-state buttons below the fold on his phone, 04:02–04:23. They are visible in the captured emulator frame. | Investigate shorter mobile viewports and adapt spacing if reproduced. | Which action must be reachable immediately, and how much header space should it receive? |
| F06 | Andy discovers the date heading opens a calendar only by accident, 04:39–05:29. | Accept the discoverability problem; an explicit calendar control is a plausible response. | Icon plus current date, a labeled button, or another clear entry point? |
| F07 | Andy clicks the calendar icon inside the date sheet and says it does nothing, 05:17–05:29. | Investigate the icon's intended role. | Make it act, remove it, or communicate that it is decorative? |
| F08 | Andy questions repeated date information above the calendar divider, 05:29–05:49. | Adapt cautiously. Selected date and browsed month can differ. | What can be removed while preserving date entry and selection context? |
| F09 | Andy is unsure whether calendar marks mean unavailable dates or game days, 05:49–07:39. He suggests dots beneath dates. | Accept clarity problem; marker treatment remains open. | What states need communicating, and how are selectable dates distinguished from game availability? |
| F10 | Andy must reposition his pointer while changing months, 07:46–08:15. [Frames](andy-visual-review.md#6-month-navigation-changes-position) show changing sheet height and moving month controls. | Accept stable navigation as the desired behavior. | Fixed grid rows, stable sheet height, or a fixed header? |
| F11 | Andy expects an upcoming game card to be clickable, 07:39–07:50. | Adapt once a useful destination is defined. | Open game details, show schedule information, or make the unavailable action clearer? |
| F12 | Andy expects a past-game card to open, cannot initially find the score, and discovers Box score after reveal, 08:24–08:55. [Frames](andy-visual-review.md#7-card-behavior-spoiler-controls-and-boxscore-access). | Separate clearer game access from spoiler defaults. | Should the card open a spoiler-safe detail view or offer explicit actions with intentional reveal? |

F01 and F03 share an offseason dead end, but one goes backward and the other forward. F02 adds a team-specific path. Do not collapse them into a ticket whose behavior is unspecified.

## Spoiler protection and discovery

| ID | Observation and source | Proposed disposition | Decision still needed |
| --- | --- | --- | --- |
| F13 | Brian likes locking later historical playoff rounds until earlier results are explored, and likes the ability to toggle protection. | Preserve this positive evidence while reviewing changes. | Confirm whether existing spoiler-first positioning remains the direction. |
| F14 | Brian asks whether the toggle is easy enough to find. Andy notices reveal only after struggling with a historical game, 08:24–08:44. | Investigate naming, placement, and explanation together. Brian's question is not a reported failed task. | What should a first-time visitor understand before interacting? |
| F15 | Andy questions hiding results for games in the past, 08:35–09:07. | Adapt toward clearer purpose and controls unless the owner changes product positioning. | Retain spoiler-first defaults, offer a remembered preference, or change defaults? Existing PRODUCT.md favors retention. |

Brian and Andy express different goals. This is not a majority vote. F12 is an access problem that can be addressed independently of the spoiler policy in F15.

## Visual treatment and control size

| ID | Observation and source | Proposed disposition | Decision still needed |
| --- | --- | --- | --- |
| F16 | Andy likes the older site's proportions but finds it bland; likes Design One's basketball color/identity but finds some elements too large, 01:19–01:59. | Adapt proportions while making a separate brand choice. | Which parts should become smaller without losing the identity the owner likes? |
| F17 | Andy questions theme-icon visual weight, then revises stroke width to possible size; compares shadcn, 02:26–03:45. Starts on the older site. | Investigate Design One specifically before changing it. | Is there a current size/weight problem? Preserve usable button targets when adjusting the glyph. |
| F18 | Andy refers to earlier concerns about Scorez/Playoffz size and legibility, 03:45–04:02. | Investigate actual reading and tapping at mobile sizes. | Are the labels too small, too tightly spaced, or insufficiently prominent? |
| F19 | Andy prefers flatter styling to the court's physical texture, 09:07–10:00, despite liking its identity earlier. | Treat as a taste and brand decision. | Retain the court, soften it, or move to a flatter direction? |
| F20 | Andy finds too much nested shadow/depth in the playoff round and matchup cards, 10:00–11:16. Suggests surface tones. | Consider reducing competing depth treatments. | Which container needs separation, and which can be visually quiet? |
| F21 | Abhi says the fixed center-court circle feels jarring while the rest of the playoff page scrolls, 00:08–00:36. Suggests the court scroll too. | Investigate motion relationship separately from court removal. | Make the background scroll with content, soften it, or remove that element? |
| F22 | Abhi says the font feels off in light mode and light-colored logos lack background contrast; dark mode looks better, 00:37–01:00. | Investigate specific logos, surfaces, and type. | Which combinations fail, and what should change? This feedback is not a measured contrast audit. |
| F23 | Abhi questions playoff alignment and suggests centering, including the year dropdown, 01:05–01:19. | Investigate the exact target before enforcing centering globally. | Which controls or text look misaligned in the reviewed viewport? |
| F24 | Abhi initially looks for year typeahead, then realizes it exists, 01:19–01:36. | Record existing capability and possible discoverability issue. | Is an explanatory hint needed? Do not create a duplicate typeahead feature. |
| F25 | Abhi says the back-to-bracket left-arrow control feels small after entering a score/detail view, 02:07–02:13. | Investigate glyph size, label, and actual hit area. | Make the icon more visible, enlarge the target, add a label, or combine these? |

The reports support reviewing scale, but not indiscriminately shrinking every element. Andy finds some elements too large; Abhi finds a specific navigation control too small.

## Accuracy, rights questions, and expansion

| ID | Observation and source | Proposed disposition | Decision still needed |
| --- | --- | --- | --- |
| F26 | Brian asks whether permission exists to use the logo. | Record as an unanswered ownership/licensing question. | Which logo does he mean, and what source or permission records exist? No legal conclusion has been drawn. |
| F27 | Brian asks what the first playoff round was called in the 1960s and whether Conference Semifinals is correct. | Investigate season-specific terminology and connect to historical format work. | Which season and label are in question? Verify before changing labels across a decade. |
| F28 | Brian would like ABA coverage. | Defer pending a scope decision. | Historical archive goal, available data, and value relative to current NBA work? |
| F29 | Brian suggests eventual FIBA expansion and believes its digital product market is underserved. | Keep as a separate discovery idea. Market claim is unverified. | Which competitions and audience? Is expansion part of this product's direction? |
| F30 | Abhi suggests natural-language questions about scores, partly to demonstrate AI/software skills, 01:41–02:00 and 02:18–02:38. | Defer pending product purpose and example queries. | Is the goal a useful fan workflow, a portfolio demonstration, or both? |
| F31 | Andy recommends design critique and animation resources, 11:26–14:26; describes his own StatSide expansion afterward. | Preserve as reference material. | No installation or NBA Scorez multi-sport work follows automatically from this advice. |

## Positive feedback to retain

- Brian values progressive playoff reveal and the option to toggle it.
- Andy sees value in Design One's basketball identity and color, even while preferring more restrained proportions.
- Andy reacts positively on discovering the boxscore at 08:44–08:55 and says the playoff layout generally feels good at 10:00.
- Andy likes the ability to type historical dates at 05:17.
- Abhi calls the app a good foundation and recognizes the existing team logos and year typeahead.

## Existing Beads context

Read-only review of open issues found possible overlaps, not confirmed duplicates:

- `nba-scores-ptb`: historical playoff stages and format-specific layouts, relevant to F27. The working tree already contains historical-playoff changes; check current progress before creating a duplicate.
- `nba-scores-90g`: individual Finals reveal controls in historical desktop brackets, potentially relevant when scoping F14.
- `nba-scores-999`: date-aware historical team logos. It concerns era selection, not permission, so it does not resolve F26.
- `nba-scores-6z5`: older production API failure. It does not establish the cause of Alex's adblocker report in F04.

No issue statuses or descriptions were changed during this review.

## Turning decisions into tickets

After a review batch, record the owner's chosen disposition and rationale beside each relevant feedback ID. Create one Beads issue per independently deliverable outcome, linking all supporting IDs and timestamped evidence. Each issue should state the chosen behavior, scope, meaningful acceptance criteria, and priority. Investigation issues should state the question and evidence needed to answer it.

First proposed batch: F01/F03 for offseason navigation, F06/F09/F10 for calendar use, and F04 for reliability investigation. Favorite-team behavior, spoiler defaults, and visual identity need their own explicit scope decisions. All remain pending owner review.
