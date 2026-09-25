import {render, screen} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {MemoryRouter} from "react-router";
import {describe, expect, it, vi} from "vitest";
import HardwoodLastMatchups from "./HardwoodLastMatchups";

const games = [{
  gameId: "0022500411", gameDate: "2025-12-23",
  awayTeam: {teamId: 1610612741, teamTricode: "CHI", score: 126},
  homeTeam: {teamId: 1610612737, teamTricode: "ATL", score: 123},
}];

describe("HardwoodLastMatchups", () => {
  it("hides scores until revealed and links to the box score", async () => {
    const onReveal = vi.fn();
    const {rerender} = render(<MemoryRouter><HardwoodLastMatchups games={games} isLoading={false} showScores={false} onReveal={onReveal} /></MemoryRouter>);
    expect(screen.queryByText("126")).toBeNull();
    expect(screen.getByRole("link", {name: /CHI at ATL/})).toHaveAttribute("href", "/design-1/games/0022500411/boxscore?date=2025-12-23");
    await userEvent.click(screen.getByRole("button", {name: "Show results"}));
    expect(onReveal).toHaveBeenCalled();
    rerender(<MemoryRouter><HardwoodLastMatchups games={games} isLoading={false} showScores onReveal={onReveal} /></MemoryRouter>);
    expect(screen.getByText("126")).toBeInTheDocument();
    expect(screen.queryByRole("button", {name: "Show results"})).toBeNull();
  });

  it("renders nothing without history", () => {
    const {container} = render(<MemoryRouter><HardwoodLastMatchups games={[]} isLoading={false} showScores onReveal={vi.fn()} /></MemoryRouter>);
    expect(container).toBeEmptyDOMElement();
  });
});
