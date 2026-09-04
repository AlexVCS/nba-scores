import {describe, expect, it} from "vitest";
import {bracketRow, bracketRowSeparation} from "./desktopBracketGeometry";

describe("desktop bracket row separation", () => {
  it("keeps ordinary opening-round cards on alternating rows", () => {
    const slots = [0, 1, 2, 3].map(order => ({roundIndex: 0, order}));
    expect(slots.map(slot => bracketRow(slot.roundIndex, slot.order))).toEqual([1, 3, 5, 7]);
    expect(bracketRowSeparation([slots])).toBe(2);
  });

  it("reserves full card clearance for the historical three-semifinal layout", () => {
    const slots = [0, 1, 2].map(order => ({roundIndex: 1, order}));
    expect(slots.map(slot => bracketRow(slot.roundIndex, slot.order))).toEqual([2, 6, 7]);
    expect(bracketRowSeparation([slots])).toBe(1);
  });

  it("shares the tightest separation across both conferences", () => {
    expect(bracketRowSeparation([
      [{roundIndex: 0, order: 0}, {roundIndex: 0, order: 1}],
      [{roundIndex: 1, order: 1}, {roundIndex: 1, order: 2}],
    ])).toBe(1);
    expect(bracketRowSeparation([])).toBe(2);
  });
});
