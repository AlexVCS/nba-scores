import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router";
import GameSummary from "@/components/GameSummary";
import DarkModeToggle from "@/components/DarkModeToggle";
import PlayerTable from "./PlayerTable";
// import InactivePlayers from "./InactivePlayers";
import { getBoxScores, getGameSummary } from "@/services/nbaService";

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

  if (boxscoreQuery.isLoading) {
    return <h1>Loading...</h1>;
  }

  if (boxscoreQuery.isError || !boxscoreQuery.data) {
    return <h1>Error loading boxscore data</h1>;
  }

  const { game } = boxscoreQuery.data;

  const buildTeamFromBoxscore = (team: any) => ({
    teamId: team.teamId ?? 0,
    teamTricode: team.teamTricode ?? "",
    teamName: `${team.teamCity ?? ""} ${team.teamName ?? ""}`.trim(),
    score: String(team.statistics?.points ?? ""),
    periods: [] as Array<{ period: number; score: string }>,
  });

  const summaryData = gameSummaryQuery.data ?? (!gameSummaryQuery.isLoading ? {
    homeTeam: buildTeamFromBoxscore(game.homeTeam),
    awayTeam: buildTeamFromBoxscore(game.awayTeam),
    period: 0,
    gameStatusText: "",
  } : null);

  return (
    <div className="bg-slate-50 dark:bg-neutral-950">
      <DarkModeToggle />
      {summaryData && <GameSummary game={summaryData} />}
      <PlayerTable team={game.homeTeam} />
      <PlayerTable team={game.awayTeam} />
      {/* <InactivePlayers game={game} /> */}
    </div>
  );
};

export default Boxscore;
