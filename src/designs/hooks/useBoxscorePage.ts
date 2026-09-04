import {useQuery} from "@tanstack/react-query";
import {useParams, useSearchParams} from "react-router";
import {isValidDateParam} from "@/helpers/dateParam";
import type {GameSummaryData, GameSummaryTeam, Player} from "@/helpers/helpers";
import type {InactivePlayer} from "@/services/nbaService";
import {getBoxScores, getGameSummary, getInactivePlayers} from "@/services/nbaService";

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

export type {InactivePlayer} from "@/services/nbaService";

export interface DesignBoxscoreTeam {
  teamId: number;
  teamTricode: string;
  teamCity: string;
  teamName: string;
  score: number;
  players: Player[];
  inactivePlayers?: InactivePlayer[];
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
  const [searchParams] = useSearchParams();
  const dateParam = searchParams.get("date") ?? "";
  const scoreboardPath = isValidDateParam(dateParam) ? `/?date=${dateParam}` : "/";
  const boxscoreQuery = useQuery({
    queryKey: ["boxscore", gameId],
    queryFn: () => getBoxScores(gameId) as Promise<BoxscoreResponse>,
  });
  const summaryQuery = useQuery({
    queryKey: ["gameSummary", gameId],
    queryFn: () => getGameSummary(gameId),
  });
  const inactiveQuery = useQuery({
    queryKey: ["inactivePlayers", gameId],
    queryFn: ({signal}) => getInactivePlayers(gameId, signal),
    enabled: Boolean(gameId),
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
  const boxscoreGame = boxscoreQuery.data?.game;
  const inactiveTeams = inactiveQuery.data?.teams;
  const game = boxscoreGame && inactiveTeams
    ? {
        ...boxscoreGame,
        homeTeam: {
          ...boxscoreGame.homeTeam,
          inactivePlayers: inactiveTeams[String(boxscoreGame.homeTeam.teamId)] ?? [],
        },
        awayTeam: {
          ...boxscoreGame.awayTeam,
          inactivePlayers: inactiveTeams[String(boxscoreGame.awayTeam.teamId)] ?? [],
        },
      }
    : boxscoreGame;

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
    scoreboardPath,
    game,
    summary: summaryQuery.data ?? fallbackSummary,
    isLoading: boxscoreQuery.isLoading || (boxscoreQuery.isError && summaryQuery.isLoading),
    isError: !game && (summaryQuery.isError || (!summaryQuery.isLoading && !summaryQuery.data)),
  };
}
