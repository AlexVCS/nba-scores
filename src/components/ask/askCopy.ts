// User-facing copy for Ask. Keep the three data flows distinct: local recent history (this browser),
// third-party provider processing (the interpreter), and server diagnostics (#201 owns retention details).
export const ASK_PLACEHOLDER = "Ask about a game, stat, or series";

export const ASK_SOURCE_COPY = "AI interprets your question. Answers use NBA data.";

export const ASK_NO_MODEL_COPY = "Answered directly from basketball data. No AI was needed for this one.";

export const ASK_RECENT_COPY = "Recent searches are saved only in this browser, never with answers.";

export const ASK_PROVIDER_COPY = "When you ask, your question is sent to our server and to an AI provider that reads it.";

export const ASK_DIAGNOSTICS_COPY = "Our server may keep limited diagnostics, such as the question type, to fix problems.";

export const ASK_DIAGNOSTICS_NOTE = "We kept an anonymous note of the question type, not your words, to decide what to support next.";

export const ASK_SCOPE_COPY =
  "Ask about games, boxscores, playoffs, player season and career stats, regular-season records and standings, season leaders, or all-time totals. Include the year or a season such as 2023-24. Career highs, franchise leaders, and statistical splits are not supported yet.";

// Asking is consent (ADR 0006): say so before the first question, so people avoiding spoilers aren't surprised.
export const ASK_ANSWERS_SHOWN_COPY = "Answers show as soon as you ask, even when results are hidden.";

// Shown before anything is asked, including while results are hidden, so none may name a playoff team or matchup: the mockup's
// "Did the Pistons beat the Magic in the 2026 first round?" would reveal that both teams qualified and met.
export const ASK_EXAMPLES = [
  {label: "Stats", question: "How many points did James Harden score on March 9, 2026?"},
  {label: "Games", question: "Knicks games from February 2 to February 8, 2026"},
  {label: "Series", question: "Who won the 2024 NBA Finals?"},
  {label: "Season", question: "Nikola Jokic rebounds per game in 2023-24"},
  {label: "Record", question: "Celtics regular-season record in 2007-08"},
  {label: "Leaders", question: "Who led the NBA in assists per game in 2019-20?"},
  {label: "Career", question: "LeBron James career points"},
] as const;
