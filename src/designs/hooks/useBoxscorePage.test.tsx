import {act, render, renderHook, screen, waitFor} from "@testing-library/react";
import {QueryClient, QueryClientProvider} from "@tanstack/react-query";
import {Link, MemoryRouter, Route, Routes, useNavigate} from "react-router";
import type {ReactNode} from "react";
import {beforeEach, describe, expect, it, vi} from "vitest";
import {getBoxScores, getGameDetails, getGameSummary, getInactivePlayers, getLastMatchups} from "@/services/nbaService";
import type {GameDetails, InactivePlayersResponse} from "@/services/nbaService";
import {useBoxscorePage} from "./useBoxscorePage";

vi.mock("@/services/nbaService", () => ({
  getBoxScores: vi.fn(),
  getGameDetails: vi.fn(),
  getGameSummary: vi.fn(),
  getInactivePlayers: vi.fn(),
  getLastMatchups: vi.fn(),
}));

let showAllResults = true;
vi.mock("@/hooks/useResultsVisibility", () => ({useResultsVisibility: () => ({showAllResults})}));

const details: GameDetails = {
  gameId: "123", gameStatus: 3, gameStatusText: "Final/OT", gameDate: "2026-06-03", gameTimeUTC: null,
  homeTeam: {teamId: 1, teamName: "Home", teamTricode: "HOM"},
  awayTeam: {teamId: 2, teamName: "Away", teamTricode: "AWY"},
  venue: null, broadcast: null, boxscoreAvailable: true,
};

const game = {
  homeTeam: {teamId: 1, score: 100, players: []},
  awayTeam: {teamId: 2, score: 90, players: []},
};

function setup(from?: string) {
  const client = new QueryClient({defaultOptions: {queries: {retry: false}}});
  function Wrapper({children}: {children: ReactNode}) {
    return <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[{pathname: "/games/123/boxscore", state: {from}}]}>
        <Routes><Route path="/games/:gameId/boxscore" element={children} /></Routes>
      </MemoryRouter>
    </QueryClientProvider>;
  }
  return {client, wrapper: Wrapper};
}

beforeEach(() => {
  vi.resetAllMocks();
  showAllResults = true;
  vi.mocked(getGameDetails).mockResolvedValue(details);
  vi.mocked(getInactivePlayers).mockResolvedValue({teams: {}});
  vi.mocked(getBoxScores).mockResolvedValue({game});
  vi.mocked(getGameSummary).mockResolvedValue(null);
  vi.mocked(getLastMatchups).mockResolvedValue({games: []});
});

describe("stat event links", () => {
  it("exposes the boxscore's statEvents and defaults to null when absent", async () => {
    const statEvents = {season: "2025-26", seasonType: "Regular Season", endRange: 28800, measures: {FGM: 3, AST: 1}};
    vi.mocked(getBoxScores).mockResolvedValue({game, statEvents});
    const first = setup();
    const {result, unmount} = renderHook(useBoxscorePage, {wrapper: first.wrapper});
    await waitFor(() => expect(result.current.game).toBeDefined());
    expect(result.current.statEvents).toEqual(statEvents);
    unmount();
    first.client.clear();

    vi.mocked(getBoxScores).mockResolvedValue({game});
    const second = setup();
    const view = renderHook(useBoxscorePage, {wrapper: second.wrapper});
    await waitFor(() => expect(view.result.current.game).toBeDefined());
    expect(view.result.current.statEvents).toBeNull();
    view.unmount();
    second.client.clear();
  });
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


describe("game visits", () => {
  it("refreshes visible live results, fetches the final score, then stops polling", async () => {
    vi.useFakeTimers();
    const {client, wrapper} = setup();
    vi.mocked(getGameDetails).mockResolvedValue({...details, gameStatus: 2});
    const {result, unmount} = renderHook(useBoxscorePage, {wrapper});
    try {
      await act(async () => { await vi.advanceTimersByTimeAsync(50); });
      await act(async () => { await vi.advanceTimersByTimeAsync(50); });
      expect(result.current.game?.homeTeam.score).toBe(100);
      vi.mocked(getBoxScores).mockResolvedValue({game: {...game, homeTeam: {...game.homeTeam, score: 105}}});
      await act(async () => { await vi.advanceTimersByTimeAsync(60_050); });
      expect(result.current.game?.homeTeam.score).toBe(105);
      expect(getGameSummary).toHaveBeenCalledTimes(2);

      vi.mocked(getBoxScores).mockResolvedValue({game: {...game, homeTeam: {...game.homeTeam, score: 110}}});
      vi.mocked(getGameDetails).mockResolvedValue(details);
      await act(async () => { await client.refetchQueries({queryKey: ["gameDetails", "123"]}); });
      await act(async () => { await vi.advanceTimersByTimeAsync(50); });
      await act(async () => { await vi.advanceTimersByTimeAsync(50); });
      expect(result.current.game?.homeTeam.score).toBe(110);
      const calls = vi.mocked(getBoxScores).mock.calls.length;
      await act(async () => { await vi.advanceTimersByTimeAsync(120_000); });
      expect(getBoxScores).toHaveBeenCalledTimes(calls);
    } finally {
      unmount();
      client.clear();
      vi.useRealTimers();
    }
  });

  it("does not poll results while a live game is hidden", async () => {
    vi.useFakeTimers();
    showAllResults = false;
    vi.mocked(getGameDetails).mockResolvedValue({...details, gameStatus: 2});
    const {client, wrapper} = setup();
    const {result, unmount} = renderHook(useBoxscorePage, {wrapper});
    try {
      await act(async () => { await vi.advanceTimersByTimeAsync(120_050); });
      expect(result.current.isHidden).toBe(true);
      expect(getGameDetails).toHaveBeenCalledTimes(3);
      expect(getBoxScores).not.toHaveBeenCalled();
      expect(getGameSummary).not.toHaveBeenCalled();
    } finally {
      unmount();
      client.clear();
      vi.useRealTimers();
    }
  });

  it("gates cached results and requests until explicitly revealed, then resets on remount", async () => {
    showAllResults = false;
    const {client, wrapper} = setup();
    client.setQueryData(["boxscore", "123"], {game});
    const first = renderHook(useBoxscorePage, {wrapper});
    await waitFor(() => expect(first.result.current.isHidden).toBe(true));
    expect(first.result.current.game).toBeUndefined();
    expect(first.result.current.summary).toBeNull();
    expect(getBoxScores).not.toHaveBeenCalled();
    expect(getGameSummary).not.toHaveBeenCalled();
    expect(getInactivePlayers).not.toHaveBeenCalled();
    act(() => first.result.current.reveal());
    await waitFor(() => expect(first.result.current.game).toMatchObject(game));
    first.unmount();
    const second = renderHook(useBoxscorePage, {wrapper});
    expect(second.result.current.isHidden).toBe(true);
    expect(second.result.current.game).toBeUndefined();
    expect(second.result.current.summary).toBeNull();
    second.unmount();
    client.clear();
  });

  it("keeps a reveal for layout changes but clears it when navigating to another game and back", async () => {
    showAllResults = false;
    const {client, wrapper} = setup("/design-1/playoffs/2026/finals");
    const {result, unmount} = renderHook(() => ({page: useBoxscorePage(), navigate: useNavigate()}), {wrapper});
    await waitFor(() => expect(result.current.page.isHidden).toBe(true));
    act(() => result.current.page.reveal());
    await waitFor(() => expect(result.current.page.game).toMatchObject(game));
    act(() => result.current.navigate("?view=stacked", {replace: true}));
    expect(result.current.page.scoresVisible).toBe(true);
    expect(result.current.page.backPath).toBe("/design-1/playoffs/2026/finals");
    act(() => result.current.navigate("/games/456/boxscore"));
    await waitFor(() => expect(result.current.page.isHidden).toBe(true));
    expect(result.current.page.game).toBeUndefined();
    act(() => result.current.navigate(-1));
    await waitFor(() => expect(result.current.page.gameId).toBe("123"));
    expect(result.current.page.isHidden).toBe(true);
    unmount();
    client.clear();
  });

  it("resets when leaving the game for the scoreboard and using browser Back", async () => {
    showAllResults = false;
    const client = new QueryClient({defaultOptions: {queries: {retry: false}}});
    function GameVisit() {
      const page = useBoxscorePage();
      return <><span>{page.isHidden ? "Hidden" : page.scoresVisible ? "Revealed" : "Loading"}</span>
        <button onClick={page.reveal}>Reveal</button><Link to="/">Scoreboard</Link></>;
    }
    function Scoreboard() {
      const navigate = useNavigate();
      return <button onClick={() => navigate(-1)}>Back</button>;
    }
    const view = render(<QueryClientProvider client={client}><MemoryRouter initialEntries={["/games/123/boxscore"]}>
      <Routes><Route path="/games/:gameId/boxscore" element={<GameVisit />} /><Route path="/" element={<Scoreboard />} /></Routes>
    </MemoryRouter></QueryClientProvider>);
    await screen.findByText("Hidden");
    act(() => screen.getByText("Reveal").click());
    expect(screen.getByText("Revealed")).toBeVisible();
    act(() => screen.getByText("Scoreboard").click());
    act(() => screen.getByText("Back").click());
    expect(screen.getByText("Hidden")).toBeVisible();
    view.unmount();
    client.clear();
  });

  it("shows global results immediately and hides cached content when that setting is disabled", async () => {
    const {client, wrapper} = setup();
    const {result, rerender, unmount} = renderHook(useBoxscorePage, {wrapper});
    await waitFor(() => expect(result.current.game).toMatchObject(game));
    showAllResults = false;
    rerender();
    expect(result.current.isHidden).toBe(true);
    expect(result.current.game).toBeUndefined();
    expect(result.current.summary).toBeNull();
    unmount();
    client.clear();
  });

  it.each(["7:30 pm ET", "Postponed", "Cancelled"])("shows pregame metadata (%s) without requesting stats", async (gameStatusText) => {
    vi.mocked(getGameDetails).mockResolvedValue({...details, gameStatus: 1, gameStatusText});
    const {client, wrapper} = setup();
    const {result, unmount} = renderHook(useBoxscorePage, {wrapper});
    await waitFor(() => expect(result.current.isPregame).toBe(true));
    expect(result.current.isLoading).toBe(false);
    expect(result.current.isHidden).toBe(false);
    expect(result.current.game).toBeUndefined();
    expect(getBoxScores).not.toHaveBeenCalled();
    expect(getGameSummary).not.toHaveBeenCalled();
    unmount();
    client.clear();
  });

  it("transitions from upcoming to live without revealing results", async () => {
    showAllResults = false;
    vi.mocked(getGameDetails).mockResolvedValue({...details, gameStatus: 1});
    const {client, wrapper} = setup();
    const {result, unmount} = renderHook(useBoxscorePage, {wrapper});
    await waitFor(() => expect(result.current.isPregame).toBe(true));
    vi.mocked(getGameDetails).mockResolvedValue({...details, gameStatus: 2});
    await act(async () => {await client.invalidateQueries({queryKey: ["gameDetails"]});});
    await waitFor(() => expect(result.current.isPregame).toBe(false));
    expect(result.current.isHidden).toBe(true);
    expect(getBoxScores).not.toHaveBeenCalled();
    unmount();
    client.clear();
  });

  it.each([false, true])("offers retry for a failed summary even when player coverage is %s", async (boxscoreAvailable) => {
    vi.mocked(getGameDetails).mockResolvedValue({...details, boxscoreAvailable});
    vi.mocked(getBoxScores).mockResolvedValue({game: null});
    vi.mocked(getGameSummary).mockRejectedValue(new Error("Game summary fetch failed"));
    const {client, wrapper} = setup();
    const {result, unmount} = renderHook(useBoxscorePage, {wrapper});
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.isUnavailable).toBe(false);
    expect(result.current.details?.homeTeam.teamName).toBe("Home");
    vi.mocked(getGameSummary).mockResolvedValue(null);
    act(() => result.current.retry());
    await waitFor(() => expect(result.current.isUnavailable).toBe(true));
    expect(result.current.isError).toBe(false);
    unmount();
    client.clear();
  });

  it("retains metadata when historical stats are unavailable", async () => {
    vi.mocked(getGameDetails).mockResolvedValue({...details, boxscoreAvailable: false});
    const {client, wrapper} = setup();
    const {result, unmount} = renderHook(useBoxscorePage, {wrapper});
    await waitFor(() => expect(result.current.isUnavailable).toBe(true));
    expect(result.current.details?.homeTeam.teamName).toBe("Home");
    expect(result.current.isError).toBe(false);
    expect(getBoxScores).not.toHaveBeenCalled();
    unmount();
    client.clear();
  });
});

describe("scoreboard seeding", () => {
  it("renders a pregame matchup from the cached scoreboard while details load", async () => {
    vi.mocked(getGameDetails).mockReturnValue(new Promise(() => {}));
    const client = new QueryClient({defaultOptions: {queries: {retry: false}}});
    client.setQueryData(["games", "2026-10-03"], {games: [{
      gameId: "123", gameStatus: 1, gameStatusText: "7:00 pm ET", gameTimeUTC: "2026-10-03T23:00:00Z",
      homeTeam: {teamId: 1, teamCity: "Toronto", teamName: "Raptors", teamTricode: "TOR", score: 0},
      awayTeam: {teamId: 2, teamCity: "Miami", teamName: "Heat", teamTricode: "MIA", score: 0},
    }]});
    const wrapper = ({children}: {children: ReactNode}) => <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={["/games/123/boxscore?date=2026-10-03"]}>
        <Routes><Route path="/games/:gameId/boxscore" element={children} /></Routes>
      </MemoryRouter>
    </QueryClientProvider>;
    const {result} = renderHook(useBoxscorePage, {wrapper});
    expect(result.current.isPregame).toBe(true);
    expect(result.current.details?.homeTeam).toEqual({teamId: 1, teamTricode: "TOR", teamName: "Toronto Raptors"});
    expect(result.current.details?.venue).toBeNull();
    client.clear();
  });
});

describe("parallel result requests", () => {
  function setupAt(date: string) {
    const client = new QueryClient({defaultOptions: {queries: {retry: false}}});
    function Wrapper({children}: {children: ReactNode}) {
      return <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={[`/games/123/boxscore?date=${date}`]}>
          <Routes><Route path="/games/:gameId/boxscore" element={children} /></Routes>
        </MemoryRouter>
      </QueryClientProvider>;
    }
    return {client, wrapper: Wrapper};
  }

  it("requests a past game's results before its details resolve", async () => {
    let resolve!: (value: GameDetails) => void;
    vi.mocked(getGameDetails).mockReturnValue(new Promise((done) => {resolve = done;}));
    const {client, wrapper} = setupAt("2025-11-04");
    const {result, unmount} = renderHook(useBoxscorePage, {wrapper});
    await waitFor(() => expect(getBoxScores).toHaveBeenCalledTimes(1));
    expect(getGameSummary).toHaveBeenCalledTimes(1);
    expect(getInactivePlayers).toHaveBeenCalledTimes(1);
    expect(result.current.isLoading).toBe(true);
    expect(result.current.game).toBeUndefined();
    await act(async () => resolve(details));
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.game?.homeTeam.score).toBe(100);
    expect(getBoxScores).toHaveBeenCalledTimes(1);
    expect(getGameSummary).toHaveBeenCalledTimes(1);
    unmount();
    client.clear();
  });

  it("requests results early when the cached scoreboard shows the game started", async () => {
    vi.mocked(getGameDetails).mockReturnValue(new Promise(() => {}));
    const {client, wrapper} = setupAt("2099-01-01");
    client.setQueryData(["games", "2099-01-01"], {games: [{
      gameId: "123", gameStatus: 2, gameStatusText: "Q2 5:00", boxscoreAvailable: true,
      homeTeam: {teamId: 1, teamName: "Home", teamTricode: "HOM", score: 30},
      awayTeam: {teamId: 2, teamName: "Away", teamTricode: "AWY", score: 28},
    }]});
    const {unmount} = renderHook(useBoxscorePage, {wrapper});
    await waitFor(() => expect(getBoxScores).toHaveBeenCalledTimes(1));
    expect(getGameSummary).toHaveBeenCalledTimes(1);
    unmount();
    client.clear();
  });

  it("waits for details before requesting results for a future game", async () => {
    vi.mocked(getGameDetails).mockResolvedValue({...details, gameStatus: 1, gameStatusText: "7:30 pm ET"});
    const {client, wrapper} = setupAt("2099-01-01");
    const {result, unmount} = renderHook(useBoxscorePage, {wrapper});
    await waitFor(() => expect(result.current.isPregame).toBe(true));
    expect(getBoxScores).not.toHaveBeenCalled();
    expect(getGameSummary).not.toHaveBeenCalled();
    expect(getInactivePlayers).not.toHaveBeenCalled();
    unmount();
    client.clear();
  });

  it("does not request results early while scores are hidden", async () => {
    showAllResults = false;
    vi.mocked(getGameDetails).mockReturnValue(new Promise(() => {}));
    const {client, wrapper} = setupAt("2025-11-04");
    const {unmount} = renderHook(useBoxscorePage, {wrapper});
    await act(async () => {await Promise.resolve();});
    expect(getBoxScores).not.toHaveBeenCalled();
    expect(getGameSummary).not.toHaveBeenCalled();
    unmount();
    client.clear();
  });

  it("ignores failed early requests when details say the game has not started", async () => {
    let resolve!: (value: GameDetails) => void;
    vi.mocked(getGameDetails).mockReturnValue(new Promise((done) => {resolve = done;}));
    vi.mocked(getBoxScores).mockRejectedValue(new Error("Boxscore fetch failed"));
    vi.mocked(getGameSummary).mockRejectedValue(new Error("Game summary fetch failed"));
    const {client, wrapper} = setupAt("2025-11-04");
    const {result, unmount} = renderHook(useBoxscorePage, {wrapper});
    await waitFor(() => expect(client.getQueryState(["gameSummary", "123"])?.status).toBe("error"));
    await waitFor(() => expect(client.getQueryState(["boxscore", "123"])?.status).toBe("error"));
    await act(async () => resolve({...details, gameStatus: 1, gameStatusText: "Postponed"}));
    await waitFor(() => expect(result.current.isPregame).toBe(true));
    expect(result.current.isLoading).toBe(false);
    expect(result.current.isError).toBe(false);
    expect(result.current.statsError).toBe(false);
    expect(result.current.isUnavailable).toBe(false);
    expect(result.current.summary).toBeNull();
    expect(result.current.game).toBeUndefined();
    unmount();
    client.clear();
  });
});
