import {useQuery} from "@tanstack/react-query";
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

const Scores = () => {
  // const [gameData, setGameData] = useState<GameData["games"]>([]);

  // const getScores = async () => {
  //   try {
  //     const response = await fetch("http://localhost:3000/");
  //     // console.log(response)
  //     const result = await response.json();
  //     // console.log(result)
  //     // setGameData(result);
  //   } catch (error) {
  //     console.error(`This call didn't work, this is the ${error}`);
  //   }
  // };

  // const endpoint = "http://localhost:3000/";

  const {
    isLoading,
    data: games,
    error,
  } = useQuery({
    queryKey: ["games"],
    queryFn: async () => {
      const {games} = await fetch("http://localhost:3000/");
      const result = await games.json();
      return result
    },
  });

  if (isLoading) return <h1>Loading...</h1>;
  if (error) return <h1>{JSON.stringify(error)}</h1>;

  {
    console.log(games);
  }
  return (
    <>
      {/* {games?.map((game) => {
        return (
          <>
            <div>{game?.homeTeam.score}</div>
            <div>{game.awayTeam.score}</div>
          </>
        );
      })} */}
    </>
  );
};

export default Scores;
