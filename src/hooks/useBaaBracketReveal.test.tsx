import {act, renderHook} from "@testing-library/react";
import {describe, expect, it} from "vitest";
import type {PlayoffBracketModel, RenderSeries} from "@/utils/playoffBracketModel";
import useBaaBracketReveal from "./useBaaBracketReveal";

function makeSeries(seriesKey: string, round: number): RenderSeries {
  return {
    seriesKey, round, roundName: round === 3 ? "Finals" : round === 2 ? "Semifinals" : "Quarterfinals",
    bracketGroupId: seriesKey === "division-winners" ? "division-winners" : "other-qualifiers",
    bracketGroupLabel: seriesKey === "division-winners" ? "Division winners" : "Other qualifiers",
    bracketGroupKind: "league", bracketOrder: 0, targetWins: 2, isFinals: round === 3,
    teams: [], wins: {}, winnerTeamId: null, winnerTeamTricode: null, gameCount: 0, games: [],
  };
}

function makeModel(season = "1946-47"): PlayoffBracketModel {
  return {
    season,
    format: {era: "baa-runners-up-bracket", playoffYear: 1947, finalsRound: 3, bracketType: "single-elimination", supportsExactBracket: true, notes: []},
    groups: [], rounds: [], fallbackMode: false,
    series: [makeSeries("division-winners", 2), makeSeries("qf-a", 1), makeSeries("qf-b", 1), makeSeries("qualifier-sf", 2), makeSeries("finals", 3)],
    edges: [],
  };
}

describe("useBaaBracketReveal", () => {
  it("allows division winners immediately and requires both quarterfinals for the other semifinal", () => {
    const {result} = renderHook(() => useBaaBracketReveal(makeModel()));
    expect(result.current.canRevealSeries("division-winners")).toBe(true);
    expect(result.current.canRevealSeries("qualifier-sf")).toBe(false);
    act(() => result.current.revealSeries("finals"));
    expect(result.current.revealedSeries.size).toBe(0);
    act(() => result.current.revealSeries("division-winners"));
    expect([...result.current.revealedSeries]).toEqual(["division-winners"]);
    expect(result.current.canRevealSeries("finals")).toBe(false);
    act(() => result.current.revealSeries("qf-a"));
    expect(result.current.canRevealSeries("qualifier-sf")).toBe(false);
    act(() => result.current.revealSeries("qf-b"));
    expect(result.current.canRevealSeries("qualifier-sf")).toBe(true);
    act(() => result.current.revealSeries("qualifier-sf"));
    expect(result.current.canRevealSeries("finals")).toBe(true);
  });

  it("hides descendants while preserving the independent path and sibling quarterfinal", () => {
    const {result} = renderHook(() => useBaaBracketReveal(makeModel()));
    act(() => result.current.showAllResults());
    act(() => result.current.hideSeries("qf-a"));
    expect([...result.current.revealedSeries]).toEqual(["division-winners", "qf-b"]);
    expect(result.current.canRevealSeries("qualifier-sf")).toBe(false);
    expect(result.current.canRevealSeries("finals")).toBe(false);
    act(() => result.current.showAllResults());
    act(() => result.current.hideSeries("division-winners"));
    expect([...result.current.revealedSeries]).toEqual(["qf-a", "qf-b", "qualifier-sf"]);
    act(() => result.current.hideAllResults());
    expect(result.current.revealedSeries.size).toBe(0);
  });

  it("clears reveals when seasons change, including when returning to the first season", () => {
    const {result, rerender} = renderHook(({season}) => useBaaBracketReveal(makeModel(season)), {initialProps: {season: "1946-47"}});
    act(() => result.current.showAllResults());
    rerender({season: "1947-48"});
    expect(result.current.revealedSeries.size).toBe(0);
    rerender({season: "1946-47"});
    expect(result.current.revealedSeries.size).toBe(0);
  });

  it("shows all under global override and hides results again when the override ends", () => {
    const {result, rerender} = renderHook(({forceShowAll}) => useBaaBracketReveal(makeModel(), {forceShowAll}), {initialProps: {forceShowAll: false}});
    act(() => result.current.revealSeries("qf-a"));
    rerender({forceShowAll: true});
    expect(result.current.revealedSeries.size).toBe(5);
    expect(result.current.canRevealSeries("finals")).toBe(true);
    act(() => result.current.hideAllResults());
    act(() => result.current.hideSeries("division-winners"));
    expect(result.current.revealedSeries.size).toBe(5);
    rerender({forceShowAll: false});
    expect(result.current.revealedSeries.size).toBe(0);
  });

  it("keeps dependent participants locked when the response has an unsupported topology", () => {
    const model = makeModel();
    model.series = model.series.filter(series => series.seriesKey !== "qf-b");
    const {result} = renderHook(() => useBaaBracketReveal(model));
    expect(result.current.canRevealSeries("qualifier-sf")).toBe(false);
    act(() => result.current.revealSeries("qualifier-sf"));
    expect(result.current.revealedSeries.size).toBe(0);
  });

  it("ignores unknown keys", () => {
    const {result} = renderHook(() => useBaaBracketReveal(makeModel()));
    expect(result.current.canRevealSeries("missing")).toBe(false);
    act(() => result.current.revealSeries("missing"));
    act(() => result.current.hideSeries("missing"));
    expect(result.current.revealedSeries.size).toBe(0);
  });
});
