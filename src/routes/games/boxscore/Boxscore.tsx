import { useQuery } from "@tanstack/react-query";
import { useParams, useSearchParams } from "react-router";
// import GameSummary from "@/components/GameSummary";
import DarkModeToggle from "@/components/DarkModeToggle";
import PlayerTable from "./PlayerTable";
// import InactivePlayers from "./InactivePlayers";
import { getBoxScores } from "@/services/nbaService";

const Boxscore = () => {
  const { gameId = "" } = useParams();
  const [searchParams] = useSearchParams();
  const date = searchParams.get("date") ?? "";

  const boxscoreQuery = useQuery({
    queryKey: ["boxscore", gameId],
    queryFn: () => getBoxScores(gameId),
  });

  // const gamesQuery = useQuery({
  //   queryKey: ["games"],
  //   queryFn: () => getScores(),
  // });

  if (boxscoreQuery.isLoading) {
    return <h1>Loading...</h1>;
  }

  if (boxscoreQuery.isError || !boxscoreQuery.data) {
    return <h1>Error loading boxscore data</h1>;
  }

  // const specificGame = gamesQuery.data?.games.find(
  //   (g: any) => g.gameId === gameId
  // );

  console.log("gameId from URL:", gameId);
console.log("date from URL:", date);
// console.log("gamesQuery.data:", gamesQuery.data);
// console.log("specificGame:", specificGame);

  const { game } = boxscoreQuery.data;

  return (
    <div className="bg-slate-50 dark:bg-neutral-950">
      <DarkModeToggle />
      {/* <GameSummary game={specificGame} /> */}
      <PlayerTable team={game.homeTeam} />
      <PlayerTable team={game.awayTeam} />
      {/* <InactivePlayers game={game} /> */}
    </div>
  );
};

export default Boxscore;