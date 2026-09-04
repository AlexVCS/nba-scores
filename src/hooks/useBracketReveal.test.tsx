import {act, renderHook} from "@testing-library/react";
import {describe, expect, it} from "vitest";
import type {PlayoffBracketModel} from "@/utils/playoffBracketModel";
import {useBracketReveal} from "./useBracketReveal";

function makeModel(season = "2024-25"): PlayoffBracketModel {
  return {
    season,
    format: {
      era: "modern-play-in-era",
      playoffYear: 2025,
      finalsRound: 4,
      bracketType: "single-elimination",
      supportsExactBracket: true,
      notes: [],
    },
    groups: [],
    rounds: [
      {round: 10, label: "First Round", sortOrder: 1, defaultRevealed: false},
      {round: 30, label: "Conference Semifinals", sortOrder: 2, defaultRevealed: false},
      {round: 40, label: "NBA Finals", sortOrder: 3, defaultRevealed: false},
    ],
    edges: [],
    series: [],
    fallbackMode: false,
  };
}

describe("useBracketReveal", () => {
  it("requires sequential reveals and cascades a hide by round order", () => {
    const {result} = renderHook(() => useBracketReveal(makeModel()));

    expect(result.current.canRevealRound(10)).toBe(true);
    expect(result.current.canRevealRound(30)).toBe(false);

    act(() => result.current.revealRound(30));
    expect(result.current.revealedRounds.size).toBe(0);

    act(() => result.current.revealRound(10));
    act(() => result.current.revealRound(30));
    act(() => result.current.revealRound(40));
    expect([...result.current.revealedRounds]).toEqual([10, 30, 40]);

    act(() => result.current.hideRound(30));
    expect([...result.current.revealedRounds]).toEqual([10]);
    expect(result.current.statusMessage).toBe("Conference Semifinals and all later results are hidden.");
  });

  it("clears spoilers when the season changes", () => {
    const {result, rerender} = renderHook(
      ({model}: {model: PlayoffBracketModel}) => useBracketReveal(model),
      {initialProps: {model: makeModel()}},
    );

    act(() => result.current.revealRound(10));
    expect(result.current.revealedRounds.has(10)).toBe(true);

    rerender({model: makeModel("1987-88")});
    expect(result.current.revealedRounds.size).toBe(0);
    expect(result.current.statusMessage).toBe("Results are hidden until you choose to reveal them.");
  });

  it("hides every result at once", () => {
    const {result} = renderHook(() => useBracketReveal(makeModel()));
    act(() => result.current.revealRound(10));
    act(() => result.current.hideAllResults());

    expect(result.current.revealedRounds.size).toBe(0);
    expect(result.current.statusMessage).toBe("All playoff results are hidden.");
  });

  it("reveals the selected round and every prerequisite in one action", () => {
    const {result} = renderHook(() => useBracketReveal(makeModel()));

    act(() => result.current.revealThroughRound(40));

    expect([...result.current.revealedRounds]).toEqual([10, 30, 40]);
    expect(result.current.revealedRounds.has(40)).toBe(true);
    expect(result.current.canRevealRound(40)).toBe(true);
    expect(result.current.statusMessage).toBe(
      "NBA Finals and required earlier results are shown.",
    );
  });
});
