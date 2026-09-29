import {describe, expect, it} from "vitest";
import {ASK_SUGGEST_FIXTURES} from "@/services/ask/fixtures";
import type {AskSuggestResponse} from "@/services/ask/types";
import {buildTypeaheadGroups, isQuestionShaped} from "./askTypeahead";

const knicks = ASK_SUGGEST_FIXTURES["knicks-hidden"];
const now = new Date("2026-09-29T12:00:00-04:00");

const withPlayoffs: AskSuggestResponse = {
  ...knicks,
  games: [
    {...knicks.games[0], game_id: "0042500101", label: "NYK vs ATL · Game 1", href: "/games/0042500101/boxscore"},
    ...knicks.games,
  ],
  questions: [...knicks.questions, {question: "How did the Knicks do in the 2026 playoffs?", category: "postseason", spoiler: true}],
};

describe("buildTypeaheadGroups", () => {
  it("puts direct game matches first for short entity queries", () => {
    const groups = buildTypeaheadGroups({query: "knicks", suggest: knicks, resultsHidden: true, now});
    expect(groups.map(group => group.id)).toEqual(["games", "ask"]);
    expect(groups[0].actions[0]).toMatchObject({kind: "game", label: "NYK @ BOS", href: "/games/0022500801/boxscore?date=2026-02-08"});
    expect(groups[1].actions[0]).toMatchObject({kind: "ask", question: "knicks"});
  });

  it("puts the typed question first for question-shaped text", () => {
    const groups = buildTypeaheadGroups({query: "did the knicks win last night?", suggest: knicks, resultsHidden: true, now});
    expect(groups[0].id).toBe("ask");
  });

  it("drops postseason games and spoiler questions while results are hidden", () => {
    const hidden = buildTypeaheadGroups({query: "knicks", suggest: withPlayoffs, resultsHidden: true, now});
    const labels = hidden.flatMap(group => group.actions.map(action => action.label));
    expect(labels.join(" ")).not.toMatch(/ATL|playoffs/);

    const shown = buildTypeaheadGroups({query: "knicks", suggest: withPlayoffs, resultsHidden: false, now});
    expect(shown.flatMap(group => group.actions.map(action => action.label)).join(" ")).toMatch(/NYK @ BOS.*playoffs/);
  });

  it("offers only a generic bracket link for playoff keywords, never a team series", () => {
    const groups = buildTypeaheadGroups({query: "knicks playoffs", suggest: undefined, resultsHidden: true, now});
    const playoffs = groups.find(group => group.id === "playoffs");
    expect(playoffs?.actions).toEqual([expect.objectContaining({kind: "bracket", label: "2025-26 playoff bracket", href: "/playoffs?season=2025-26"})]);
  });

  it("classifies question-shaped input", () => {
    expect(isQuestionShaped("knicks")).toBe(false);
    expect(isQuestionShaped("knicks celtics")).toBe(false);
    expect(isQuestionShaped("how did the knicks do")).toBe(true);
    expect(isQuestionShaped("knicks games last week")).toBe(true);
  });
});
