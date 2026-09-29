import {render, screen, within} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {afterEach, describe, expect, it, vi} from "vitest";
import type {StatEvents} from "@/helpers/statEventUrl";
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
    matches: query === "(min-width: 768px)",
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }));

const statEvents: StatEvents = {
  season: "2025-26",
  seasonType: "Regular Season",
  endRange: 28800,
  measures: {FGM: 3, FGA: 3, FG3M: 3, FG3A: 3, OREB: 1, DREB: 1, REB: 1, AST: 1, STL: 1, BLK: 1, TOV: 1},
};

const playerUrl = (measure: string, flag: number) =>
  `https://www.nba.com/stats/events/?CFID=&CFPARAMS=&ContextMeasure=${measure}&EndPeriod=0&EndRange=28800&GameID=0022500868&PlayerID=2&RangeType=0&Season=2025-26&SeasonType=Regular%20Season&StartPeriod=0&StartRange=0&TeamID=1&flag=${flag}&sct=plot&section=game`;

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
    expect(screen.getAllByRole("listitem")[0]).toHaveTextContent("5-10");

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

  it("opens the full ledger with every column and no facet chips at widths from 768px", async () => {
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
    expect(totals).not.toHaveTextContent("240");
    for (const value of ["44-88", "12-36", "17-20", "47", "29", "9", "4", "+13", "117"]) {
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
    expect(totals).toHaveTextContent("Totals11756");
    expect(totals.querySelectorAll("small")).toHaveLength(0);

    await user.click(screen.getByRole("button", {name: "Shooting"}));
    expect(totals).toHaveTextContent("Totals5-102-43-4117");
    expect(totals.querySelectorAll("small")).toHaveLength(0);
  });

  it("sums the players on the floor when the payload carries no team statistics", () => {
    stubWideViewport();
    render(<HardwoodScorersBook team={team} />);

    const totals = screen.getByLabelText("Cleveland Cavaliers totals");
    expect(totals).not.toHaveTextContent("30");
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

  describe("NBA.com stat event links", () => {
    const playerRow = () => screen.getAllByRole("listitem")[0];

    it("links each positive listed stat in the wide row, splitting made and attempted", () => {
      stubWideViewport();
      render(<HardwoodScorersBook team={team} gameId="0022500868" statEvents={statEvents} />);

      const made = screen.getByRole("link", {name: "View Test Player's field goals made on NBA.com, opens in new tab"});
      expect(made).toHaveAttribute("href", playerUrl("FGM", 3));
      expect(made).toHaveTextContent(/^5$/);
      expect(made).toHaveAttribute("target", "_blank");
      expect(made).toHaveAttribute("rel", "noopener noreferrer");
      const attempted = screen.getByRole("link", {name: "View Test Player's field goals attempted on NBA.com, opens in new tab"});
      expect(attempted).toHaveTextContent(/^10$/);
      expect(attempted.parentElement).toHaveTextContent("5-10");
      expect(screen.getByRole("link", {name: /Test Player's turnovers/})).toHaveAttribute("href", playerUrl("TOV", 1));
      for (const name of ["three-pointers made", "three-pointers attempted", "rebounds", "assists", "steals", "blocks"]) {
        expect(within(playerRow()).getByRole("link", {name: new RegExp(`Test Player's ${name} on`)})).toBeInTheDocument();
      }
      // Free throws, points, minutes and plus/minus are never linked.
      expect(within(playerRow()).getAllByRole("link")).toHaveLength(9);
      expect(screen.queryByRole("link", {name: /Bench Guy/})).not.toBeInTheDocument();
    });

    it("keeps zero values and measures missing from statEvents as plain text", () => {
      stubWideViewport();
      const partial: StatEvents = {...statEvents, measures: {FGM: 2, FGA: 2, FG3M: 2, FG3A: 2}};
      const noThrees: DesignBoxscoreTeam = {
        ...team,
        players: [{...team.players[0], statistics: {...team.players[0].statistics, threePointersMade: 0}}, team.players[1]],
      };
      render(<HardwoodScorersBook team={noThrees} gameId="0022500868" statEvents={partial} />);

      const links = within(playerRow()).getAllByRole("link").map((link) => link.getAttribute("aria-label"));
      expect(links).toEqual([
        "View Test Player's field goals made on NBA.com, opens in new tab",
        "View Test Player's field goals attempted on NBA.com, opens in new tab",
        "View Test Player's three-pointers attempted on NBA.com, opens in new tab",
      ]);
      expect(playerRow()).toHaveTextContent("0-4");
    });

    it("renders no links when the game has no statEvents", () => {
      stubWideViewport();
      render(<HardwoodScorersBook team={team} gameId="0022500868" statEvents={null} />);

      expect(screen.queryByRole("link", {name: /on NBA.com/})).not.toBeInTheDocument();
      expect(playerRow()).toHaveTextContent("5-10");
    });

    it("links team totals without a PlayerID", () => {
      stubWideViewport();
      render(<HardwoodScorersBook team={team} gameId="0022500868" statEvents={statEvents} />);

      const totals = screen.getByLabelText("Cleveland Cavaliers totals");
      const made = within(totals).getByRole("link", {name: "View Cleveland Cavaliers' field goals made on NBA.com, opens in new tab"});
      expect(made).toHaveAttribute("href", playerUrl("FGM", 3).replace("PlayerID=2&", ""));
      expect(within(totals).getAllByRole("link")).toHaveLength(9);
      for (const link of within(totals).getAllByRole("link")) expect(link.getAttribute("href")).not.toContain("PlayerID");
    });

    it("links the expanded sheet's shooting splits and counters, including rebound splits", async () => {
      const user = userEvent.setup();
      render(<HardwoodScorersBook team={team} gameId="0022500868" statEvents={statEvents} />);

      await user.click(screen.getByRole("button", {name: /Test Player/}));
      const sheet = document.getElementById("hw-sheet-2")!;
      const labels = within(sheet).getAllByRole("link", {name: /on NBA.com/}).map((link) => link.getAttribute("aria-label"));
      for (const name of ["field goals made", "field goals attempted", "three-pointers made", "three-pointers attempted", "offensive rebounds", "defensive rebounds", "steals", "blocks", "turnovers"]) {
        expect(labels).toContain(`View Test Player's ${name} on NBA.com, opens in new tab`);
      }
      expect(within(sheet).getByRole("link", {name: /offensive rebounds/})).toHaveAttribute("href", playerUrl("OREB", 1));
      expect(within(sheet).getByRole("link", {name: /defensive rebounds/})).toHaveAttribute("href", playerUrl("DREB", 1));
      // The line facet already shows assists in the row, so the sheet does not repeat them.
      expect(labels).not.toContain("View Test Player's assists on NBA.com, opens in new tab");
      expect(sheet).toHaveTextContent("3-4");
    });

    it.each([
      ["mobile", false, false],
      ["desktop", true, false],
      ["comparison", false, true],
    ])("toggles the row independently of stat links in the %s layout", async (_layout, isWide, comparison) => {
      if (isWide) stubWideViewport();
      const user = userEvent.setup();
      render(<HardwoodScorersBook team={team} gameId="0022500868" statEvents={statEvents} comparison={comparison} />);

      const row = screen.getByRole("button", {name: /Test Player/});
      const link = within(playerRow()).getByRole("link", {name: /Test Player's assists/});
      expect(row).not.toContainElement(link);
      await user.click(link);
      expect(row).toHaveAttribute("aria-expanded", "false");

      await user.click(row);
      expect(row).toHaveAttribute("aria-expanded", "true");
      await user.click(within(playerRow()).getByRole("link", {name: /Test Player's assists/}));
      expect(row).toHaveAttribute("aria-expanded", "true");
      await user.click(row);
      expect(row).toHaveAttribute("aria-expanded", "false");
    });
  });
});
