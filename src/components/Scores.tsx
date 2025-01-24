import {useState} from "react";
import {useQuery} from "@tanstack/react-query";
import {getResults} from "../../server/src"



const Scores = () => {
  const [gameData, setGameData] = useState<GameData["games"]>([]);

  // const getScores = async () => {
  //   try {
  //     const response = await fetch("http://localhost:3000/");
  //     const result = await response.json();
  //     // console.log(result)
  //     setGameData(result.games);
  //   } catch (error) {
  //     console.error(`This call didn't work, this is the ${error}`);
  //   }
  // };

  // getScores();

  const endpoint = "http://localhost:3000/";

  const {
    isLoading,
    data: games,
    error,
  } = useQuery({
    queryKey: ["games"],
    queryFn: getResults,
  })

  if (isLoading) return <h1>Loading...</h1>
  if (error) return <h1>{JSON.stringify(error)}</h1>

  {console.log(games)}
  return (
    <>
      hi
      <div>hi</div>
      {/* {games?.map((game) => {
        return (
          <>
            <div>{game?.games.}</div>
            <div>{game.awayTeam.score}</div>
          </>
        );
      })} */}
    </>
  );
};

export default Scores;
