import {render, screen} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {afterEach, describe, expect, it, vi} from "vitest";
import type {DesignBoxscoreTeam} from "../../hooks/useBoxscorePage";
import HardwoodScorersBook from "./HardwoodScorersBook";

const emptyStatistics = {
  minutes: "",
  fieldGoalsMade: 0,
  fieldGoalsAttempted: 0,
  fieldGoalsPercentage: 0,
  threePointersMade: 0,
  threePointersAttempted: 0,
  threePointersPercentage: 0,
  freeThrowsMade: 0,
  freeThrowsAttempted: 0,
  freeThrowsPercentage: 0,
  reboundsOffensive: 0,
  reboundsDefensive: 0,
  reboundsTotal: 0,
  assists: 0,
  steals: 0,
  blocks: 0,
  turnovers: 0,
  foulsPersonal: 0,
  points: 0,
  plusMinusPoints: 0,
};

const team: DesignBoxscoreTeam = {
  teamId: 1,
  teamTricode: "CLE",
  teamCity: "Cleveland",
  teamName: "Cavaliers",
  score: 117,
  players: [
    {
      personId: 2,
      firstName: "Test",
      familyName: "Player",
      nameI: "T. Player",
      playerSlug: "test-player",
      position: "G",
      comment: "",
      jerseyNum: "1",
      statistics: {
        ...emptyStatistics,
        minutes: "PT30M00.00S",
        fieldGoalsMade: 5,
        fieldGoalsAttempted: 10,
        fieldGoalsPercentage: 0.5,
        threePointersMade: 2,
        threePointersAttempted: 4,
        threePointersPercentage: 0.5,
        freeThrowsMade: 3,
        freeThrowsAttempted: 4,
        freeThrowsPercentage: 0.75,
        reboundsOffensive: 1,
        reboundsDefensive: 4,
        reboundsTotal: 5,
        assists: 6,
        steals: 2,
        blocks: 1,
        turnovers: 3,
        foulsPersonal: 2,
        points: 15,
        plusMinusPoints: 8,
      },
    },
    {
      personId: 3,
      firstName: "Bench",
      familyName: "Guy",
      nameI: "B. Guy",
      playerSlug: "bench-guy",
      position: "",
      comment: "DNP - Coach's Decision",
      jerseyNum: "12",
      statistics: emptyStatistics,
    },
  ],
};

const stubWideViewport = () =>
  vi.stubGlobal("matchMedia", (query: string) => ({
    matches: query === "(min-width: 900px)",
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }));

describe("hardwood scorer's book", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("defaults to the line facet and swaps row stats per facet on narrow widths", async () => {
    const user = userEvent.setup();
    render(<HardwoodScorersBook team={team} />);

    expect(screen.getByRole("button", {name: "Line"})).toHaveAttribute("aria-pressed", "true");
    expect(screen.getAllByText("PTS")).not.toHaveLength(0);
    expect(screen.queryByText("FG")).not.toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", {name: "Shooting"}));
    expect(screen.getAllByText("FG")).not.toHaveLength(0);
    expect(screen.getByRole("button", {name: /Test Player/})).toHaveTextContent("5-10");

    await user.click(screen.getByRole("button", {name: "Hustle"}));
    expect(screen.getAllByText("+/-")).not.toHaveLength(0);
    expect(screen.getByText("+8")).toBeInTheDocument();
  });

  it("unfolds a player's full stat sheet on demand", async () => {
    const user = userEvent.setup();
    render(<HardwoodScorersBook team={team} />);

    const row = screen.getByRole("button", {name: /Test Player/});
    expect(row).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByText("Field goals")).not.toBeInTheDocument();

    await user.click(row);
    expect(row).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("Field goals")).toBeInTheDocument();
    expect(screen.getByText("Off boards")).toBeInTheDocument();
    // The line facet already shows points, so the sheet does not repeat them.
    expect(screen.queryByText("Points")).not.toBeInTheDocument();
    expect(screen.getByText("Steals")).toBeInTheDocument();
    expect(screen.getByRole("link", {name: /Full profile/})).toHaveAttribute("href", expect.stringContaining("nba.com/player/"));

    await user.click(row);
    expect(row).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByText("Field goals")).not.toBeInTheDocument();
  });

  it("opens the full ledger with every column and no facet chips on desktop widths", async () => {
    stubWideViewport();
    const user = userEvent.setup();
    render(<HardwoodScorersBook team={team} />);

    for (const label of ["MIN", "PTS", "REB", "AST", "FG", "3PT", "FT", "STL", "BLK", "TO", "+/-"]) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
    expect(screen.getByText("MORE")).toBeInTheDocument();
    expect(screen.queryByRole("button", {name: "Line"})).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", {name: /Test Player/}));
    const tiles = screen.getAllByRole("term").map((dt) => dt.textContent);
    expect(tiles).toEqual(["Field goals", "Three pointers", "Free throws", "Off boards", "Def boards", "Fouls"]);
  });

  it("folds players who did not play into the ledger rows", () => {
    render(<HardwoodScorersBook team={team} />);

    expect(screen.getAllByText("Bench Guy")).not.toHaveLength(0);
    expect(screen.getByText("DNP - Coach's Decision")).toBeInTheDocument();
    expect(screen.queryByRole("button", {name: /Bench Guy/})).not.toBeInTheDocument();
    expect(screen.getByTitle("Bench Guy")).toBeInTheDocument();
  });

  it("closes the ledger with the team's totals from the box score statistics", async () => {
    stubWideViewport();
    const user = userEvent.setup();
    const withTotals: DesignBoxscoreTeam = {
      ...team,
      statistics: {
        points: 117,
        minutes: "PT240M00.00S",
        fieldGoalsMade: 44,
        fieldGoalsAttempted: 88,
        threePointersMade: 12,
        threePointersAttempted: 36,
        freeThrowsMade: 17,
        freeThrowsAttempted: 20,
        reboundsTotal: 47,
        assists: 29,
        steals: 9,
        blocks: 4,
        turnovers: 13,
        plusMinusPoints: 13,
      },
    };
    render(<HardwoodScorersBook team={withTotals} />);

    const totals = screen.getByLabelText("Cleveland Cavaliers totals");
    expect(totals).toHaveTextContent("Totals");
    for (const value of ["240", "44-88", "12-36", "17-20", "47", "29", "9", "4", "+13", "117"]) {
      expect(totals).toHaveTextContent(value);
    }
    expect(totals).not.toHaveTextContent("—");
    // Every total sits on one line: no percentage sublabels beneath the shooting pairs.
    expect(totals.querySelectorAll("small")).toHaveLength(0);
    await user.click(screen.getByRole("button", {name: /Test Player/}));
    expect(screen.getByText("Field goals")).toBeInTheDocument();
  });

  it("keeps total values but removes their labels on narrow widths", async () => {
    const user = userEvent.setup();
    render(<HardwoodScorersBook team={team} />);

    const totals = screen.getByLabelText("Cleveland Cavaliers totals");
    expect(totals).toHaveTextContent("Totals3011756");
    expect(totals.querySelectorAll("small")).toHaveLength(0);

    await user.click(screen.getByRole("button", {name: "Shooting"}));
    expect(totals).toHaveTextContent("Totals5-102-43-4117");
    expect(totals.querySelectorAll("small")).toHaveLength(0);
  });

  it("sums the players on the floor when the payload carries no team statistics", () => {
    stubWideViewport();
    render(<HardwoodScorersBook team={team} />);

    const totals = screen.getByLabelText("Cleveland Cavaliers totals");
    expect(totals).toHaveTextContent("30");
    expect(totals).toHaveTextContent("5-10");
    expect(totals).toHaveTextContent("117");
  });

  it("uses the broad stat line in comparison mode regardless of viewport", () => {
    render(<HardwoodScorersBook team={team} comparison />);

    expect(screen.getByRole("heading", {level: 2, name: "Cleveland Cavaliers"})).toBeInTheDocument();
    expect(screen.getByText("CLE")).toBeInTheDocument();
    expect(screen.getByRole("region", {name: "Cleveland Cavaliers player statistics"})).toBeInTheDocument();
    for (const label of ["MIN", "FG", "3PT", "FT", "REB", "AST", "STL", "BLK", "TO", "+/-", "PTS"]) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
    expect(screen.queryByText("MORE")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", {name: "Line"})).not.toBeInTheDocument();
    expect(screen.getAllByRole("listitem")).toHaveLength(team.players.length);
  });

  it("uses the complete team name outside comparison mode", () => {
    render(<HardwoodScorersBook team={team} />);

    const heading = screen.getByRole("heading", {level: 2, name: "Cleveland Cavaliers"});
    expect(heading).toBeInTheDocument();
    expect(heading.parentElement).toHaveClass("max-[700px]:h-[60px]");
    expect(screen.getByText("CLE")).toBeInTheDocument();
  });
});
