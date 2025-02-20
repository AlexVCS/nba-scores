import {useQuery} from "@tanstack/react-query";
import {useParams} from "react-router";

const getBoxScores = async (gameId: string) => {
  try {
    const url = `http://localhost:3000/boxscore?gameId=${gameId}`;
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }
    const result = await response.json()
    console.log(result)
    return result
  } catch (error) {
    console.error(`Error fetching boxscore: ${error}`);
    throw error;
  }
};

const Boxscore = () => {
  const params = useParams();
  const gameId = params.gameId ?? "";
  console.log({gameId})
  const {isLoading, data, error} = useQuery({
    queryKey: ["boxscore", gameId],
    queryFn: () => getBoxScores(gameId),
    // enabled: false
  });

  if (isLoading) return <h1>Loading...</h1>;
  if (error) return <h1>{JSON.stringify(error)}</h1>;
  if (!data) return <h1>Didn't receive a boxscore</h1>;
  const {homeTeam, awayTeam} = data;
  return (
    <div>
      <div>{homeTeam.score}</div>
    </div>
  );
};

export default Boxscore;
