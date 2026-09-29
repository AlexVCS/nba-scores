import {useState} from "react";
import {render, screen, within} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {beforeEach, describe, expect, it, vi} from "vitest";
import {ASK_RESPONSE_FIXTURES} from "@/services/ask/fixtures";
import type {AskResponse} from "@/services/ask/types";
import AskResult from "./AskResult";
import AskFooter from "./AskFooter";
import {AskTestProviders, perceivableText} from "./askTestUtils";
import type {AskRevealControls} from "./askStyles";

const IGNORED_KEYS = new Set(["kind", "stat", "round", "conference", "category", "field", "origin", "status", "external", "season_type", "id", "resolution", "player_id", "team_id", "game_id", "href", "series_href"]);

/** Every value the contract marks as protected, as text a user could perceive. */
function protectedValues(node: unknown, key = "", inside = false, found: string[] = [], exposed: string[] = []): string[] {
  if (Array.isArray(node)) {
    node.forEach(child => protectedValues(child, key, inside, found));
  } else if (node && typeof node === "object") {
    const record = node as Record<string, unknown>;
    const isGuarded = "value" in record && "spoiler" in record && Object.keys(record).length === 2;
    const flagged = record.spoiler === true;
    if (isGuarded) {
      protectedValues(record.value, key, inside || flagged, found, exposed);
    } else {
      if ("spoilers" in record && "game" in record && !inside) {
        const spoilers = record.spoilers as {score: boolean; status_text: boolean};
        const game = record.game as {homeTeam: {score: number}; awayTeam: {score: number}; gameStatusText: string};
        if (spoilers.score) found.push(String(game.homeTeam.score), String(game.awayTeam.score));
        if (spoilers.status_text && /OT/.test(game.gameStatusText)) found.push(game.gameStatusText);
      }
      for (const [childKey, child] of Object.entries(record)) {
        if (childKey === "spoiler" || childKey === "spoilers" || ("spoilers" in record && childKey === "game")) continue;
        protectedValues(child, childKey, inside || flagged, found, exposed);
      }
    }
  } else if (!IGNORED_KEYS.has(key)) {
    const target = inside ? found : exposed;
    if (typeof node === "number" && node >= 10) target.push(String(node));
    if (typeof node === "string" && (node.length >= 3 || /^\d{2,}$/.test(node))) target.push(node);
  }
  return found;
}

/** Protected values that the response does not also send unprotected (e.g. a matchup the user named). */
function leakCandidates(response: AskResponse): string[] {
  const exposed: string[] = [];
  const found = protectedValues(response, "", false, [], exposed);
  return found.filter(value => !exposed.includes(value));
}

function containsValue(haystack: string, value: string): boolean {
  const escaped = value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  // Digits may sit right after a label ("Points21"), so numbers only need non-digit neighbours.
  const edge = /^\d+$/.test(value) ? "\\d" : "\\w-";
  return new RegExp(`(?<![${edge}])${escaped}(?![${edge}])`).test(haystack);
}

function Harness({response}: {response: AskResponse}) {
  const [revealed, setRevealed] = useState<string[]>([]);
  const controls: AskRevealControls = {
    showAllResults: false,
    isRevealed: group => revealed.includes(group),
    reveal: group => setRevealed(current => [...current, group]),
    hide: group => setRevealed(current => current.filter(item => item !== group)),
  };
  return (
    <AskResult
      response={response}
      controls={controls}
      onAsk={vi.fn()}
      onChooseOption={vi.fn()}
      onRetry={vi.fn()}
      onEditQuestion={vi.fn()}
    />
  );
}

function renderFixture(name: string) {
  return render(<AskTestProviders><Harness response={ASK_RESPONSE_FIXTURES[name]} /></AskTestProviders>);
}

describe("AskResult spoiler protection", () => {
  beforeEach(() => localStorage.clear());

  it.each(Object.keys(ASK_RESPONSE_FIXTURES))("keeps protected values out of the DOM and accessibility text: %s", name => {
    const {container} = renderFixture(name);
    const text = perceivableText(container);
    const leaks = leakCandidates(ASK_RESPONSE_FIXTURES[name]).filter(value => containsValue(text, value));
    expect(leaks).toEqual([]);
  });

  it("reveals a single stat without the final score, which has its own reveal", async () => {
    const user = userEvent.setup();
    const {container} = renderFixture("answer-player-stat");

    await user.click(screen.getByRole("button", {name: "Reveal points"}));
    expect(containsValue(perceivableText(container), "21")).toBe(true);
    expect(containsValue(perceivableText(container), "104")).toBe(false);
    expect(containsValue(perceivableText(container), "112")).toBe(false);

    await user.click(screen.getByRole("button", {name: "Reveal score"}));
    expect(containsValue(perceivableText(container), "104")).toBe(true);
    expect(containsValue(perceivableText(container), "112")).toBe(true);
  });

  it("shows percentage display instead of made-attempted", async () => {
    const user = userEvent.setup();
    const response = structuredClone(ASK_RESPONSE_FIXTURES["answer-player-stat"]);
    if (response.result?.kind !== "boxscore_stat" || !response.result.player_line) throw new Error("Expected player stat");
    response.result.player_line.values[0].value = {stat: "field_goal_percentage", value: 0.5, display: "50.0%", made: 5, attempted: 10};
    response.result.stat = "field_goal_percentage";
    render(<AskTestProviders><Harness response={response} /></AskTestProviders>);
    await user.click(screen.getByRole("button", {name: "Reveal fg%"}));
    expect(screen.getByText("50.0%")).toBeInTheDocument();
    expect(screen.queryByText("5-10")).not.toBeInTheDocument();
  });

  it("offers a local reveal for protected clarification options without listing them first", async () => {
    const user = userEvent.setup();
    const response = structuredClone(ASK_RESPONSE_FIXTURES["clarification-which-jalen"]);
    if (!response.clarification) throw new Error("Expected clarification");
    response.clarification.options[0].spoiler = true;
    render(<AskTestProviders><Harness response={response} /></AskTestProviders>);
    expect(screen.queryByText("Jalen Duren")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", {name: "Show all options"}));
    expect(screen.getByRole("button", {name: /Jalen Duren/})).toBeInTheDocument();
  });

  it("uses the same hidden score controls for a completed and an unfinished game", () => {
    const final = structuredClone(ASK_RESPONSE_FIXTURES["answer-player-stat"]);
    const pending = structuredClone(final);
    if (pending.result?.kind !== "boxscore_stat") throw new Error("Expected boxscore stat");
    pending.result.game.final_score.value = null;
    const first = render(<AskTestProviders><Harness response={final} /></AskTestProviders>);
    expect(screen.getByRole("button", {name: "Reveal score"})).toBeInTheDocument();
    const finalText = perceivableText(first.container);
    first.unmount();
    render(<AskTestProviders><Harness response={pending} /></AskTestProviders>);
    expect(screen.getByRole("button", {name: "Reveal score"})).toBeInTheDocument();
    expect(perceivableText(document.body)).toBe(finalText);
  });

  it("omits protected interpretation chips in a gated response", () => {
    const response = structuredClone(ASK_RESPONSE_FIXTURES["answer-conditional-game-hidden"]);
    if (!response.interpretation) throw new Error("Expected interpretation");
    response.interpretation.items.push({...response.interpretation.items[0], field: "game", value: "Spoiler matchup", spoiler: true});
    const {container} = render(<AskTestProviders><Harness response={response} /></AskTestProviders>);
    expect(perceivableText(container)).not.toContain("Spoiler matchup");
    expect(within(screen.getByRole("region", {name: "How Ask read your question"})).queryByText("Hidden")).not.toBeInTheDocument();
  });

  it("keeps source completion out of the hidden footer", () => {
    const response = ASK_RESPONSE_FIXTURES["answer-postseason-league-in-progress"];
    const {rerender} = render(<AskFooter mode="result" resultsHidden response={response} />);
    expect(screen.queryByText(/still in progress/)).not.toBeInTheDocument();
    rerender(<AskFooter mode="result" resultsHidden={false} response={response} />);
    expect(screen.getByText(/still in progress/)).toBeInTheDocument();
  });

  it("renders the same hidden gate for a played and an unplayed conditional game", async () => {
    const user = userEvent.setup();
    const played = renderFixture("answer-conditional-game-hidden");
    const hiddenPlayed = within(screen.getByRole("region", {name: "Hidden answer"})).getByText(/Whether this game was played/).textContent;
    expect(screen.queryByRole("heading", {name: "No games found"})).not.toBeInTheDocument();
    played.unmount();

    renderFixture("not-found-conditional-game-hidden");
    expect(within(screen.getByRole("region", {name: "Hidden answer"})).getByText(/Whether this game was played/).textContent).toBe(hiddenPlayed);
    await user.click(screen.getByRole("button", {name: "Reveal answer"}));
    expect(screen.queryByRole("region", {name: "Hidden answer"})).not.toBeInTheDocument();
  });

  it("omits conditional games and the guarded total until revealed", async () => {
    const user = userEvent.setup();
    const {container} = renderFixture("answer-games-conditional");
    const result = ASK_RESPONSE_FIXTURES["answer-games-conditional"].result;
    if (result?.kind !== "games") throw new Error("Expected games fixture");
    const visibleCount = result.days.flatMap(day => day.games).filter(game => !game.spoiler).length;
    expect(container.querySelectorAll("article")).toHaveLength(visibleCount);
    expect(perceivableText(container)).toContain(result.hidden_note);
    expect(perceivableText(container)).not.toContain(`${result.total_games.value} games`);

    await user.click(screen.getByRole("button", {name: "Reveal results"}));
    expect(container.querySelectorAll("article")).toHaveLength(result.total_games.value);
  });

  it("hides the entire tied leaders list, including ranks and its length", async () => {
    const user = userEvent.setup();
    const {container} = renderFixture("answer-stat-leaders-tied");
    expect(container.querySelector("ol")).not.toBeInTheDocument();
    expect(perceivableText(container)).not.toContain("Chet Holmgren");

    await user.click(screen.getByRole("button", {name: /Reveal blocks/}));
    expect(perceivableText(container)).toContain("Chet Holmgren");
  });

  it("omits inferred series participants, spoiler links, and spoiler suggestions until revealed", async () => {
    const user = userEvent.setup();
    const {container} = renderFixture("answer-series-inferred");

    expect(screen.queryByRole("link", {name: "Open series"})).not.toBeInTheDocument();
    expect(screen.getByRole("link", {name: /Open 2025 bracket/})).toHaveAttribute("href", "/design-1/playoffs?season=2024-25");
    expect(perceivableText(container)).not.toMatch(/Shai|OKC|Thunder/);

    await user.click(screen.getByRole("button", {name: "Reveal answer"}));
    expect(screen.getByRole("link", {name: "Open series"})).toHaveAttribute("href", "/design-1/playoffs/2025/the-finals");
    expect(perceivableText(container)).toMatch(/Oklahoma City Thunder/);
  });

  it("echoes the teams the user named in a hidden series answer", () => {
    renderFixture("answer-series-hidden");
    expect(screen.getAllByText("Detroit Pistons").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Orlando Magic").length).toBeGreaterThan(0);
  });

  it("renders game results with the shared card and one reveal for every score", async () => {
    const user = userEvent.setup();
    const {container} = renderFixture("answer-games-last-week");
    const cards = container.querySelectorAll("article");
    expect(cards).toHaveLength(4);
    expect(perceivableText(container)).not.toMatch(/Final\/OT/);

    await user.click(screen.getByRole("button", {name: "Reveal results"}));
    expect(perceivableText(container)).toMatch(/Final\/OT/);
    expect(within(cards[0] as HTMLElement).getByText("121")).toBeInTheDocument();
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
