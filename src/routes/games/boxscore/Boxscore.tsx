import {useQuery} from "@tanstack/react-query";
import {useParams} from "react-router";
import GameSummary from "@/components/GameSummary";
import DarkModeToggle from "@/components/DarkModeToggle";
import PlayerTable from "./PlayerTable";
import InactivePlayers from "./InactivePlayers";

const getBoxScores = async (gameId: string) => {
  try {
    const baseUrl = import.meta.env.DEV
      ? import.meta.env.VITE_API_URL_DEV
      : import.meta.env.VITE_API_URL_PROD;
    const url = `${baseUrl}/games/${gameId}/boxscore`;
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }
    const result = await response.json();
    return result;
  } catch (error) {
    console.error(`Error fetching boxscore: ${error}`);
    throw error;
  }
};

const Boxscore = () => {
  const params = useParams();
  const gameId = params.gameId ?? "";
  const {isLoading, data, error} = useQuery({
    queryKey: ["boxscore", gameId],
    queryFn: () => getBoxScores(gameId),
  });

  if (isLoading) return <h1>Loading...</h1>;
  if (error) return <h1>{JSON.stringify(error)}</h1>;
  if (!data) return <h1>Didn't receive a boxscore</h1>;
  const {game} = data;

  return (
    <div className="bg-slate-50 dark:bg-neutral-950">
      <DarkModeToggle />
      <GameSummary game={game} />
      <PlayerTable team={game.homeTeam} />
      <PlayerTable team={game.awayTeam} />
      <InactivePlayers game={game} />
    </div>
  );
};

export default Boxscore;
