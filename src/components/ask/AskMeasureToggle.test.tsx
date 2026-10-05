import {render, screen, within} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {describe, expect, it, vi} from "vitest";
import {ASK_RESPONSE_FIXTURES} from "@/services/ask/fixtures";
import type {AskCareerStatsResult, AskPlayerSeasonStatsResult, AskResponse, AskSeasonLeadersResult} from "@/services/ask/types";
import AskResult from "./AskResult";
import {AskTestProviders} from "./askTestUtils";

function show(response: AskResponse) {
  return render(<AskTestProviders><AskResult
    response={response} resultsHidden
    onAsk={vi.fn()} onChooseOption={vi.fn()} onRetry={vi.fn()} onEditQuestion={vi.fn()}
  /></AskTestProviders>);
}

function edit<T>(name: string, update: (result: T) => T): AskResponse {
  const base = ASK_RESPONSE_FIXTURES[name];
  return {...base, result: update(structuredClone(base.result) as T) as AskResponse["result"]};
}

describe("Ask measure toggle", () => {
  it("shows a stat line per game first and switches to totals from the same answer", async () => {
    const user = userEvent.setup();
    show(ASK_RESPONSE_FIXTURES["answer-player-season-line"]);
    const region = screen.getByRole("region", {name: "Kevin Durant season statistics"});
    const group = within(region).getByRole("group", {name: "Show Kevin Durant 2015-16 statistics per game or as totals"});
    const perGame = within(group).getByRole("button", {name: "Per game"});
    const totals = within(group).getByRole("button", {name: "Totals"});
    expect(perGame).toHaveAttribute("aria-pressed", "true");
    expect(totals).toHaveAttribute("aria-pressed", "false");
    expect(within(region).getByText("28.2")).toBeInTheDocument();
    expect(within(region).getByText("9.7/19.2")).toBeInTheDocument();
    expect(within(region).getByText(/Per game · 72 games played/)).toBeInTheDocument();

    await user.click(totals);
    expect(totals).toHaveAttribute("aria-pressed", "true");
    expect(perGame).toHaveAttribute("aria-pressed", "false");
    expect(within(region).getByText("2029")).toBeInTheDocument();
    expect(within(region).getByText("698/1381")).toBeInTheDocument();
    expect(within(region).queryByText("28.2")).not.toBeInTheDocument();
    expect(within(region).getByText(/Season totals · 72 games played/)).toBeInTheDocument();

    await user.click(perGame);
    expect(within(region).getByText("28.2")).toBeInTheDocument();
  });

  it("keeps the requested measure first when the question stated one", () => {
    show(ASK_RESPONSE_FIXTURES["answer-player-season"]);
    const region = screen.getByRole("region", {name: "Nikola Jokic season statistics"});
    expect(within(region).getByRole("button", {name: "Per game"})).toHaveAttribute("aria-pressed", "true");
    expect(within(region).getByText("12.4")).toBeInTheDocument();
  });

  it("shows no toggle when both measures would be identical", () => {
    show(edit<AskPlayerSeasonStatsResult>("answer-player-season", result => ({
      ...result, aggregation: "total", alternate: null,
      values: [{stat: "field_goal_percentage", value: 0.583, display: "58.3%", made: null, attempted: null}],
    })));
    const region = screen.getByRole("region", {name: "Nikola Jokic season statistics"});
    expect(within(region).queryByRole("group")).not.toBeInTheDocument();
    expect(within(region).getByText(/Season shooting percentage/)).toBeInTheDocument();
  });

  it("switches a career line between totals and per game", async () => {
    const user = userEvent.setup();
    show(edit<AskCareerStatsResult>("answer-career-totals", result => ({
      ...result, aggregation: "total",
      values: result.alternate!.values, alternate: {aggregation: "per_game", values: result.values},
    })));
    const region = screen.getByRole("region", {name: "LeBron James career statistics"});
    expect(within(region).getByRole("button", {name: "Totals"})).toHaveAttribute("aria-pressed", "true");
    expect(within(region).getByText("43440")).toBeInTheDocument();
    expect(within(region).getByText(/Career totals · 1622 games played/)).toBeInTheDocument();
    await user.click(within(region).getByRole("button", {name: "Per game"}));
    expect(within(region).getByText("26.8")).toBeInTheDocument();
    expect(within(region).getByText(/Career per game · 1622 games played/)).toBeInTheDocument();
  });

  it("shows a full career line per game first and switches to totals from the keyboard", async () => {
    const user = userEvent.setup();
    const line = (points: number, rebounds: number, display: (n: number) => string) => [
      {stat: "points" as const, value: points, display: display(points), made: null, attempted: null},
      {stat: "rebounds" as const, value: rebounds, display: display(rebounds), made: null, attempted: null},
    ];
    show(edit<AskCareerStatsResult>("answer-career-totals", result => ({
      ...result, stat: "stat_line", aggregation: "per_game",
      values: line(26.8, 7.4, n => n.toFixed(1)),
      alternate: {aggregation: "total", values: line(43440, 12000, n => String(n))},
    })));
    const region = screen.getByRole("region", {name: "LeBron James career statistics"});
    const group = within(region).getByRole("group", {name: "Show LeBron James career statistics per game or as totals"});
    const perGame = within(group).getByRole("button", {name: "Per game"});
    const totals = within(group).getByRole("button", {name: "Totals"});
    expect(perGame).toHaveAttribute("aria-pressed", "true");
    expect(within(region).getByText("26.8")).toBeInTheDocument();
    expect(within(region).getByText("7.4")).toBeInTheDocument();
    expect(within(region).getByText(/Career per game · 1622 games played/)).toBeInTheDocument();

    totals.focus();
    await user.keyboard("{Enter}");
    expect(totals).toHaveAttribute("aria-pressed", "true");
    expect(within(region).getByText("43440")).toBeInTheDocument();
    expect(within(region).getByText("12000")).toBeInTheDocument();
    expect(within(region).queryByText("26.8")).not.toBeInTheDocument();
    expect(within(region).getByText(/Career totals · 1622 games played/)).toBeInTheDocument();

    await user.keyboard("{Shift>}{Tab}{/Shift} ");
    expect(perGame).toHaveAttribute("aria-pressed", "true");
    expect(within(region).getByText("26.8")).toBeInTheDocument();
  });

  it("says when a leaderboard shows the top 25 instead of a larger request", () => {
    show(edit<AskSeasonLeadersResult>("answer-season-leaders", result => ({
      ...result, limit_note: "Showing the top 25, the most Ask lists.",
    })));
    expect(screen.getByText("Showing the top 25, the most Ask lists.")).toBeInTheDocument();
  });
});
