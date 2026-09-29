import {describe, expect, it} from "vitest";
import {ASK_ANSWERS_SHOWN_COPY, ASK_EXAMPLES} from "./askCopy";

const TEAM_NAMES = [
  "Hawks", "Celtics", "Nets", "Hornets", "Bulls", "Cavaliers", "Mavericks", "Nuggets", "Pistons", "Warriors",
  "Rockets", "Pacers", "Clippers", "Lakers", "Grizzlies", "Heat", "Bucks", "Timberwolves", "Pelicans", "Knicks",
  "Thunder", "Magic", "76ers", "Suns", "Trail Blazers", "Kings", "Spurs", "Raptors", "Jazz", "Wizards",
];

describe("Ask copy", () => {
  // Examples show before anything is asked, including while results are hidden, so they are not answers:
  // one that pairs a team with the playoffs would reveal that the team qualified.
  it("never pairs a team with a playoff round in an example question", () => {
    for (const {question} of ASK_EXAMPLES) {
      const namesTeam = TEAM_NAMES.some(name => new RegExp(`\\b${name}\\b`, "i").test(question));
      const namesPostseason = /\b(playoffs?|postseason|finals?|first round|semifinals?|series|game [5-7])\b/i.test(question);
      expect(namesTeam && namesPostseason, question).toBe(false);
    }
  });

  it("tells people that answers show as soon as they ask", () => {
    expect(ASK_ANSWERS_SHOWN_COPY).toMatch(/as soon as you ask/);
  });
});
