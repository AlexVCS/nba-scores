import {render, screen} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {describe, expect, it, vi} from "vitest";
import type {useBoxscorePage} from "../hooks/useBoxscorePage";
import GameDetailsPanel from "./GameDetailsPanel";

const state: ReturnType<typeof useBoxscorePage> = {
  gameId: "123", scoreboardPath: "/", backPath: "/", backLabel: "Scoreboard",
  details: {
    gameId: "123", gameStatus: 3, gameStatusText: "Final/2OT", gameDate: "2026-06-03", gameTimeUTC: null,
    homeTeam: {teamId: 1, teamName: "Home team", teamTricode: "HOM"},
    awayTeam: {teamId: 2, teamName: "Away team", teamTricode: "AWY"},
    venue: null, broadcast: null, boxscoreAvailable: true,
  },
  isPregame: false, isHidden: true, scoresVisible: false, reveal: vi.fn(),
  game: undefined, lastMatchups: [], lastMatchupsLoading: false, summary: null, isLoading: false, isUnavailable: false, isError: false, statsError: false, retry: vi.fn(),
};

describe("game details panel", () => {
  it("shows matchup and reveal control with no result-bearing status or accessible ghosts", async () => {
    const {container} = render(<GameDetailsPanel state={state} hardwood />);
    expect(screen.getByRole("heading", {level: 1})).toHaveTextContent("Away team at Home team");
    expect(screen.getByText("Scores hidden")).toBeVisible();
    expect(screen.queryByText(/Final|2OT/)).not.toBeInTheDocument();
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    expect(container.querySelectorAll('[aria-hidden="true"]')).toHaveLength(3);
    await userEvent.click(screen.getByRole("button", {name: "Show scores for this game"}));
    expect(state.reveal).toHaveBeenCalledOnce();
  });

  it("shows a focused upcoming page with TBD and optional schedule details", () => {
    render(<GameDetailsPanel state={{...state, isHidden: false, isPregame: true,
      details: {...state.details!, gameStatus: 1, gameStatusText: "TBD", venue: "Arena", broadcast: "ABC"}}} />);
    expect(screen.getByText("Time TBD")).toBeVisible();
    expect(screen.getByText("Arena")).toBeVisible();
    expect(screen.getByText("ABC")).toBeVisible();
    expect(screen.getByText("Box score will be available after tip-off.")).toBeVisible();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it.each(["Postponed", "Cancelled"])("explains %s without promising tip-off", (gameStatusText) => {
    render(<GameDetailsPanel state={{...state, isHidden: false, isPregame: true,
      details: {...state.details!, gameStatus: 1, gameStatusText}}} />);
    expect(screen.getByRole("heading", {name: gameStatusText})).toBeVisible();
    expect(screen.queryByText(/after tip-off/)).not.toBeInTheDocument();
  });

  it("retains matchup and supplies retry when the result request fails", async () => {
    render(<GameDetailsPanel state={{...state, isHidden: false, isError: true}} />);
    expect(screen.getByText("Home team")).toBeVisible();
    await userEvent.click(screen.getByRole("button", {name: "Try again"}));
    expect(state.retry).toHaveBeenCalledOnce();
  });
});
