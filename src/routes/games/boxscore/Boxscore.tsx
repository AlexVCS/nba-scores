import { useQuery } from "@tanstack/react-query";
import { useParams, useSearchParams } from "react-router";
import GameSummary from "@/components/GameSummary";
import DarkModeToggle from "@/components/DarkModeToggle";
import PlayerTable from "./PlayerTable";
import InactivePlayers from "./InactivePlayers";
import { getScores, getBoxScores } from "@/services/nbaService";

const Boxscore = () => {
  const { gameId = "" } = useParams();
  const [searchParams] = useSearchParams();
  const date = searchParams.get("date") ?? "";

  const boxscoreQuery = useQuery({
    queryKey: ["boxscore", gameId],
    queryFn: () => getBoxScores(gameId),
  });

  // Logic Change: Pass the date to the service so getScores 
  // fetches the list containing your gameId.
  const gamesQuery = useQuery({
    queryKey: ["games", date], 
    queryFn: () => getScores(date), // Logic: Fetch the list for that day
    enabled: !!gameId, // Enable based on ID, not existence of date string
  });

  if (boxscoreQuery.isLoading || gamesQuery.isLoading) {
    return <h1>Loading...</h1>;
  }

  // Logic Check: Find the game in the list by ID
  const specificGame = gamesQuery.data?.games?.find(
    (g: any) => g.gameId === gameId
  );

  const { game } = boxscoreQuery.data;

  return (
    <div className="bg-slate-50 dark:bg-neutral-950">
      <DarkModeToggle />
      {/* 
        Logic Check: Ensure specificGame exists, 
        otherwise GameSummary will receive undefined 
      */}
      {specificGame ? (
        <GameSummary game={specificGame} />
      ) : (
        <p>Game details not found in scoreboard data.</p>
      )}
      <PlayerTable team={game.homeTeam} />
      <PlayerTable team={game.awayTeam} />
      <InactivePlayers game={game} />
    </div>
  );
};

export default Boxscore;