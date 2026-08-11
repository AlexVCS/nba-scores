import {describe, expect, it} from "vitest";
import {chooseRandomGameDay, formatGameDateParam, parseGameDateParam} from "./useRandomGameDay";

describe("random game day helpers", () => {
  it("chooses a stable indexed date", () => {
    expect(chooseRandomGameDay(["2026-01-03", "2026-01-02"], "2026-01-01", 3)).toBe("2026-01-02");
  });

  it("falls back when no schedule dates are available", () => {
    expect(chooseRandomGameDay([], "2026-01-01")).toBe("2026-01-01");
  });

  it("validates and formats local date parameters", () => {
    expect(parseGameDateParam("2026-02-29")).toBeUndefined();
    expect(formatGameDateParam(new Date(2026, 0, 2))).toBe("2026-01-02");
  });
});
