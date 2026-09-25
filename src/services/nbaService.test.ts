import {afterEach, beforeEach, describe, expect, it, vi} from "vitest";
import {getBoxScores, getGameSummary, getRecentGameDays, getScores} from "./nbaService";

describe("API URL configuration", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({}),
    }));
    vi.stubGlobal("location", new URL("http://192.168.1.42:5173"));
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  it("uses the explicit development backend address and port", async () => {
    vi.stubEnv("DEV", true);
    vi.stubEnv("VITE_API_URL_DEV", "http://backend.example:9000");

    await getScores("2026-09-04");

    expect(fetch).toHaveBeenCalledWith("http://backend.example:9000/?date=2026-09-04");
  });

  it.each([undefined, ""])("uses the phone hostname when the override is %s", async (override) => {
    vi.stubEnv("DEV", true);
    vi.stubEnv("VITE_API_URL_DEV", override);

    await getScores("");

    expect(fetch).toHaveBeenCalledWith("http://192.168.1.42:8000/");
  });

  it("uses the production backend regardless of the development override", async () => {
    vi.stubEnv("DEV", false);
    vi.stubEnv("VITE_API_URL_DEV", "http://backend.example:9000");
    vi.stubEnv("VITE_API_URL_PROD", "https://api.example.com");

    await getScores("");

    expect(fetch).toHaveBeenCalledWith("https://api.example.com/");
  });
  it("treats missing box scores and summaries as unavailable coverage", async () => {
    vi.mocked(fetch).mockResolvedValue(new Response(null, {status: 404}));
    await expect(getBoxScores("123")).resolves.toEqual({game: null});
    await expect(getGameSummary("123")).resolves.toBeNull();
  });

  it("keeps temporary box score and summary failures retryable", async () => {
    vi.mocked(fetch).mockResolvedValue(new Response(null, {status: 503}));
    await expect(getBoxScores("123")).rejects.toThrow("Boxscore fetch failed");
    await expect(getGameSummary("123")).rejects.toThrow("Game summary fetch failed");
  });

  it("requests recent game days before the given date", async () => {
    vi.stubEnv("DEV", true);
    vi.stubEnv("VITE_API_URL_DEV", "http://backend.example:9000");

    await getRecentGameDays("2026-09-25");

    expect(fetch).toHaveBeenCalledWith("http://backend.example:9000/api/game-days/recent?before=2026-09-25");
  });

  it("throws when the recent game days request fails", async () => {
    vi.mocked(fetch).mockResolvedValue(new Response(null, {status: 500}));
    await expect(getRecentGameDays("2026-09-25")).rejects.toThrow("Recent game days fetch failed");
  });

});
