import {describe, expect, it} from "vitest";
import {buildDesignHref, designPath, detectDesignId, stripDesignPrefix} from "./designRoutes";
import {DESIGN_DEFINITIONS} from "./designRegistry";

describe("design routes", () => {
  it("detects design-1 at its root and on deep routes", () => {
    expect(detectDesignId("/design-1")).toBe("design-1");
    expect(detectDesignId("/design-1/playoffs")).toBe("design-1");
  });

  it.each([2, 3, 4, 5, 6, 11, 14, 16])("does not recognize retired design-%s", (number) => {
    expect(detectDesignId(`/design-${number}/playoffs`)).toBe("original");
  });

  it("treats public routes and partial prefix matches as original", () => {
    expect(detectDesignId("/games/123/boxscore")).toBe("original");
    expect(detectDesignId("/original/playoffs")).toBe("original");
    expect(detectDesignId("/design-10/playoffs")).toBe("original");
  });

  it("removes a design prefix", () => {
    expect(stripDesignPrefix("/design-1/playoffs/2025/east-finals"))
      .toBe("/playoffs/2025/east-finals");
    expect(stripDesignPrefix("/original")).toBe("/");
    expect(stripDesignPrefix("/design-10/playoffs")).toBe("/design-10/playoffs");
  });

  it("maps deep routes while preserving search and hash", () => {
    expect(buildDesignHref("design-1", {
      pathname: "/original/playoffs/2025/east-finals",
      search: "?season=2024-25&revealed=true",
      hash: "#games",
    })).toBe("/design-1/playoffs/2025/east-finals?season=2024-25&revealed=true#games");
  });

  it("maps a design route to the equivalent original route", () => {
    expect(buildDesignHref("original", {
      pathname: "/design-1/games/002/boxscore",
      search: "?date=2026-04-18",
      hash: "#leaders",
    })).toBe("/original/games/002/boxscore?date=2026-04-18#leaders");
  });

  it("falls back to the selected homepage for unknown routes", () => {
    expect(buildDesignHref("design-1", {
      pathname: "/design-1/settings",
      search: "?tab=a",
    }))
      .toBe("/design-1?tab=a");
  });

  it("builds internal links without reading window location and leaves external links alone", () => {
    expect(designPath("design-1", "/playoffs?season=2025-26"))
      .toBe("/design-1/playoffs?season=2025-26");
    expect(designPath("original", "/design-1/games/002/boxscore#stats"))
      .toBe("/original/games/002/boxscore#stats");
    expect(designPath("design-1", "https://nba.com/game/example")).toBe("https://nba.com/game/example");
  });

  it("uses canonical design roots without a trailing slash", () => {
    expect(designPath("design-1", "/")).toBe("/design-1");
    expect(designPath("original", "/")).toBe("/original");
    expect(buildDesignHref("design-1", {pathname: "/original"})).toBe("/design-1");
    expect(buildDesignHref("original", {pathname: "/design-1"})).toBe("/original");
  });

  it("registers the original and Hardwood as the sole alternative", () => {
    expect(DESIGN_DEFINITIONS).toHaveLength(2);
    expect(new Set(DESIGN_DEFINITIONS.map((design) => design.id)).size).toBe(2);
    expect(DESIGN_DEFINITIONS.map((design) => design.number)).toEqual([null, 1]);
  });
});
