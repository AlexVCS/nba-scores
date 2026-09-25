import {cleanup, fireEvent, render, screen, within} from "@testing-library/react";
import {MemoryRouter} from "react-router-dom";
import {afterEach, describe, expect, it} from "vitest";
import type {PlayoffBracketModel, RenderSeries} from "@/utils/playoffBracketModel";
import BaaPlayoffBracket from "./BaaPlayoffBracket";

function makeModel(): PlayoffBracketModel {
  const teams = ["Washington Capitols", "Chicago Stags", "Cleveland Rebels", "New York Knicks", "Philadelphia Warriors", "St. Louis Bombers"]
    .map((name, index) => ({id: index + 1, name, tricode: ["WAS", "CHS", "CLR", "NYK", "PHW", "STB"][index]}));
  const series = (key: string, round: number, first: number, second: number): RenderSeries => ({
    seriesKey: key, round, roundName: round === 1 ? "Quarterfinals" : round === 2 ? "Semifinals" : "BAA Finals", bracketGroupId: key === "division" ? "division-winners" : "other-qualifiers",
    bracketGroupLabel: key === "division" ? "Division winners" : key === "finals" ? "BAA Finals" : "Other qualifiers", bracketGroupKind: "league", bracketOrder: first,
    targetWins: round === 1 ? 2 : 4, isFinals: round === 3,
    teams: [teams[first], teams[second]], wins: {[teams[first].id]: 2, [teams[second].id]: 4},
    winnerTeamId: teams[second].id, winnerTeamTricode: teams[second].tricode, gameCount: 6, games: [],
  });
  return {
    season: "1946-47", format: {era: "baa-runners-up-bracket", playoffYear: 1947, finalsRound: 3, bracketType: "single-elimination", supportsExactBracket: false, notes: []},
    groups: [], rounds: [], edges: [], fallbackMode: false,
    series: [series("division", 2, 0, 1), series("qf-1", 1, 2, 3), series("qf-2", 1, 4, 5), series("qualifier", 2, 3, 4), series("finals", 3, 1, 4)],
  };
}

function renderBracket(forceShowAll = false) {
  return render(<MemoryRouter><BaaPlayoffBracket model={makeModel()} forceShowAll={forceShowAll} /></MemoryRouter>);
}

afterEach(cleanup);

describe("BaaPlayoffBracket", () => {
  it("shows all initial teams with full names while later matchups have no spoiler links", () => {
    renderBracket();
    expect(screen.getAllByRole("link")).toHaveLength(3);
    expect(screen.getByText("Washington Capitols")).toBeInTheDocument();
    expect(screen.getByText("St. Louis Bombers")).toBeInTheDocument();
    expect(screen.getByAltText("Chicago Stags logo")).toHaveAttribute("src", "/images/historical-team-logos/chs-chicago-stags-1946-1950.gif");
    expect(screen.getByAltText("Philadelphia Warriors logo")).toHaveAttribute("src", "/images/historical-team-logos/phw-philadelphia-warriors-1946-1962.gif");
    expect(screen.queryByRole("link", {name: /Capitols 2/})).not.toBeInTheDocument();
    for (const name of ["Other qualifiers", "BAA Finals"]) {
      expect(within(screen.getByRole("region", {name})).queryByRole("link")).not.toBeInTheDocument();
    }
  });

  it("reveals the two paths independently and removes downstream participant links on hide", () => {
    renderBracket();
    fireEvent.click(screen.getByRole("button", {name: "Reveal Division winners results"}));
    expect(screen.getByRole("link", {name: "Washington Capitols 2, Chicago Stags 4. View series details."})).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", {name: "Reveal Quarterfinals, series 1 results"}));
    expect(within(screen.getByRole("region", {name: "Other qualifiers"})).queryByRole("link")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", {name: "Reveal Quarterfinals, series 2 results"}));
    expect(within(screen.getByRole("region", {name: "Other qualifiers"})).getByRole("link")).toHaveAccessibleName("New York Knicks versus Philadelphia Warriors. View series details.");
    fireEvent.click(screen.getByRole("button", {name: "Reveal Other qualifiers results"}));
    expect(within(screen.getByRole("region", {name: "BAA Finals"})).getByRole("link")).toHaveAccessibleName("Chicago Stags versus Philadelphia Warriors. View series details.");
    fireEvent.click(screen.getByRole("button", {name: "Hide Quarterfinals, series 1 results"}));
    expect(within(screen.getByRole("region", {name: "BAA Finals"})).queryByRole("link")).not.toBeInTheDocument();
    expect(screen.getByRole("button", {name: "Hide Division winners results"})).toBeInTheDocument();
  });

  it("honors global show results without redundant reveal controls", () => {
    renderBracket(true);
    expect(screen.getAllByRole("link")).toHaveLength(5);
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(within(screen.getByRole("region", {name: "BAA Finals"})).getByRole("link")).toHaveAccessibleName("Chicago Stags 2, Philadelphia Warriors 4. View series details.");
  });
});
