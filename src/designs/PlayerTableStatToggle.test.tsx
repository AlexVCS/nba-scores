import {render, screen} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type {ComponentType} from "react";
import {describe, expect, it} from "vitest";
import type {DesignBoxscoreTeam} from "./hooks/useBoxscorePage";
import HardwoodPlayerTable from "./design-4/components/HardwoodPlayerTable";
import DesignPlayerTable from "./shared/DesignPlayerTable";

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
  ],
};

interface PlayerTableCase {
  name: string;
  Component: ComponentType<{team: DesignBoxscoreTeam}>;
}

const playerTables: PlayerTableCase[] = [{name: "shared design table", Component: DesignPlayerTable}];

describe.each(playerTables)("$name", ({Component}) => {
  it("defaults to all stats and can switch to compact columns", async () => {
    const user = userEvent.setup();
    render(<Component team={team} />);

    const allStatsButton = screen.getByRole("button", {name: "All stats"});
    const compactButton = screen.getByRole("button", {name: "Compact"});

    expect(allStatsButton).toHaveAttribute("aria-pressed", "true");
    expect(compactButton).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByRole("columnheader", {name: "OREB"})).toBeInTheDocument();
    expect(screen.getByRole("columnheader", {name: "FG%"})).toBeInTheDocument();

    await user.click(compactButton);

    expect(compactButton).toHaveAttribute("aria-pressed", "true");
    expect(allStatsButton).toHaveAttribute("aria-pressed", "false");
    expect(screen.queryByRole("columnheader", {name: "OREB"})).not.toBeInTheDocument();
    expect(screen.queryByRole("columnheader", {name: "FG%"})).not.toBeInTheDocument();
    expect(screen.getByRole("columnheader", {name: "PTS"})).toBeInTheDocument();
    expect(screen.getByRole("columnheader", {name: "MIN"})).toBeInTheDocument();
  });
});

describe("hardwood table", () => {
  it("shows all stats without column controls", () => {
    render(<HardwoodPlayerTable team={team} />);

    expect(screen.queryByRole("button", {name: "All stats"})).not.toBeInTheDocument();
    expect(screen.queryByRole("button", {name: "Compact"})).not.toBeInTheDocument();
    expect(screen.getByRole("columnheader", {name: "OREB"})).toBeInTheDocument();
    expect(screen.getByRole("columnheader", {name: "FG%"})).toBeInTheDocument();
    expect(screen.getByRole("columnheader", {name: "PTS"})).toBeInTheDocument();
    expect(screen.getByRole("columnheader", {name: "MIN"})).toBeInTheDocument();
  });
});
