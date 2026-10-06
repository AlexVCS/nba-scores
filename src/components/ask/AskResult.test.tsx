import {render, screen, within} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {beforeEach, describe, expect, it, vi} from "vitest";
import {ASK_RESPONSE_FIXTURES} from "@/services/ask/fixtures";
import type {AskResponse} from "@/services/ask/types";
import AskResult from "./AskResult";
import AskFooter from "./AskFooter";
import {AskTestProviders, perceivableText} from "./askTestUtils";

function renderResponse(response: AskResponse, {resultsHidden = true}: {resultsHidden?: boolean} = {}) {
  return render(
    <AskTestProviders>
      <AskResult
        response={response}
        resultsHidden={resultsHidden}
        onAsk={vi.fn()}
        onChooseOption={vi.fn()}
        onRetry={vi.fn()}
        onEditQuestion={vi.fn()}
      />
    </AskTestProviders>,
  );
}

function renderFixture(name: string, options?: {resultsHidden?: boolean}) {
  return renderResponse(ASK_RESPONSE_FIXTURES[name], options);
}

function containsValue(haystack: string, value: string): boolean {
  const escaped = value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  // Digits may sit right after a label ("Points21"), so numbers only need non-digit neighbours.
  const edge = /^\d+$/.test(value) ? "\\d" : "\\w-";
  return new RegExp(`(?<![${edge}])${escaped}(?![${edge}])`).test(haystack);
}

describe("AskResult: asking is consent (ADR 0006)", () => {
  beforeEach(() => localStorage.clear());

  it.each(Object.keys(ASK_RESPONSE_FIXTURES))("has no reveal or hide controls: %s", name => {
    const {container} = renderFixture(name);
    expect(screen.queryByRole("button", {name: /^(Reveal|Hide) /})).not.toBeInTheDocument();
    expect(screen.queryByRole("region", {name: "Hidden answer"})).not.toBeInTheDocument();
    expect(perceivableText(container)).not.toMatch(/\bHidden\b/);
  });

  it("shows a requested stat and its final score immediately while results are hidden", () => {
    const {container} = renderFixture("answer-player-stat");
    const text = perceivableText(container);
    expect(containsValue(text, "21")).toBe(true);
    expect(containsValue(text, "104")).toBe(true);
    expect(containsValue(text, "112")).toBe(true);
  });

  it("shows percentage display instead of made-attempted", () => {
    const response = structuredClone(ASK_RESPONSE_FIXTURES["answer-player-stat"]);
    if (response.result?.kind !== "boxscore_stat" || !response.result.player_line) throw new Error("Expected player stat");
    response.result.player_line.values[0] = {stat: "field_goal_percentage", value: 0.5, display: "50.0%", made: 5, attempted: 10};
    response.result.stat = "field_goal_percentage";
    renderResponse(response);
    expect(screen.getByText("50.0%")).toBeInTheDocument();
    expect(screen.queryByText("5-10")).not.toBeInTheDocument();
  });

  it("says a game is not final yet instead of showing a score", () => {
    const response = structuredClone(ASK_RESPONSE_FIXTURES["answer-player-stat"]);
    if (response.result?.kind !== "boxscore_stat") throw new Error("Expected boxscore stat");
    response.result.game.final_score = null;
    renderResponse(response);
    expect(screen.getByText("Not final yet")).toBeInTheDocument();
  });

  it("shows every game, conditional ones included, with scores and overtime", () => {
    const {container} = renderFixture("answer-games-conditional");
    const result = ASK_RESPONSE_FIXTURES["answer-games-conditional"].result;
    if (result?.kind !== "games") throw new Error("Expected games fixture");
    const total = result.days.flatMap(day => day.games).length;
    expect(container.querySelectorAll("article")).toHaveLength(total);
    expect(perceivableText(container)).toContain(`${total} games`);

    const lastWeek = renderFixture("answer-games-last-week");
    const cards = lastWeek.container.querySelectorAll("article");
    expect(cards).toHaveLength(4);
    expect(perceivableText(lastWeek.container)).toMatch(/Final\/OT/);
    expect(within(cards[0] as HTMLElement).getByText("121")).toBeInTheDocument();
  });

  it("shows a tied leaders list with its shared ranks", () => {
    const {container} = renderFixture("answer-stat-leaders-tied");
    expect(container.querySelector("ol")).toBeInTheDocument();
    expect(perceivableText(container)).toContain("Chet Holmgren");
  });

  it("answers a conditional game directly, whether or not it was played", () => {
    renderFixture("answer-conditional-game");
    expect(screen.getByRole("region", {name: "How Ask read your question"})).toBeInTheDocument();
    expect(screen.queryByText(/Whether this game was played/)).not.toBeInTheDocument();
  });

  it("shows inferred series participants in the answer and its interpretation", () => {
    const {container} = renderFixture("answer-series-inferred");
    expect(perceivableText(container)).toMatch(/Oklahoma City Thunder/);
    const chips = within(screen.getByRole("region", {name: "How Ask read your question"}));
    expect(chips.getByText("OKC vs IND")).toBeInTheDocument();
  });

  it("shows the source's in-progress note with an answer", () => {
    render(<AskFooter mode="result" response={ASK_RESPONSE_FIXTURES["answer-postseason-league-in-progress"]} />);
    expect(screen.getByText(/still in progress/)).toBeInTheDocument();
  });

  it("shows the detected type as a badge, not a control, with a way to edit the question", () => {
    renderFixture("answer-games-last-week");
    const region = screen.getByRole("region", {name: "How Ask read your question"});
    expect(within(region).getByText("Games")).not.toHaveAttribute("role");
    expect(within(region).queryByRole("checkbox")).not.toBeInTheDocument();
    expect(within(region).getByRole("button", {name: /Edit your question/})).toBeInTheDocument();
  });

  it.each([
    ["unsupported-career-stats", "Can't answer that one yet", false],
    ["not-found-historical-record", "No boxscore for that game", false],
    ["unavailable-service", "NBA data isn't responding", true],
    ["budget-exhausted", "Ask is paused for today", false],
  ] as const)("renders the %s notice", (name, title, retryable) => {
    renderFixture(name);
    expect(screen.getByRole("heading", {name: title})).toBeInTheDocument();
    expect(Boolean(screen.queryByRole("button", {name: /Try again/}))).toBe(retryable);
  });

  it("has no thumbs feedback controls", () => {
    const {container} = renderFixture("answer-player-stat");
    expect(perceivableText(container)).not.toMatch(/thumb|helpful|feedback/i);
  });
});

describe("AskResult: the global preference still governs what wasn't asked for", () => {
  beforeEach(() => localStorage.clear());

  const SPOILER_SUGGESTION = "How many points did Shai Gilgeous-Alexander score in game 7 of the 2025 NBA Finals?";

  function withSpoilerLink(name: string): AskResponse {
    const response = structuredClone(ASK_RESPONSE_FIXTURES[name]);
    response.links = [
      ...response.links,
      {kind: "boxscore", label: "Next game recap", href: "/games/0042400407/boxscore?date=2025-06-22", external: false, spoiler: true},
    ];
    return response;
  }

  it("leaves spoiler suggestions and follow-up links out of the DOM while results are hidden", () => {
    const {container} = renderResponse(withSpoilerLink("answer-series-inferred"));
    const text = perceivableText(container);
    expect(text).not.toContain(SPOILER_SUGGESTION);
    expect(text).not.toContain("Next game recap");
    expect(screen.getByRole("link", {name: /Open 2025 bracket/})).toHaveAttribute("href", "/playoffs?season=2024-25");
  });

  it("shows spoiler suggestions and follow-up links when the preference shows results", () => {
    renderResponse(withSpoilerLink("answer-series-inferred"), {resultsHidden: false});
    expect(screen.getByRole("button", {name: SPOILER_SUGGESTION})).toBeInTheDocument();
    expect(screen.getByRole("link", {name: "Next game recap"})).toBeInTheDocument();
  });

  it("drops a result-revealing suggestion from a notice while results are hidden", () => {
    const {container, unmount} = renderFixture("unsupported-career-stats");
    expect(perceivableText(container)).not.toContain("Did the Pistons beat the Magic");
    unmount();
    renderFixture("unsupported-career-stats", {resultsHidden: false});
    expect(screen.getByRole("button", {name: /Did the Pistons beat the Magic/})).toBeInTheDocument();
  });

  it("keeps spoiler clarification options out until the user asks to see them", async () => {
    const user = userEvent.setup();
    const response = structuredClone(ASK_RESPONSE_FIXTURES["clarification-which-jalen"]);
    if (!response.clarification) throw new Error("Expected clarification");
    response.clarification.options[0].spoiler = true;
    const {container} = renderResponse(response);
    expect(perceivableText(container)).not.toContain("Jalen Duren");
    await user.click(screen.getByRole("button", {name: "Show all options"}));
    expect(screen.getByRole("button", {name: /Jalen Duren/})).toBeInTheDocument();
  });

  it("lists spoiler clarification options when the preference shows results", () => {
    const response = structuredClone(ASK_RESPONSE_FIXTURES["clarification-which-jalen"]);
    if (!response.clarification) throw new Error("Expected clarification");
    response.clarification.options[0].spoiler = true;
    renderResponse(response, {resultsHidden: false});
    expect(screen.getByRole("button", {name: /Jalen Duren/})).toBeInTheDocument();
    expect(screen.queryByRole("button", {name: "Show all options"})).not.toBeInTheDocument();
  });

  it("omits the option reveal control when every option is already safe", () => {
    renderFixture("clarification-which-jalen");
    expect(screen.queryByRole("button", {name: "Show all options"})).not.toBeInTheDocument();
  });

  it("omits an inferred participant chip beside a clarification while results are hidden", () => {
    const response = structuredClone(ASK_RESPONSE_FIXTURES["clarification-which-jalen"]);
    if (!response.interpretation) throw new Error("Expected interpretation");
    response.interpretation.items.push({...response.interpretation.items[0], field: "game", value: "Spoiler matchup", origin: "inferred", spoiler: true});
    const {container, unmount} = renderResponse(response);
    expect(perceivableText(container)).not.toContain("Spoiler matchup");
    unmount();
    renderResponse(response, {resultsHidden: false});
    expect(screen.getByText("Spoiler matchup")).toBeInTheDocument();
  });
});
