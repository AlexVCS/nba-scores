import {act, renderHook, waitFor} from "@testing-library/react";
import {QueryClient, QueryClientProvider} from "@tanstack/react-query";
import {format} from "date-fns";
import {MemoryRouter, useLocation, useNavigate} from "react-router";
import type {ReactNode} from "react";
import {beforeEach, describe, expect, it, vi} from "vitest";
import {getScores} from "@/services/nbaService";
import {useScoresPage} from "./useScoresPage";

vi.mock("@/services/nbaService", () => ({getScores: vi.fn()}));

const today = format(new Date(), "yyyy-MM-dd");
const futureDate = `${new Date().getFullYear() + 1}-01-02`;
const scheduledGame = {gameId: "001", gameStatus: 1};

function setup(entry = "/design-1") {
  const client = new QueryClient({defaultOptions: {queries: {retry: false}}});
  function Wrapper({children}: {children: ReactNode}) {
    return <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[entry]}>{children}</MemoryRouter>
    </QueryClientProvider>;
  }
  return renderHook(() => ({
    ...useScoresPage({persistScoreReveal: false}),
    location: useLocation(),
    navigate: useNavigate(),
  }), {wrapper: Wrapper});
}

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(getScores).mockResolvedValue({games: []});
});

describe("default scores date", () => {
  it("keeps today when games are scheduled", async () => {
    vi.mocked(getScores).mockResolvedValue({games: [scheduledGame]});
    const {result} = setup();
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(getScores).toHaveBeenCalledExactlyOnceWith("");
    expect(result.current.location.search).toBe("");
  });

  it("selects the next game day and preserves unrelated URL parameters", async () => {
    vi.mocked(getScores).mockImplementation(async (date) => date
      ? {games: [scheduledGame]}
      : {games: [], nextGameDate: futureDate});
    const {result} = setup("/design-1?source=bookmark");
    await waitFor(() => expect(result.current.games).toEqual([scheduledGame]));
    expect(getScores).toHaveBeenCalledTimes(2);
    expect(getScores).toHaveBeenLastCalledWith(futureDate);
    expect(result.current.dateParam).toBe(futureDate);
    expect(result.current.location.search).toContain("source=bookmark");
    expect(result.current.location.search).toContain(`date=${futureDate}`);
  });

  it.each([today, "2025-07-01"])("respects an explicit empty date %s", async (date) => {
    const {result} = setup(`/design-1?date=${date}`);
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.dateParam).toBe(date);
    expect(getScores).toHaveBeenCalledExactlyOnceWith(date);
  });

  it("keeps the empty state when there is no next date", async () => {
    vi.mocked(getScores).mockResolvedValue({games: [], nextGameDate: null});
    const {result} = setup();
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.games).toEqual([]);
    expect(result.current.location.search).toBe("");
  });

  it("does not override a manual date chosen while the schedule is loading", async () => {
    let resolve!: (value: {games: []; nextGameDate: string}) => void;
    vi.mocked(getScores).mockReturnValueOnce(new Promise((done) => {resolve = done;}));
    const {result} = setup();
    await waitFor(() => expect(getScores).toHaveBeenCalled());
    expect(result.current.isLoading).toBe(true);
    await act(async () => result.current.navigate("?date=2025-07-01"));
    await act(async () => resolve({games: [], nextGameDate: futureDate}));
    expect(result.current.dateParam).toBe("2025-07-01");
  });
});
