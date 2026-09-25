import {createElement} from "react";
import type {ReactNode} from "react";
import {renderHook, waitFor} from "@testing-library/react";
import {QueryClient, QueryClientProvider} from "@tanstack/react-query";
import {beforeEach, describe, expect, it, vi} from "vitest";
import {getRecentGameDays} from "@/services/nbaService";
import {chooseRandomGameDay, formatGameDateParam, parseGameDateParam, useRandomGameDay} from "./useRandomGameDay";

vi.mock("@/services/nbaService", () => ({getRecentGameDays: vi.fn()}));

function setup(options: Parameters<typeof useRandomGameDay>[0]) {
  const client = new QueryClient({defaultOptions: {queries: {retryDelay: 0}}});
  function Wrapper({children}: {children: ReactNode}) {
    return createElement(QueryClientProvider, {client}, children);
  }
  return renderHook(() => useRandomGameDay(options), {wrapper: Wrapper});
}

beforeEach(() => {
  vi.resetAllMocks();
});

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

describe("useRandomGameDay", () => {
  it("fetches recent game days once and picks from dates before the active date", async () => {
    vi.mocked(getRecentGameDays).mockResolvedValue({
      before: "2026-03-10",
      game_days: ["2026-03-10", "2026-02-01", "2026-03-08", "2026-03-08"],
      total: 4,
    });
    const {result} = setup({dateParam: "2026-03-10", randomIndex: 1});

    expect(result.current.isLoading).toBe(true);
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(getRecentGameDays).toHaveBeenCalledExactlyOnceWith("2026-03-10");
    expect(result.current.lastGameDay).toBe("2026-03-08");
    expect(result.current.randomGameDay).toBe("2026-02-01");
    expect(result.current.previousDate).toBe("2026-03-09");
  });

  it("falls back to the previous day when the request fails", async () => {
    vi.mocked(getRecentGameDays).mockRejectedValue(new Error("Recent game days fetch failed"));
    const {result} = setup({dateParam: "2026-03-10"});

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(getRecentGameDays).toHaveBeenCalledTimes(2);
    expect(result.current.randomGameDay).toBe("2026-03-09");
    expect(result.current.lastGameDay).toBe("2026-03-09");
  });

  it("skips the request for unsupported years", () => {
    const {result} = setup({dateParam: "1999-03-10"});

    expect(result.current.isLoading).toBe(false);
    expect(getRecentGameDays).not.toHaveBeenCalled();
    expect(result.current.randomGameDay).toBe("1999-03-09");
  });
});
