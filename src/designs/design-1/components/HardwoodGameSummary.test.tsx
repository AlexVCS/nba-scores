import {render, screen} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {describe, expect, it, vi} from "vitest";
import type {GameSummaryData} from "@/helpers/helpers";
import HardwoodGameSummary from "./HardwoodGameSummary";

const team = (teamId: number, teamTricode: string, score: string, scores: number[]) => ({
  teamId, teamTricode, teamName: teamTricode, score,
  periods: scores.map((points, index) => ({period: index + 1, score: String(points)})),
});

const withoutPeriods: GameSummaryData = {
  awayTeam: team(1610612752, "NYK", "68", []),
  homeTeam: team(1610610035, "HUS", "66", []),
  period: 4,
  gameStatusText: "Final",
  periodScoreSource: "unavailable",
  periodScoreRetryAfter: 6,
  periodScoreType: "quarters",
};

describe("HardwoodGameSummary", () => {
  it("keeps the final score and offers a retry while quarter scores are temporarily missing", async () => {
    const onRetry = vi.fn();
    render(<HardwoodGameSummary summary={withoutPeriods} periodRetry={{isRetrying: false, onRetry}} />);
    expect(screen.getByText("68")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Quarter scores are temporarily unavailable.");
    expect(screen.queryByRole("table")).toBeNull();
    await userEvent.click(screen.getByRole("button", {name: "Try again"}));
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it("disables the retry while a request is in flight", () => {
    render(<HardwoodGameSummary summary={withoutPeriods} periodRetry={{isRetrying: true, onRetry: vi.fn()}} />);
    expect(screen.getByRole("button", {name: "Checking…"})).toBeDisabled();
  });

  it("explains permanently missing quarter scores without a retry", () => {
    render(<HardwoodGameSummary summary={{...withoutPeriods, periodScoreRetryAfter: null}} />);
    expect(screen.getByRole("status")).toHaveTextContent("Quarter scores are not available for this game.");
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("shows recovered quarter scores without the notice", () => {
    render(<HardwoodGameSummary summary={{
      ...withoutPeriods,
      awayTeam: team(1610612752, "NYK", "68", [16, 21, 6, 25]),
      homeTeam: team(1610610035, "HUS", "66", [12, 17, 19, 18]),
      periodScoreSource: "basketball-reference",
      periodScoreRetryAfter: null,
    }} />);
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.queryByRole("status")).toBeNull();
  });
});
