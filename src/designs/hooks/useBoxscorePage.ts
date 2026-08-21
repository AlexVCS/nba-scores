import {useQuery} from "@tanstack/react-query";
import {useParams} from "react-router";
import type {GameSummaryData, GameSummaryTeam, Player} from "@/helpers/helpers";
import {getBoxScores, getGameSummary} from "@/services/nbaService";

// Team-level totals from the box score endpoint. Every field beyond `points`
// is optional so older payloads and fixtures that only carry the score keep working.
export interface DesignTeamStatistics {
  points: number;
  minutes?: string;
  fieldGoalsMade?: number;
  fieldGoalsAttempted?: number;
  fieldGoalsPercentage?: number;
  threePointersMade?: number;
  threePointersAttempted?: number;
  threePointersPercentage?: number;
  freeThrowsMade?: number;
  freeThrowsAttempted?: number;
  freeThrowsPercentage?: number;
  reboundsOffensive?: number;
  reboundsDefensive?: number;
  reboundsTotal?: number;
  assists?: number;
  steals?: number;
  blocks?: number;
  turnovers?: number;
  foulsPersonal?: number;
  plusMinusPoints?: number;
}

export interface DesignBoxscoreTeam {
  teamId: number;
  teamTricode: string;
  teamCity: string;
  teamName: string;
  score: number;
  players: Player[];
  statistics?: DesignTeamStatistics;
}

export interface DesignBoxscoreGame {
  gameStatusText?: string;
  homeTeam: DesignBoxscoreTeam;
  awayTeam: DesignBoxscoreTeam;
}

interface BoxscoreResponse {
  game?: DesignBoxscoreGame;
}

const buildSummaryTeam = (team: DesignBoxscoreTeam): GameSummaryTeam => ({
  teamId: team.teamId ?? 0,
  teamTricode: team.teamTricode ?? "",
  teamName: `${team.teamCity ?? ""} ${team.teamName ?? ""}`.trim(),
  score: String(team.statistics?.points ?? team.score ?? ""),
  periods: [],
});

export function useBoxscorePage() {
  const {gameId = ""} = useParams();
  const boxscoreQuery = useQuery({
    queryKey: ["boxscore", gameId],
    queryFn: () => getBoxScores(gameId) as Promise<BoxscoreResponse>,
  });
  const summaryQuery = useQuery({
    queryKey: ["gameSummary", gameId],
    queryFn: () => getGameSummary(gameId),
  });
  const game = boxscoreQuery.data?.game;

  const fallbackSummary: GameSummaryData | null = !summaryQuery.isLoading && game
    ? {
        homeTeam: buildSummaryTeam(game.homeTeam),
        awayTeam: buildSummaryTeam(game.awayTeam),
        period: 0,
        gameStatusText: game.gameStatusText ?? "Unknown",
        periodScoreSource: "unavailable",
        periodScoreType: "quarters",
      }
    : null;

  return {
    gameId,
    game,
    summary: summaryQuery.data ?? fallbackSummary,
    isLoading: boxscoreQuery.isLoading || (boxscoreQuery.isError && summaryQuery.isLoading),
    isError: !game && (summaryQuery.isError || (!summaryQuery.isLoading && !summaryQuery.data)),
  };
}
