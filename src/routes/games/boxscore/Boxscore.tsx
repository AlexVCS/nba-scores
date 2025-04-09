import {formatPlayerNameLink, formatMinutesPlayed} from "@/helpers/helpers.jsx";
import {useQuery} from "@tanstack/react-query";
import {useParams} from "react-router";
import {Fragment} from "react";
// import GameCard from "../GameCard";
import OvertimeHead from "@/components/Overtime";

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

const getPlayerHeadshots = async (personId: string) => {
  try {
    const baseUrl = import.meta.env.DEV
      ? import.meta.env.VITE_API_URL_DEV
      : import.meta.env.VITE_API_URL_PROD;
    const url = `${baseUrl}/headshots/${personId}`;
    return url;
  } catch (error) {
    console.error(`Error fetching headshot: ${error}`);
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
    <div>
      {/* <GameCard showScores={showScores} game={gamedata} /> */}
      <table className="w-full text-center text-white">
        <thead>
          <tr>
            <th className="text-left pl-3 pr-8"></th>{" "}
            {/* Team column - left aligned with more space */}
            <th className="px-2">1</th>
            <th className="px-2">2</th>
            <th className="px-2">3</th>
            <th className="px-2">4</th>
            <OvertimeHead period={game.period} />
            <th className="px-2">T</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td className="text-left pl-3 pr-8">{game.homeTeam.teamTricode}</td>
            {game.homeTeam.periods.map((period) => (
              <td className="px-2" key={period.period}>
                {period.score}
              </td>
            ))}
            <td className="px-2">{game.homeTeam.score}</td>
          </tr>
          <tr>
            <td className="text-left pl-3 pr-8">{game.awayTeam.teamTricode}</td>
            {game.awayTeam.periods.map((period) => (
              <td className="px-2" key={period.period}>
                {period.score}
              </td>
            ))}
            <td className="px-2">{game.awayTeam.score}</td>
          </tr>
        </tbody>
      </table>
      <div className="pb-4">
        <h1 className="text-lg font-bold">{game.homeTeam.teamName}</h1>
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
          {game.homeTeam.players
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
                          <figure>
                            <img
                              src={`${
                                import.meta.env.DEV
                                  ? import.meta.env.VITE_API_URL_DEV
                                  : import.meta.env.VITE_API_URL_PROD
                              }/headshots/${player.personId}`}
                              alt={`${player.name} headshot`}
                              width="52"
                              height="38"
                              onError={(e) => {
                                // Fallback image if headshot fails to load
                                e.currentTarget.src =
                                  "/placeholder-headshot.png";
                              }}
                            />
                          </figure>
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
        <h1 className="text-lg font-bold">{game.awayTeam.teamName}</h1>
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
          {game.awayTeam.players
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
                          <figure>
                            <img
                              src={`${
                                import.meta.env.DEV
                                  ? import.meta.env.VITE_API_URL_DEV
                                  : import.meta.env.VITE_API_URL_PROD
                              }/headshots/${player.personId}`}
                              alt={`${player.name} headshot`}
                              width="52"
                              height="38"
                              onError={(e) => {
                                // Fallback image if headshot fails to load
                                e.currentTarget.src =
                                  "/placeholder-headshot.png";
                              }}
                            />
                          </figure>
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
            {game.homeTeam.teamTricode}:{" "}
            {game.homeTeam.players
              .filter((player: Player) => player.status === "INACTIVE")
              .map((player: Player) => player.name)
              .join(", ")}
          </p>
          <p>
            {game.awayTeam.teamTricode}:{" "}
            {game.awayTeam.players
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
