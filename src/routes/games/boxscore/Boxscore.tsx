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

  if (boxscoreQuery.isLoading || gameSummaryQuery.isLoading) {
    return <h1>Loading...</h1>;
  }

  if (boxscoreQuery.isError || !boxscoreQuery.data) {
    return <h1>Error loading boxscore data</h1>;
  }

  const { game } = boxscoreQuery.data;

  return (
    <div className="bg-slate-50 dark:bg-neutral-950">
      <DarkModeToggle />
      {gameSummaryQuery.data && <GameSummary game={gameSummaryQuery.data} />}
      <PlayerTable team={game.homeTeam} />
      <PlayerTable team={game.awayTeam} />
      {/* <InactivePlayers game={game} /> */}
    </div>
  );
};

export default Boxscore;
