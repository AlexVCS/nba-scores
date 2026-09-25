import {useEffect, useRef, useState, useMemo} from "react";
import {useQuery, useQueryClient} from "@tanstack/react-query";
import {format} from "date-fns";
import {useLocation, useParams, useSearchParams} from "react-router";
import {designPath, detectDesignId} from "../designRoutes";
import {useResultsVisibility} from "@/hooks/useResultsVisibility";
import {isValidDateParam} from "@/helpers/dateParam";
import type {GameData, GameSummaryData, GameSummaryTeam, Player} from "@/helpers/helpers";
import type {GameDetails, InactivePlayer} from "@/services/nbaService";
import {getBoxScores, getGameDetails, getGameSummary, getInactivePlayers, getLastMatchups} from "@/services/nbaService";

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

type ScoreboardTeam = GameData["homeTeam"] & {teamCity?: string};

const scoreboardTeam = (team: ScoreboardTeam): GameDetails["homeTeam"] => ({
  teamId: team.teamId,
  teamTricode: team.teamTricode,
  teamName: [team.teamCity, team.teamName].filter(Boolean).join(" "),
});

// The scoreboard the reader clicked through from already knows the matchup and
// tip-off, so render it immediately while the full details (venue, TV) load.
const detailsFromScoreboard = (game: GameData, date: string): GameDetails => ({
  gameId: game.gameId,
  gameStatus: game.gameStatus,
  gameStatusText: game.gameStatusText,
  gameTimeUTC: game.gameTimeUTC || null,
  gameDate: date || null,
  homeTeam: scoreboardTeam(game.homeTeam),
  awayTeam: scoreboardTeam(game.awayTeam),
  venue: null,
  broadcast: null,
  boxscoreAvailable: Boolean(game.boxscoreAvailable),
});

export function useBoxscorePage() {
  const queryClient = useQueryClient();
  const {gameId = ""} = useParams();
  const [searchParams] = useSearchParams();
  const location = useLocation();
  const {showAllResults} = useResultsVisibility();
  const dateParam = searchParams.get("date") ?? "";
  const scoreboardPath = isValidDateParam(dateParam) ? `/?date=${dateParam}` : "/";
  const from: unknown = location.state?.from;
  const origin = typeof from === "string" && /^\/(?![/\\])/.test(from)
    ? from : designPath(detectDesignId(location.pathname), scoreboardPath);
  const [visit, setVisit] = useState({gameId, showAllResults, revealed: false, backPath: origin});
  // A different game starts a fresh visit even when the router reuses this page.
  if (visit.gameId !== gameId || visit.showAllResults !== showAllResults) {
    setVisit({gameId, showAllResults, revealed: false, backPath: visit.gameId === gameId ? visit.backPath : origin});
  }
  const {backPath} = visit;
  const scoresVisible = showAllResults || (visit.gameId === gameId && visit.showAllResults === showAllResults && visit.revealed);
  const scoreboardGame = isValidDateParam(dateParam)
    ? queryClient.getQueryData<{games?: GameData[]}>(["games", dateParam])?.games?.find((item) => item.gameId === gameId)
    : undefined;
  // Only pregame games are seeded; started games need the details endpoint's
  // box score availability before loading stats.
  const scoreboardDetails = useMemo(
    () => scoreboardGame?.gameStatus === 1 ? detailsFromScoreboard(scoreboardGame, dateParam) : undefined,
    [scoreboardGame, dateParam],
  );
  const detailsQuery = useQuery({
    queryKey: ["gameDetails", gameId, isValidDateParam(dateParam) ? dateParam : ""],
    queryFn: ({signal}) => getGameDetails(gameId, isValidDateParam(dateParam) ? dateParam : "", signal),
    enabled: Boolean(gameId),
    // Live games poll every minute; pregame games only need to notice tip-off.
    refetchInterval: (query) => {
      const status = query.state.data?.gameStatus;
      return status === 2 ? 60_000 : status === 1 ? 5 * 60_000 : false;
    },
    placeholderData: scoreboardDetails,
  });
  const details = detailsQuery.data;
  const isPregame = Boolean(details && (details.gameStatus === 1
    || /postponed|cancelled|canceled/i.test(details.gameStatusText)));
  const isHidden = Boolean(details && !isPregame && !scoresVisible);
  const hasStarted = details?.gameStatus === 2 || details?.gameStatus === 3;
  const loadResults = Boolean(hasStarted && !isPregame && scoresVisible);
  const loadPlayers = loadResults && Boolean(details?.boxscoreAvailable);
  const liveRefreshInterval = loadResults && details?.gameStatus === 2 ? 60_000 : false;
  // Until details arrive, start result requests in parallel when the game has
  // almost certainly tipped off (the scoreboard says so, or its date has passed).
  // Details stay authoritative: every rendered result, loading and error state
  // below is derived from loadResults/loadPlayers, never from these guesses.
  const scoreboardStarted = scoreboardGame?.gameStatus === 2 || scoreboardGame?.gameStatus === 3;
  const pastDate = isValidDateParam(dateParam) && dateParam < format(new Date(), "yyyy-MM-dd");
  const prefetchResults = !details && scoresVisible && Boolean(gameId) && (scoreboardStarted || pastDate);
  const prefetchPlayers = prefetchResults && (scoreboardGame ? Boolean(scoreboardGame.boxscoreAvailable) : true);
  const boxscoreQuery = useQuery({
    queryKey: ["boxscore", gameId],
    queryFn: () => getBoxScores(gameId) as Promise<BoxscoreResponse>,
    enabled: loadPlayers || prefetchPlayers,
    refetchInterval: liveRefreshInterval,
  });
  const summaryQuery = useQuery({
    queryKey: ["gameSummary", gameId],
    queryFn: () => getGameSummary(gameId),
    enabled: loadResults || prefetchResults,
    refetchInterval: liveRefreshInterval,
  });
  const inactiveQuery = useQuery({
    queryKey: ["inactivePlayers", gameId],
    queryFn: ({signal}) => getInactivePlayers(gameId, signal),
    enabled: loadPlayers || prefetchPlayers,
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
  const previousGame = useRef({gameId, status: details?.gameStatus});
  useEffect(() => {
    const previous = previousGame.current;
    previousGame.current = {gameId, status: details?.gameStatus};
    // Polling stops at the buzzer, but its last response may still be live.
    if (previous.gameId === gameId && previous.status === 2 && details?.gameStatus === 3 && loadResults) {
      void queryClient.invalidateQueries({queryKey: ["gameSummary", gameId]});
      if (loadPlayers) void queryClient.invalidateQueries({queryKey: ["boxscore", gameId]});
    }
  }, [gameId, details?.gameStatus, loadPlayers, loadResults, queryClient]);
  const matchupDate = details?.gameDate ?? (isValidDateParam(dateParam) ? dateParam : "");
  const matchupTeams = details ? [details.awayTeam.teamId, details.homeTeam.teamId] as const : null;
  const lastMatchupsQuery = useQuery({
    queryKey: ["lastMatchups", matchupTeams?.[0], matchupTeams?.[1], matchupDate],
    queryFn: ({signal}) => getLastMatchups(matchupTeams![0], matchupTeams![1], matchupDate, signal),
    enabled: Boolean(isPregame && matchupTeams?.[0] && matchupTeams[1] && matchupDate),
    staleTime: 60 * 60 * 1000,
    retry: false,
  });
  const boxscoreGame = loadPlayers ? boxscoreQuery.data?.game : undefined;
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
    backPath,
    backLabel: backPath.includes("/playoffs/") ? "Series" : "Scoreboard",
    details,
    isPregame,
    isHidden,
    scoresVisible,
    reveal: () => setVisit({...visit, revealed: true}),
    game,
    lastMatchups: isPregame ? lastMatchupsQuery.data?.games ?? [] : [],
    lastMatchupsLoading: isPregame && lastMatchupsQuery.isLoading,
    summary: loadResults ? summaryQuery.data ?? fallbackSummary : null,
    isLoading: detailsQuery.isLoading || (loadResults && (loadPlayers && boxscoreQuery.isLoading || summaryQuery.isLoading)),
    isUnavailable: Boolean(details && !isPregame && !isHidden && (!hasStarted || !game && summaryQuery.isSuccess && !summaryQuery.data && (!loadPlayers || boxscoreQuery.isSuccess))),
    isError: !details && detailsQuery.isError || loadResults && !(loadPlayers && boxscoreQuery.isLoading) && !summaryQuery.isLoading && !game && !summaryQuery.data && (summaryQuery.isError || loadPlayers && boxscoreQuery.isError),
    statsError: loadPlayers && boxscoreQuery.isError,
    retry: () => {
      void detailsQuery.refetch();
      if (loadResults) void summaryQuery.refetch();
      if (loadPlayers) void boxscoreQuery.refetch();
    },
  };
}
