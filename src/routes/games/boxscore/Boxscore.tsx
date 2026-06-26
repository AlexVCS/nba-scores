import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router";
import GameSummary from "@/components/GameSummary";
import DarkModeToggle from "@/components/DarkModeToggle";
import PlayerTable from "./PlayerTable";
// import InactivePlayers from "./InactivePlayers";
import { getBoxScores, getGameSummary } from "@/services/nbaService";

interface BoxscoreTeam {
  teamId: number;
  teamTricode: string;
  teamCity: string;
  teamName: string;
  statistics?: { points: number };
}

const Boxscore = () => {
  const { gameId = "" } = useParams();

  const boxscoreQuery = useQuery({
    queryKey: ["boxscore", gameId],
    queryFn: () => getBoxScores(gameId),
  });

  const gameSummaryQuery = useQuery({
    queryKey: ["gameSummary", gameId],
    queryFn: () => getGameSummary(gameId),
  });

  if (boxscoreQuery.isLoading || (boxscoreQuery.isError && gameSummaryQuery.isLoading)) {
    return <h1>Loading...</h1>;
  }

  const game = boxscoreQuery.data?.game;

  if (!game && (gameSummaryQuery.isError || !gameSummaryQuery.data)) {
    return <h1>Error loading boxscore data</h1>;
  }

  const buildTeamFromBoxscore = (team: BoxscoreTeam) => ({
    teamId: team.teamId ?? 0,
    teamTricode: team.teamTricode ?? "",
    teamName: `${team.teamCity ?? ""} ${team.teamName ?? ""}`.trim(),
    score: String(team.statistics?.points ?? ""),
    periods: [] as Array<{ period: number; score: string }>,
  });

  const summaryData = gameSummaryQuery.data ?? (!gameSummaryQuery.isLoading && game ? {
    homeTeam: buildTeamFromBoxscore(game.homeTeam),
    awayTeam: buildTeamFromBoxscore(game.awayTeam),
    period: 0,
    gameStatusText: game.gameStatusText ?? "Unknown",
    periodScoreSource: "unavailable" as const,
    periodScoreType: "quarters" as const,
  } : null);

  return (
    <div className="bg-slate-50 dark:bg-neutral-950 min-h-screen">
      <DarkModeToggle />
      {summaryData && <GameSummary game={summaryData} />}
      {game ? (
        <>
          <PlayerTable team={game.homeTeam} />
          <PlayerTable team={game.awayTeam} />
        </>
      ) : (
        <p className="px-4 pb-6 text-center text-sm text-neutral-700 dark:text-slate-300">
          Player boxscore is unavailable for this game.
        </p>
      )}
      {/* <InactivePlayers game={game} /> */}
    </div>
  );
};

export default Boxscore;
