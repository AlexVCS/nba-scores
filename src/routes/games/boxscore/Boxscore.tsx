import { formatPlayerNameLink } from "@/helpers/helpers";
import {useQuery} from "@tanstack/react-query";
import {useParams} from "react-router";

const getBoxScores = async (gameId: string) => {
  try {
    const url = `http://localhost:3000/boxscore?gameId=${gameId}`;
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }
    const result = await response.json();
    console.log(result);
    return result;
  } catch (error) {
    console.error(`Error fetching boxscore: ${error}`);
    throw error;
  }
};

const Boxscore = () => {
  const params = useParams();
  const gameId = params.gameId ?? "";
  console.log({gameId});
  const {isLoading, data, error} = useQuery({
    queryKey: ["boxscore", gameId],
    queryFn: () => getBoxScores(gameId),
  });

  if (isLoading) return <h1>Loading...</h1>;
  if (error) return <h1>{JSON.stringify(error)}</h1>;
  if (!data) return <h1>Didn't receive a boxscore</h1>;
  const {homeTeam, awayTeam} = data;
  return (
    <div>
      <div className="text-center">
        {homeTeam.teamName} {homeTeam.score}
      </div>
      {homeTeam.players.map((player) => {
        const nameLinkFormat = formatPlayerNameLink(player)

        return (
          <>
            <div>
              <a
                href={`http://www.nba.com/player/${nameLinkFormat}`}
                target="_blank"
              >
                {player.name}
              </a>{" "}
              PTS {player.statistics.points}
            </div>
          </>
        );
      })}
      <div className="text-center">
        {awayTeam.teamName} {awayTeam.score}
      </div>
      {awayTeam.players.map((player) => {
        const nameLinkFormat = formatPlayerNameLink(player);
        return (
          <>
            <div>
              <a
                href={`http://www.nba.com/player/${nameLinkFormat}`}
                target="_blank"
              >
                {player.name}
              </a>{" "}
              PTS {player.statistics.points}
            </div>
          </>
        );
      })}
    </div>
  );
};

export default Boxscore;
