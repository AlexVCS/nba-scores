import {formatPlayerNameLink, formatMinutesPlayed} from "@/helpers/helpers.jsx";
import {useQuery} from "@tanstack/react-query";
import {useParams} from "react-router";
import { Fragment } from "react";
// import GameCard from "../GameCard";

export interface Player {
  status: string;
  notPlayingReason: string;
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
  const {homeTeam, awayTeam} = data;
  return (
    <div>
      {/* <GameCard showScores={showScores} game={gamedata} /> */}
      <div className="pb-4">
        <h1 className="text-lg font-bold">{homeTeam.teamName}</h1>
        <table className="table-auto">
          <thead>
            <tr>
              <th className="pr-6">Name</th>
              <th className="pr-6">PTS</th>
              <th className="pr-6">REB</th>
              <th className="pr-6">AST</th>
              <th className="pr-6">+/-</th>
              <th className="pr-6">MIN</th>
            </tr>
          </thead>
          {homeTeam.players
            .filter((player: Player) => player.status === "ACTIVE")
            .map((player: Player) => {
              const nameLinkFormat = formatPlayerNameLink(player);
              
              return (
                <Fragment key={player.personId}>
                  <tbody>
                    <tr>
                      <td className="pr-2 border-t pt-2">
                        {" "}
                        <a
                          href={`http://www.nba.com/player/${nameLinkFormat}`}
                          target="_blank"
                          className="text-[#0268d6]"
                        >
                          {player.name}
                        </a>
                      </td>
                      {player.statistics.minutesCalculated !== "PT00M" ? (
                        <>
                          <td className="border-t pt-2">
                            {player.statistics.points}
                          </td>
                          <td className="border-t pt-2">
                            {player.statistics.reboundsTotal}
                          </td>
                          <td className="border-t pt-2">
                            {player.statistics.assists}
                          </td>
                          <td className="border-t pt-2">
                            {player.statistics.plusMinusPoints}
                          </td>
                          <td className="border-t pt-2">
                            {formatMinutesPlayed(
                              player.statistics.minutesCalculated
                            )}
                          </td>
                        </>
                      ) : (
                        <td className="border-t pt-2" colSpan={20}>
                          {player.notPlayingReason
                            ? "DND - Injury/Illness"
                            : "DNP - Coach's Decision"}
                        </td>
                      )}
                    </tr>
                  </tbody>
                </Fragment>
              );
            })}
        </table>
      </div>

      <div className="mb-4">
        <h1 className="text-lg font-bold">{awayTeam.teamName}</h1>
        <table className="table-auto">
          <thead>
            <tr>
              <th className="pr-6">Name</th>
              <th className="pr-6">PTS</th>
              <th className="pr-6">REB</th>
              <th className="pr-6">AST</th>
              <th className="pr-6">+/-</th>
              <th className="pr-6">MIN</th>
            </tr>
          </thead>
          {awayTeam.players
            .filter((player: Player) => player.status === "ACTIVE")
            .map((player: Player) => {
              const nameLinkFormat = formatPlayerNameLink(player);
              return (
                <Fragment key={player.personId}>
                  <tbody>
                    <tr>
                      <td className="pr-2 border-t pt-2">
                        {" "}
                        <a
                          href={`http://www.nba.com/player/${nameLinkFormat}`}
                          target="_blank"
                          className="text-[#0268d6]"
                        >
                          {player.name}
                        </a>
                      </td>
                      {player.statistics.minutesCalculated !== "PT00M" ? (
                        <>
                          <td className="border-t pt-2">
                            {player.statistics.points}
                          </td>
                          <td className="border-t pt-2">
                            {player.statistics.reboundsTotal}
                          </td>
                          <td className="border-t pt-2">
                            {player.statistics.assists}
                          </td>
                          <td className="border-t pt-2">
                            {player.statistics.plusMinusPoints}
                          </td>
                          <td className="border-t pt-2">
                            {formatMinutesPlayed(
                              player.statistics.minutesCalculated
                            )}
                          </td>
                        </>
                      ) : (
                        <td className="border-t pt-2" colSpan={20}>
                          {player.notPlayingReason
                            ? "DND - Injury/Illness"
                            : "DNP - Coach's Decision"}
                        </td>
                      )}
                    </tr>
                  </tbody>
                </Fragment>
              );
            })}
        </table>
      </div>
      <section>
        <div>
          <h1 className="uppercase">Inactive Players</h1>
          <p>
            {homeTeam.teamTricode}:{" "}
            {homeTeam.players
              .filter((player: Player) => player.status === "INACTIVE")
              .map((player: Player) => player.name)
              .join(", ")}
          </p>
          <p>
            {awayTeam.teamTricode}:{" "}
            {awayTeam.players
              .filter((player: Player) => player.status === "INACTIVE")
              .map((player: Player) => player.name)
              .join(", ")}{" "}
          </p>
        </div>
      </section>
    </div>
  );
};

export default Boxscore;
