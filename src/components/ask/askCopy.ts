// User-facing copy for Ask. Keep the three data flows distinct: local recent history (this browser),
// third-party provider processing (the interpreter), and server diagnostics (#201 owns retention details).
export const ASK_PLACEHOLDER = "Ask about a game, stat, or series";

export const ASK_SOURCE_COPY = "AI interprets your question. Answers use NBA data.";

export const ASK_NO_MODEL_COPY = "Answered straight from NBA data. No AI was needed for this one.";

export const ASK_RECENT_COPY = "Recent searches are saved only in this browser, never with answers.";

export const ASK_PROVIDER_COPY = "When you ask, your question is sent to our server and to an AI provider that reads it.";

export const ASK_DIAGNOSTICS_COPY = "Our server may keep limited diagnostics, such as the question type, to fix problems.";

export const ASK_DIAGNOSTICS_NOTE = "We kept an anonymous note of the question type, not your words, to decide what to support next.";

export const ASK_SCOPE_COPY =
  "Ask about games on a date or within a week, one player’s stats in one game, or a playoff series. Include the year. Career totals and all-time comparisons aren’t supported.";

export const ASK_HIDDEN_COPY = "Results stay hidden until you reveal them";

// Always shown, including while results are hidden, so none may name a playoff team or matchup: the mockup's
// "Did the Pistons beat the Magic in the 2026 first round?" would reveal that both teams qualified and met.
export const ASK_EXAMPLES = [
  {label: "Stats", question: "How many points did James Harden score on March 9, 2026?"},
  {label: "Games", question: "Knicks games from February 2 to February 8, 2026"},
  {label: "Series", question: "Who won the 2024 NBA Finals?"},
] as const;
