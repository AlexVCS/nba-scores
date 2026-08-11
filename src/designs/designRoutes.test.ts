import {describe, expect, it} from "vitest";
import {buildDesignHref, designPath, detectDesignId, stripDesignPrefix} from "./designRoutes";
import {DESIGN_DEFINITIONS} from "./designRegistry";

const DESIGN_PREVIEW_BASE_PATH = "/preview/test-token-that-is-at-least-32-characters";

describe("design routes", () => {
  it.each([1, 2, 3, 4])("detects design-%s", (number) => {
    expect(detectDesignId(`${DESIGN_PREVIEW_BASE_PATH}/design-${number}/playoffs`)).toBe(`design-${number}`);
  });

  it.each([5, 11, 14, 16])("does not recognize retired design-%s", (number) => {
    expect(detectDesignId(`${DESIGN_PREVIEW_BASE_PATH}/design-${number}/playoffs`)).toBe("original");
  });

  it("treats public and formerly predictable routes as original", () => {
    expect(detectDesignId("/games/123/boxscore")).toBe("original");
    expect(detectDesignId("/design-1")).toBe("original");
  });

  it("removes a design prefix", () => {
    expect(stripDesignPrefix(
      `${DESIGN_PREVIEW_BASE_PATH}/design-3/playoffs/2025/east-finals`,
    )).toBe("/playoffs/2025/east-finals");
  });

  it("maps deep routes while preserving search and hash", () => {
    expect(buildDesignHref("design-4", {
      pathname: `${DESIGN_PREVIEW_BASE_PATH}/design-2/playoffs/2025/east-finals`,
      search: "?season=2024-25&revealed=true",
      hash: "#games",
    })).toBe(`${DESIGN_PREVIEW_BASE_PATH}/design-4/playoffs/2025/east-finals?season=2024-25&revealed=true#games`);
  });

  it("maps a design route to the preview copy of the original", () => {
    expect(buildDesignHref("original", {
      pathname: `${DESIGN_PREVIEW_BASE_PATH}/design-1/games/002/boxscore`,
      search: "?date=2026-04-18",
    })).toBe(`${DESIGN_PREVIEW_BASE_PATH}/original/games/002/boxscore?date=2026-04-18`);
  });

  it("falls back to the selected homepage for unknown routes", () => {
    expect(buildDesignHref("design-2", {
      pathname: `${DESIGN_PREVIEW_BASE_PATH}/design-2/settings`,
      search: "?tab=a",
    }))
      .toBe(`${DESIGN_PREVIEW_BASE_PATH}/design-2/?tab=a`);
  });

  it("prefixes internal links and leaves external links alone", () => {
    window.history.replaceState({}, "", `${DESIGN_PREVIEW_BASE_PATH}/design-4`);
    expect(designPath("design-4", "/playoffs?season=2025-26"))
      .toBe(`${DESIGN_PREVIEW_BASE_PATH}/design-4/playoffs?season=2025-26`);
    expect(designPath("design-4", "https://nba.com/game/example")).toBe("https://nba.com/game/example");
  });

  it("registers the original and four unique alternatives", () => {
    expect(DESIGN_DEFINITIONS).toHaveLength(5);
    expect(new Set(DESIGN_DEFINITIONS.map((design) => design.id)).size).toBe(5);
    expect(DESIGN_DEFINITIONS.map((design) => design.number)).toEqual([null, 1, 2, 3, 4]);
  });
});
