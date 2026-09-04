import {afterEach, beforeEach, describe, expect, it, vi} from "vitest";
import {getScores} from "./nbaService";

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
});
