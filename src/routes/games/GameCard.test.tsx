import {render, screen} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {MemoryRouter, Route, Routes, useLocation} from "react-router";
import {describe, expect, it, vi} from "vitest";
import type {GameData} from "@/helpers/helpers";
import HardwoodGameCard from "@/designs/design-1/components/HardwoodGameCard";
import GameCard from "./GameCard";

vi.mock("@/components/TeamLogos", () => ({default: () => null}));

const game: GameData = {
  gameId: "0042500401", gameCode: "", gameStatus: 3, gameStatusText: "Final",
  gameLabel: "", gameSubLabel: "", gameTimeUTC: "", ifNecessary: false,
  seriesGameNumber: "", seriesText: "", boxscoreAvailable: false,
  homeTeam: {teamId: 1, teamName: "Spurs", teamTricode: "SAS", score: 123},
  awayTeam: {teamId: 2, teamName: "Knicks", teamTricode: "NYK", score: 111},
};

function Destination() {
  const location = useLocation();
  return <output>{location.pathname}{location.search} from {location.state?.from}</output>;
}

describe.each(["design-1", "original"])("%s game links", (design) => {
  it.each([1, 3])("opens hidden status %s games without available stats", async (gameStatus) => {
    const user = userEvent.setup();
    const props = {game: {...game, gameStatus}, showScores: false, dateParam: "2026-06-03"};
    render(<MemoryRouter initialEntries={[`/${design}?date=2026-06-03`]}>
      <Routes>
        <Route path={`/${design}`} element={design === "design-1"
          ? <HardwoodGameCard {...props} index={0} /> : <GameCard {...props} />} />
        <Route path={`/${design}/games/:gameId/boxscore`} element={<Destination />} />
      </Routes>
    </MemoryRouter>);
    expect(screen.queryByText("123")).not.toBeInTheDocument();
    expect(screen.queryByText("111")).not.toBeInTheDocument();
    const link = screen.getByRole("link", {name: "View NYK at SAS game details"});
    const watch = screen.getByRole("link", {name: /Watch/});
    expect(watch).toHaveAttribute("target", "_blank");
    expect(watch).toHaveAttribute("href", expect.stringContaining("nba.com/game/"));
    expect(link.contains(watch)).toBe(false);
    await user.tab();
    expect(link).toHaveFocus();
    await user.keyboard("{Enter}");
    expect(screen.getByRole("status")).toHaveTextContent(
      `/${design}/games/0042500401/boxscore?date=2026-06-03 from /${design}?date=2026-06-03`,
    );
  });
});
