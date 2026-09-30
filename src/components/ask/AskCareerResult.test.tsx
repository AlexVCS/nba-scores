import {render, screen, within} from "@testing-library/react";
import {describe, expect, it, vi} from "vitest";
import {ASK_RESPONSE_FIXTURES} from "@/services/ask/fixtures";
import type {AskCareerStatsResult, AskResponse} from "@/services/ask/types";
import AskResult from "./AskResult";
import {AskTestProviders} from "./askTestUtils";

function show(response: AskResponse) {
  return render(<AskTestProviders><AskResult
    response={response} resultsHidden
    onAsk={vi.fn()} onChooseOption={vi.fn()} onRetry={vi.fn()} onEditQuestion={vi.fn()}
  /></AskTestProviders>);
}

function edit(name: string, update: (result: AskCareerStatsResult) => AskCareerStatsResult): AskResponse {
  const base = ASK_RESPONSE_FIXTURES[name];
  return {...base, result: update(structuredClone(base.result) as AskCareerStatsResult)};
}

describe("Ask career answers", () => {
  it("shows a player's career average with games played while results are hidden", () => {
    show(ASK_RESPONSE_FIXTURES["answer-career-totals"]);
    const region = screen.getByRole("region", {name: "LeBron James career statistics"});
    expect(within(region).getByText("26.8")).toBeInTheDocument();
    expect(within(region).getByText(/Career · Regular season/)).toBeInTheDocument();
    expect(within(region).getByText(/Career per game · 1622 games played/)).toBeInTheDocument();
    expect(screen.getByRole("link", {name: /Source: NBA.com/})).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("lists all-time leaders in an accessible table with active players marked", () => {
    show(ASK_RESPONSE_FIXTURES["answer-career-leaders"]);
    const table = screen.getByRole("table", {name: /Regular season all-time assists leaders, top 10/});
    expect(within(table).getAllByRole("rowheader")).toHaveLength(10);
    expect(within(table).getAllByRole("columnheader").map(el => el.textContent)).toEqual(["Rank", "Player", "Total"]);
    const leader = within(table).getAllByRole("row")[1];
    expect(leader).toHaveAttribute("data-leader", "true");
    expect(within(leader).getByText("Rank 1")).toBeInTheDocument();
    expect(screen.getByText(/All-time totals from NBA.com/)).toBeInTheDocument();
  });

  it("shows a player's all-time rank, a shared rank, and a rank outside the list", () => {
    const {unmount} = show(ASK_RESPONSE_FIXTURES["answer-career-rank"]);
    const region = screen.getByRole("region", {name: /Stephen Curry · all-time 3-pointers/});
    expect(within(region).getByText("1st")).toBeInTheDocument();
    expect(within(region).getByText("4,248")).toBeInTheDocument();
    unmount();
    const tied = show(edit("answer-career-rank", result => ({...result, rank: 12, tied_count: 3})));
    expect(screen.getByText("T-12th")).toBeInTheDocument();
    expect(screen.getByText("3 players share this rank.")).toBeInTheDocument();
    tied.unmount();
    show(edit("answer-career-rank", result => ({...result, rank: null, tied_count: null, values: []})));
    expect(screen.getByText("Not in NBA.com's top 250 for career 3-pointers.")).toBeInTheDocument();
  });
});
