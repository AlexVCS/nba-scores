import {describe, expect, it} from "vitest";
import {getBaaBracketTopology} from "@/utils/baaBracketTopology";
import type {PlayoffBracketModel, RenderSeries} from "@/utils/playoffBracketModel";

function makeModel(playoffYear = 1947): PlayoffBracketModel {
  const series = (seriesKey: string, bracketGroupId: string, round: number, bracketOrder = 0): RenderSeries => ({
    seriesKey, bracketGroupId, round, bracketOrder,
    bracketGroupLabel: bracketGroupId,
    bracketGroupKind: bracketGroupId === "finals" ? "finals" : "league",
    roundName: `Round ${round}`,
    isFinals: bracketGroupId === "finals",
    targetWins: 2,
    teams: [], wins: {}, games: [], gameCount: 0,
    winnerTeamId: null, winnerTeamTricode: null,
  });
  return {
    season: playoffYear === 1947 ? "1946-47" : "1947-48",
    format: {era: "baa-runners-up-bracket", playoffYear, finalsRound: 3, bracketType: "hybrid", supportsExactBracket: false, notes: []},
    groups: [], rounds: [], edges: [], fallbackMode: false,
    series: [series("q2", "other-qualifiers", 1, 1), series("division", "division-winners", 2), series("finals", "finals", 3), series("semi", "other-qualifiers", 2), series("q1", "other-qualifiers", 1)],
  };
}

describe("getBaaBracketTopology", () => {
  it.each([1947, 1948])("connects the independent paths in %i even when API edges and results are absent", year => {
    const topology = getBaaBracketTopology(makeModel(year));
    expect(topology?.quarterfinals.map(series => series.seriesKey)).toEqual(["q1", "q2"]);
    expect(topology?.edges).toEqual([
      {sourceSeriesKey: "q1", targetSeriesKey: "semi", winnerTeamId: null},
      {sourceSeriesKey: "q2", targetSeriesKey: "semi", winnerTeamId: null},
      {sourceSeriesKey: "division", targetSeriesKey: "finals", winnerTeamId: null},
      {sourceSeriesKey: "semi", targetSeriesKey: "finals", winnerTeamId: null},
    ]);
  });

  it("never chooses connections from winning teams", () => {
    const model = makeModel();
    const before = getBaaBracketTopology(model)?.edges;
    model.series = model.series.map(series => ({...series, winnerTeamId: 123, wins: {"123": 4}}));
    model.edges = [{sourceSeriesKey: "division", targetSeriesKey: "semi", winnerTeamId: 123}];
    expect(getBaaBracketTopology(model)?.edges).toEqual(before);
  });

  it("leaves other formats and incomplete or ambiguous records to the existing renderer", () => {
    const otherEra = makeModel();
    otherEra.format.era = "unknown";
    const incomplete = makeModel();
    incomplete.series.pop();
    const duplicate = makeModel();
    duplicate.series[0] = duplicate.series[1];
    const unexpectedRound = makeModel();
    unexpectedRound.series[0].round = 2;
    for (const model of [otherEra, makeModel(1949), incomplete, duplicate, unexpectedRound]) {
      expect(getBaaBracketTopology(model)).toBeNull();
    }
  });
});
