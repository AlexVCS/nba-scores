import {render, screen, within} from "@testing-library/react";
import {describe, expect, it, vi} from "vitest";
import {ASK_RESPONSE_FIXTURES} from "@/services/ask/fixtures";
import AskResult from "./AskResult";
import {AskTestProviders} from "./askTestUtils";

function show(name: string) {
  return render(<AskTestProviders><AskResult
    response={ASK_RESPONSE_FIXTURES[name]} resultsHidden
    onAsk={vi.fn()} onChooseOption={vi.fn()} onRetry={vi.fn()} onEditQuestion={vi.fn()}
  /></AskTestProviders>);
}

describe("Ask season answers", () => {
  it("shows a season average with games played and season context while results are hidden", () => {
    show("answer-player-season");
    const region = screen.getByRole("region", {name: "Nikola Jokic season statistics"});
    expect(within(region).getByText("12.4")).toBeInTheDocument();
    expect(within(region).getByText(/79 games played/)).toBeInTheDocument();
    expect(within(region).getByText(/2023-24 · Regular season/)).toBeInTheDocument();
    expect(within(region).getByText(/Per game/)).toBeInTheDocument();
    expect(screen.getByRole("link", {name: /Source: NBA.com/})).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("shows a single team's season record without unrelated standings", () => {
    show("answer-team-record");
    const region = screen.getByRole("region", {name: "Boston Celtics season record"});
    expect(within(region).getByText("64")).toBeInTheDocument();
    expect(within(region).getByText("18")).toBeInTheDocument();
    expect(within(region).getByText("78.0%")).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(within(region).getByText(/Data as of/)).toBeInTheDocument();
  });

  it("uses an accessible standings table with team row headings", () => {
    show("answer-standings");
    const table = screen.getByRole("table", {name: "2023-24 Eastern conference regular-season wins and losses"});
    expect(within(table).getAllByRole("row")).toHaveLength(16);
    expect(within(table).getAllByRole("rowheader")).toHaveLength(15);
    expect(within(table).getAllByRole("columnheader").map(el => el.textContent)).toEqual(["Team", "W", "L", "Win %"]);
  });
});
