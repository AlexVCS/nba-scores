import {describe, expect, it} from "vitest";
import {designPath, stripDesignPrefix} from "./designRoutes";

describe("design routes", () => {
  it("removes a legacy design prefix", () => {
    expect(stripDesignPrefix("/design-1/playoffs/2025/east-finals"))
      .toBe("/playoffs/2025/east-finals");
    expect(stripDesignPrefix("/design-1")).toBe("/");
    expect(stripDesignPrefix("/original")).toBe("/");
    expect(stripDesignPrefix("/original/games/002/boxscore")).toBe("/games/002/boxscore");
  });

  it("leaves unprefixed routes and partial prefix matches alone", () => {
    expect(stripDesignPrefix("/games/123/boxscore")).toBe("/games/123/boxscore");
    expect(stripDesignPrefix("/design-10/playoffs")).toBe("/design-10/playoffs");
  });

  it("builds unprefixed internal links and leaves external links alone", () => {
    expect(designPath("design-1", "/playoffs?season=2025-26")).toBe("/playoffs?season=2025-26");
    expect(designPath("design-1", "/design-1/games/002/boxscore#stats")).toBe("/games/002/boxscore#stats");
    expect(designPath("design-1", "/")).toBe("/");
    expect(designPath("design-1", "/?date=2026-02-05")).toBe("/?date=2026-02-05");
    expect(designPath("design-1", "https://nba.com/game/example")).toBe("https://nba.com/game/example");
  });
});
