import {render, screen, within} from "@testing-library/react";
import {describe, expect, it, vi} from "vitest";
import {ASK_RESPONSE_FIXTURES} from "@/services/ask/fixtures";
import type {AskResponse, AskSeasonLeadersResult} from "@/services/ask/types";
import AskResult from "./AskResult";
import {AskTestProviders} from "./askTestUtils";

function show(response: AskResponse) {
  return render(<AskTestProviders><AskResult
    response={response} resultsHidden
    onAsk={vi.fn()} onChooseOption={vi.fn()} onRetry={vi.fn()} onEditQuestion={vi.fn()}
  /></AskTestProviders>);
}

const base = ASK_RESPONSE_FIXTURES["answer-season-leaders"];

function withResult(update: (result: AskSeasonLeadersResult) => AskSeasonLeadersResult): AskResponse {
  const result = structuredClone(base.result) as AskSeasonLeadersResult;
  return {...base, result: update(result)};
}

describe("Ask season leaders", () => {
  it("shows the leaderboard immediately, with season context, qualification and source", () => {
    show(base);
    const region = screen.getByRole("region", {name: "2023-24 Points per game leaders"});
    expect(within(region).getByText(/2023-24 · Regular season · Top 10/)).toBeInTheDocument();
    const table = within(region).getByRole("table", {name: /2023-24 regular season points per game leaders, top 10/});
    expect(within(table).getAllByRole("rowheader")).toHaveLength(10);
    expect(within(table).getAllByRole("columnheader").map(el => el.textContent)).toEqual(["Rank", "Player", "Team", "GP", "Per game"]);
    const leader = within(table).getByRole("rowheader", {name: "Luka Dončić"}).closest("tr")!;
    expect(leader).toHaveAttribute("data-leader", "true");
    expect(within(leader).getByText("33.9")).toBeInTheDocument();
    expect(within(leader).getByText("Rank 1")).toBeInTheDocument();
    expect(within(region).getByText(/Qualified players only/)).toBeInTheDocument();
    expect(within(region).getByText(/Data as of/)).toBeInTheDocument();
    expect(screen.getByRole("link", {name: /Source: NBA.com/})).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("explains equal-looking values that rank apart", () => {
    show(base);
    expect(screen.getByText(/Ranks use unrounded values/)).toBeInTheDocument();
    expect(screen.queryByText(/T marks players tied/)).not.toBeInTheDocument();
  });

  it("marks shared ranks, several teams and an omitted tie group", () => {
    show(withResult(result => {
      const rows = result.rows.slice(0, 3);
      rows[2] = {...rows[2], rank: 2, team: null, multiple_teams: true, value: {...rows[1].value}};
      return {...result, rows, omitted_tie: {rank: 4, count: 60}};
    }));
    const table = screen.getByRole("table");
    expect(within(table).getAllByText("Tied for rank 2")).toHaveLength(2);
    expect(within(table).getAllByText("T2")).toHaveLength(2);
    expect(within(table).getByText("Multiple teams")).toBeInTheDocument();
    expect(screen.getByText("60 more players tied at rank 4 are not shown.")).toBeInTheDocument();
    expect(screen.getByText(/T marks players tied/)).toBeInTheDocument();
  });

  it("labels totals, percentages and playoffs", () => {
    const {unmount} = show(withResult(result => ({...result, aggregation: "total", season_type: "playoffs"})));
    expect(screen.getByRole("heading", {name: "Total points leaders"})).toBeInTheDocument();
    expect(screen.getByText(/2023-24 · Playoffs · Top 10/)).toBeInTheDocument();
    unmount();
    show(withResult(result => ({...result, stat: "field_goal_percentage", aggregation: "total"})));
    expect(screen.getByRole("heading", {name: "FG% leaders"})).toBeInTheDocument();
    expect(screen.getAllByRole("columnheader").at(-1)).toHaveTextContent("FG%");
  });
});
