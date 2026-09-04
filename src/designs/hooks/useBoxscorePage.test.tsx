import {act, renderHook, waitFor} from "@testing-library/react";
import {QueryClient, QueryClientProvider} from "@tanstack/react-query";
import {MemoryRouter, Route, Routes} from "react-router";
import type {ReactNode} from "react";
import {beforeEach, describe, expect, it, vi} from "vitest";
import {getBoxScores, getGameSummary, getInactivePlayers} from "@/services/nbaService";
import type {InactivePlayersResponse} from "@/services/nbaService";
import {useBoxscorePage} from "./useBoxscorePage";

vi.mock("@/services/nbaService", () => ({
  getBoxScores: vi.fn(),
  getGameSummary: vi.fn(),
  getInactivePlayers: vi.fn(),
}));

const game = {
  homeTeam: {teamId: 1, score: 100, players: []},
  awayTeam: {teamId: 2, score: 90, players: []},
};

function setup() {
  const client = new QueryClient({defaultOptions: {queries: {retry: false}}});
  function Wrapper({children}: {children: ReactNode}) {
    return <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={["/games/123/boxscore"]}>
        <Routes><Route path="/games/:gameId/boxscore" element={children} /></Routes>
      </MemoryRouter>
    </QueryClientProvider>;
  }
  return {client, wrapper: Wrapper};
}

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(getBoxScores).mockResolvedValue({game});
  vi.mocked(getGameSummary).mockRejectedValue(new Error("Summary unavailable"));
});

describe("optional inactive players", () => {
  it("returns scores while pending, then merges by team without changing the cache", async () => {
    let resolve!: (value: InactivePlayersResponse) => void;
    vi.mocked(getInactivePlayers).mockReturnValue(new Promise((done) => {resolve = done;}));
    const {client, wrapper} = setup();
    const {result, unmount} = renderHook(useBoxscorePage, {wrapper});
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.game?.homeTeam.score).toBe(100);
    expect(result.current.isError).toBe(false);
    const player = {personId: 20, firstName: "Away", familyName: "Player"};
    await act(async () => resolve({teams: {"2": [player]}}));
    await waitFor(() => expect(result.current.game?.awayTeam.inactivePlayers).toEqual([player]));
    expect(result.current.game?.homeTeam.inactivePlayers).toEqual([]);
    expect(client.getQueryData(["boxscore", "123"])).toEqual({game});
    expect(game.awayTeam).not.toHaveProperty("inactivePlayers");
    unmount();
    const second = renderHook(useBoxscorePage, {wrapper});
    await waitFor(() => expect(second.result.current.game?.awayTeam.inactivePlayers).toEqual([player]));
    expect(getInactivePlayers).toHaveBeenCalledTimes(1);
    second.unmount();
    client.clear();
  });

  it("keeps scores usable when the optional request fails without retrying", async () => {
    vi.mocked(getInactivePlayers).mockRejectedValue(new Error("unavailable"));
    const {client, wrapper} = setup();
    const {result, unmount} = renderHook(useBoxscorePage, {wrapper});
    await waitFor(() => expect(client.getQueryState(["inactivePlayers", "123"])?.status).toBe("error"));
    expect(result.current.isLoading).toBe(false);
    expect(result.current.isError).toBe(false);
    expect(result.current.game?.homeTeam.score).toBe(100);
    expect(getInactivePlayers).toHaveBeenCalledTimes(1);
    unmount();
    client.clear();
  });
});
