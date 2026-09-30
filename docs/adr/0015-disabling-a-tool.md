# 15. Disabling a tool

Date: 2026-09-30
Status: proposed (the user decides)

## Context

ADR 0009 says what happens when a model tier fails its gate: the tier is
disabled and skipped, and the system gate is re-measured without it. It does
not say what happens when one tool fails, or breaks in production. For
example, stats.nba could change `LeagueLeaders`, or the unseen run could show
guesses only in `career_stats`.

What exists in code today:

- One switch for all of Ask: `ASK_ENABLED` (`server/ask/config.py`), read once
  at startup in `server/ask/router.py`. When it is off, every question gets
  `service_unavailable` ("NBA data isn't responding"). The Design 1 entry has a
  separate build-time flag, `VITE_ASK_ENABLED`.
- A tier is skipped when its settings are missing: no `TYPESAFE_API_KEY` means
  no Jev, and no `LAYA_BASE_URL` (or no `ASK_DEV=1`) means no Laya
  (`server/ask/interpreters/factory.py`).
- No per-tool switch. The only documented way to drop a tool is to leave it out
  of `TOOLS` (`server/ask/tools.py` docstring; ADR 0010: a failing family
  "stays `unsupported` in the router").

Leaving a tool out of `TOOLS` changes the router's closed set. That changes the
prompts, the OpenAI instructions hash, the Jev options and the parse-cache
keys. The frozen evaluation no longer describes the running system, so every
number would need a new provider run.

## Options

1. **Remove the tool from `TOOLS`.** Simple and already documented. But it
   changes the router, so the interpretation results are no longer comparable.
   Questions for the removed family may also be routed to a similar tool (a
   career question read as a season question), which can produce a wrong
   answer.
2. **Keep the router unchanged; refuse after routing.** Interpreters still see
   all eight tools. Python checks the settled intent against a disabled set and
   returns `unsupported` with a specific reason. This is the same pattern as
   ADR 0014, where Python overrides a model read after interpretation.
3. **Turn off all of Ask.** Already possible with `ASK_ENABLED=0`. Too broad
   for one broken family, but it stays the emergency switch.

## Decision (recommended)

Option 2, with option 3 kept as the whole-feature switch.

1. **Flag.** A new server variable `ASK_DISABLED_TOOLS`, a comma-separated list
   of tool names (for example `season_leaders,career_stats`). `AskConfig`
   parses it like the other `ASK_*` settings. An unknown name fails at startup,
   as an unknown model price does. It is read at startup, so a change needs a
   restart or redeploy, the same as `ASK_ENABLED`. Empty by default.
2. **Router unchanged.** `TOOLS`, router descriptions and closed sets do not
   change. Prompts and parse-cache keys stay identical, so interpretation
   evidence stays comparable.
3. **Where the check runs.** Once the intent is settled, before any
   clarification for that tool's fields, before the answer cache, and before
   any resolver. A backstop check at the top of `AskPipeline._execute` covers
   all three paths into it (exact date, pending clarification, interpreted
   question). A cached answer from before the switch is never served.
4. **Response.** Outcome `unsupported`, with a new reason `tool_disabled`. It
   joins the Python-only reasons (like `LEGACY_UNSUPPORTED_REASONS`), so it is
   never offered to interpreters and the closed sets do not change. The message
   names the family, for example "Season leaders are turned off for now. Ask
   still covers games, boxscores, playoffs, player season stats and standings."
   The general unsupported copy in `server/ask/present.py` must not list a
   disabled family. The frontend type `AskUnsupportedReason` gets the new value.
5. **Intent clarification.** A disabled tool is removed from "Which kind of
   question?" options. If no option remains, the answer is `tool_disabled`.
6. **Logs.** The `ask cascade` INFO line records `tool_disabled` and the tool
   name, with no question text.

## Re-measuring the system gate

- Interpretation is unchanged, so the frozen run's preserved traces still
  apply. The gate is re-scored offline from them, with no new provider calls,
  the same way `scripts/ask/tier_gate.py` scores tiers from traces.
- For the re-score, the disabled family's cases expect `unsupported`
  (`tool_disabled`). Any of them that renders an answer counts as a guess.
- Report two results: the ADR 0009 gate over the enabled families, and the
  disabled family's refusals. The 90% figures use the enabled families only.
  Zero guesses covers every case.
- Removing a family is not a fix. Re-enabling it needs a new frozen commit and
  a fresh unseen run, as for any change.

## Consequences

- One broken source or family can be turned off without touching the others
  or the evaluation evidence.
- Users get a clear "turned off" message, not "NBA data isn't responding".
- Questions for a disabled tool still pay for interpretation. That cost is
  small (about $0.0003 per question on recorded runs).
- `server/ask/tools.py`'s docstring and ADR 0010's consequence ("stays
  `unsupported` in the router") would be amended to point here.
- Not built yet. This ADR records the proposal only.
