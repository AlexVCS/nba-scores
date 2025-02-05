import {useQuery, useInfiniteQuery} from "@tanstack/react-query";
import {format} from "date-fns";
// import {getResults} from "../../server/src"


interface GameData {
  games: {
    gameId: string;
    gameStatus: number;
    gameStatusText: string;
    ifNecessary: boolean;
    seriesGameNumber: string;
    seriesText: string;
    homeTeam: {
      teamName: string;
      teamTricode: string;
      score: number;
    };
    awayTeam: {
      teamName: string;
      teamTricode: string;
      score: number;
    };
  };
}

const Scores = ({searchParams}: URLSearchParams) => {

  const todaysDate = new Date();
  const formattedDate = format(todaysDate, "yyyy-MM-dd")

  const url = `http://localhost:3000/`;
  // console.log(url)

  const getScores = async () => {
    try {
      const response = await fetch(url);
      return response.json();
    } catch (error) {
      console.error(`This call didn't work, this is the ${error}`);
    }
  };

  const {
    isLoading,
    data: games,
    error,
  } = useQuery({
    queryKey: ["games", searchParams],
    queryFn: () => getScores(searchParams),
  });

  if (isLoading) return <h1>Loading...</h1>;
  if (error) return <h1>{JSON.stringify(error)}</h1>;

  return (
    <>
      {games?.map((game: GameData['games']) => {
        return (
            <div key={game.gameId} className="flex justify-center">
              {game.homeTeam.teamTricode}
              {game.homeTeam.score}
           
              {game.awayTeam.teamTricode}
              {game.awayTeam.score}
            </div>
        );
      })}
    </>
  );
};

export default Scores;
