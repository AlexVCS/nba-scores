import {formatPlayerNameLink, formatMinutesPlayed} from "@/helpers/helpers.jsx";
import {useQuery} from "@tanstack/react-query";
import {useParams} from "react-router";
// import GameCard from "../GameCard";

export interface Player {
  status: string;
  order: number;
  personId: number;
  jerseyNum: string;
  position: string;
  starter: string;
  oncourt: string;
  played: string;
  statistics: PlayerStatistics;
  name: string;
  nameI: string;
  firstName: string;
  familyName: string;
}
interface PlayerStatistics {
  assists: number;
  blocks: number;
  blocksReceived: number;
  fieldGoalsAttempted: number;
  fieldGoalsMade: number;
  fieldGoalsPercentage: number;
  foulsOffensive: number;
  foulsDrawn: number;
  foulsPersonal: number;
  foulsTechnical: number;
  freeThrowsAttempted: number;
  freeThrowsMade: number;
  freeThrowsPercentage: number;
  minus: number;
  minutes: string;
  minutesCalculated: string;
  plus: number;
  plusMinusPoints: number;
  points: number;
  pointsFastBreak: number;
  pointsInThePaint: number;
  pointsSecondChance: number;
  reboundsDefensive: number;
  reboundsOffensive: number;
  reboundsTotal: number;
  steals: number;
  threePointersAttempted: number;
  threePointersMade: number;
  threePointersPercentage: number;
  turnovers: number;
  twoPointersAttempted: number;
  twoPointersMade: number;
  twoPointersPercentage: number;
}


const getBoxScores = async (gameId: string) => {
  try {
    const baseUrl = import.meta.env.DEV
      ? import.meta.env.VITE_API_URL_DEV
      : import.meta.env.VITE_API_URL_PROD;
    const url = `${baseUrl}/boxscore?gameId=${gameId}`;
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
      {/* <GameCard showScores={showScores} game={gamedata} /> */}
      <div className="pb-4">
        <h1 className="text-lg font-bold">{homeTeam.teamName}</h1>
        <table className="table-fixed">
          <thead>
            <tr>
              <th>Name</th>
              <th>PTS</th>
              <th>REB</th>
              <th>AST</th>
              <th>+/-</th>
              <th>MIN</th>
            </tr>
          </thead>
          {homeTeam.players.map((player: Player) => {
            const nameLinkFormat = formatPlayerNameLink(player);

            return (
              <>
                <tbody>
                  <tr>
                    <td className="pr-2">
                      {" "}
                      <a
                        href={`http://www.nba.com/player/${nameLinkFormat}`}
                        target="_blank"
                        className="text-[#0268d6]"
                      >
                        {player.name}
                      </a>
                    </td>
                    <td>{player.statistics.points}</td>
                    <td>{player.statistics.reboundsTotal}</td>
                    <td>{player.statistics.assists}</td>
                    <td>{player.statistics.plusMinusPoints}</td>
                    <td>
                      {formatMinutesPlayed(player.statistics.minutesCalculated)}
                    </td>
                  </tr>
                </tbody>
              </>
            );
          })}
        </table>
      </div>

      <div>
        <h1 className="text-lg font-bold">{awayTeam.teamName}</h1>
        <table className="table-fixed">
          <thead>
            <tr>
              <th>Name</th>
              <th>PTS</th>
              <th>REB</th>
              <th>AST</th>
              <th>+/-</th>
              <th>MIN</th>
            </tr>
          </thead>
          {awayTeam.players.map((player: Player) => {
            const nameLinkFormat = formatPlayerNameLink(player);
            return (
              <>
                <tbody>
                  <tr>
                    <td className="pr-2">
                      {" "}
                      <a
                        href={`http://www.nba.com/player/${nameLinkFormat}`}
                        target="_blank"
                        className="text-[#0268d6]"
                      >
                        {player.name}
                      </a>
                    </td>
                    <td>{player.statistics.points}</td>
                    <td>{player.statistics.reboundsTotal}</td>
                    <td>{player.statistics.assists}</td>
                    <td>{player.statistics.plusMinusPoints}</td>
                    <td>
                      {formatMinutesPlayed(player.statistics.minutesCalculated)}
                    </td>
                  </tr>
                </tbody>
              </>
            );
          })}
        </table>
      </div>
    </div>
  );
};

export default Boxscore;
