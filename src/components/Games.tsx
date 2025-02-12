import {useQuery, useInfiniteQuery} from "@tanstack/react-query";
import {format} from "date-fns";
// import {getResults} from "../../server/src"
import GameCard from "./GameCard";

interface GameData {
  games: {
    gameId: string;
    gameCode: string;
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

interface Props {
  searchParams: URLSearchParams;
}

const Games: React.FC<Props> = ({searchParams}) => {
  const getScores = async () => {
    try {
      const dateParam = searchParams.get("date");
      const url = `http://localhost:3000/?date=${dateParam}`;
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
    queryKey: ["games", searchParams.toString()],
    queryFn: () => getScores(),
  });


  if (isLoading) return <h1>Loading...</h1>;
  if (error) return <h1>{JSON.stringify(error)}</h1>;

  return (
    <>
      <GameCard games={games} />
    </>
  );
};

export default Games;
