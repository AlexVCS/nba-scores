import {useQuery} from "@tanstack/react-query";
import {useParams} from "react-router";
import {Fragment} from "react";
import {
  formatMinutesPlayed,
  firstNameInitial,
  formatPlayerNameLink,
  Player,
} from "@/helpers/helpers.jsx";
// import GameCard from "../GameCard";
import PlayerHeadshot from "@/components/PlayerHeadshot";
import GameSummary from "@/components/GameSummary";
import DarkModeToggle from "@/components/DarkModeToggle";

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
  const {game} = data;

  return (
    <div >
      <DarkModeToggle />
      <GameSummary game={game} />
      <div className="pb-4">
        <h1 className="text-lg font-bold p-4 text-center md:text-start">
          {game.homeTeam.teamName}
        </h1>

        <table className="table-auto ml-2 mr-2 overflow-scroll">
          <thead>
            <tr className="text-xs">
              <th className="pr-[6px]">PLAYER</th>
              <th className="pr-3">PTS</th>
              <th className="pr-3">REB</th>
              <th className="pr-3 hidden lg:table-cell">OREB</th>
              <th className="pr-3 hidden lg:table-cell">DREB</th>
              <th className="pr-3">AST</th>
              <th className="pr-3">TO</th>
              <th className="pr-3">STL</th>
              <th className="pr-3">PF</th>
              <th className="pr-3 hidden md:table-cell">+/-</th>
              <th className="pr-3 hidden md:table-cell">MIN</th>
              <th className="pr-3 hidden md:table-cell">FGM</th>
              <th className="pr-3 hidden md:table-cell">FGA</th>
              <th className="pr-3 hidden md:table-cell">FG%</th>
              <th className="pr-3 hidden md:table-cell">3PM</th>
              <th className="pr-3 hidden md:table-cell">3PA</th>
              <th className="pr-3 hidden md:table-cell">3P%</th>
              <th className="pr-3 hidden md:table-cell">FTM</th>
              <th className="pr-3 hidden md:table-cell">FTA</th>
              <th className="pr-3 hidden md:table-cell">FT%</th>
              <th className="pr-3 hidden lg:table-cell">BLK</th>
            </tr>
          </thead>
          {game.homeTeam.players
            .filter((player: Player) => player.status === "ACTIVE")
            .map((player: Player) => {
              const nameLinkFormat = formatPlayerNameLink(player);

              return (
                <Fragment key={player.personId}>
                  <tbody className="text-sm">
                    <tr>
                      <td className="pr-2 border-t pt-2 whitespace-nowrap">
                        <a
                          href={`http://www.nba.com/player/${nameLinkFormat}`}
                          target="_blank"
                          className="text-[#0268d6]"
                        >
                          <PlayerHeadshot player={player} />
                          <span className="block md:hidden">
                            {firstNameInitial(player.name)}
                          </span>
                          <span className="hidden md:block md:place-self-center">
                            {player.name}
                          </span>
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
                          <td className="border-t pt-2 hidden lg:table-cell">
                            {player.statistics.reboundsOffensive}
                          </td>
                          <td className="border-t pt-2 hidden lg:table-cell">
                            {player.statistics.reboundsDefensive}
                          </td>
                          <td className="border-t pt-2">
                            {player.statistics.assists}
                          </td>
                          <td className="border-t pt-2">
                            {player.statistics.turnovers}
                          </td>
                          <td className="border-t pt-2">
                            {player.statistics.steals}
                          </td>
                          <td className="border-t pt-2">
                            {player.statistics.foulsPersonal}
                          </td>
                          <td className="border-t pt-2 hidden md:table-cell">
                            {player.statistics.plusMinusPoints}
                          </td>
                          <td className="border-t pt-2 hidden md:table-cell">
                            {formatMinutesPlayed(
                              player.statistics.minutesCalculated
                            )}
                          </td>
                          <td className="border-t pt-2 hidden md:table-cell">
                            {player.statistics.fieldGoalsMade}
                          </td>
                          <td className="border-t pt-2 hidden md:table-cell">
                            {player.statistics.fieldGoalsAttempted}
                          </td>
                          <td className="border-t pt-2 hidden md:table-cell">
                            {parseFloat(
                              (
                                player.statistics.fieldGoalsPercentage * 100
                              ).toFixed(1)
                            )}
                          </td>
                          <td className="border-t pt-2 hidden md:table-cell">
                            {player.statistics.threePointersMade}
                          </td>
                          <td className="border-t pt-2 hidden md:table-cell">
                            {player.statistics.threePointersAttempted}
                          </td>
                          <td className="border-t pt-2 hidden md:table-cell">
                            {parseFloat(
                              (
                                player.statistics.threePointersPercentage * 100
                              ).toFixed(1)
                            )}
                          </td>
                          <td className="border-t pt-2 hidden md:table-cell">
                            {player.statistics.freeThrowsMade}
                          </td>
                          <td className="border-t pt-2 hidden md:table-cell">
                            {player.statistics.freeThrowsAttempted}
                          </td>
                          <td className="border-t pt-2 hidden md:table-cell">
                            {parseFloat(
                              (
                                player.statistics.freeThrowsPercentage * 100
                              ).toFixed(1)
                            )}
                          </td>
                          <td className="border-t pt-2 hidden lg:table-cell">
                            {player.statistics.blocks}
                          </td>
                        </>
                      ) : (
                        <td
                          className="border-t pt-2 whitespace-nowrap"
                          colSpan={20}
                        >
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
        <h1 className="text-lg font-bold p-4 text-center md:text-start">
          {game.awayTeam.teamName}
        </h1>
        <table className="table-auto ml-2 mr-2">
          <thead>
            <tr className="text-xs">
              <th className="pr-[6px]">PLAYER</th>
              <th className="pr-3">PTS</th>
              <th className="pr-3">REB</th>
              <th className="pr-3 hidden lg:table-cell">OREB</th>
              <th className="pr-3 hidden lg:table-cell">DREB</th>
              <th className="pr-3">AST</th>
              <th className="pr-3">TO</th>
              <th className="pr-3">STL</th>
              <th className="pr-3">PF</th>
              <th className="pr-3 hidden md:table-cell">+/-</th>
              <th className="pr-3 hidden md:table-cell">MIN</th>
              <th className="pr-3 hidden md:table-cell">FGM</th>
              <th className="pr-3 hidden md:table-cell">FGA</th>
              <th className="pr-3 hidden md:table-cell">FG%</th>
              <th className="pr-3 hidden md:table-cell">3PM</th>
              <th className="pr-3 hidden md:table-cell">3PA</th>
              <th className="pr-3 hidden md:table-cell">3P%</th>
              <th className="pr-3 hidden md:table-cell">FTM</th>
              <th className="pr-3 hidden md:table-cell">FTA</th>
              <th className="pr-3 hidden md:table-cell">FT%</th>
              <th className="pr-3 hidden lg:table-cell">BLK</th>
            </tr>
          </thead>
          {game.awayTeam.players
            .filter((player: Player) => player.status === "ACTIVE")
            .map((player: Player) => {
              const nameLinkFormat = formatPlayerNameLink(player);
              return (
                <Fragment key={player.personId}>
                  <tbody className="text-sm">
                    <tr>
                      <td className="pr-2 border-t pt-2 whitespace-nowrap">
                        <a
                          href={`http://www.nba.com/player/${nameLinkFormat}`}
                          target="_blank"
                          className="text-[#0268d6]"
                        >
                          <PlayerHeadshot player={player} />
                          <span className="block md:hidden">
                            {firstNameInitial(player.name)}
                          </span>
                          <span className="hidden md:block md:place-self-center">
                            {player.name}
                          </span>
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
                          <td className="border-t pt-2 hidden lg:table-cell">
                            {player.statistics.reboundsOffensive}
                          </td>
                          <td className="border-t pt-2 hidden lg:table-cell">
                            {player.statistics.reboundsDefensive}
                          </td>
                          <td className="border-t pt-2">
                            {player.statistics.assists}
                          </td>
                          <td className="border-t pt-2">
                            {player.statistics.turnovers}
                          </td>
                          <td className="border-t pt-2">
                            {player.statistics.steals}
                          </td>
                          <td className="border-t pt-2">
                            {player.statistics.foulsPersonal}
                          </td>
                          <td className="border-t pt-2 hidden md:table-cell">
                            {player.statistics.plusMinusPoints}
                          </td>
                          <td className="border-t pt-2 hidden md:table-cell">
                            {formatMinutesPlayed(
                              player.statistics.minutesCalculated
                            )}
                          </td>
                          <td className="border-t pt-2 hidden md:table-cell">
                            {player.statistics.fieldGoalsMade}
                          </td>
                          <td className="border-t pt-2 hidden md:table-cell">
                            {player.statistics.fieldGoalsAttempted}
                          </td>
                          <td className="border-t pt-2 hidden md:table-cell">
                            {parseFloat(
                              (
                                player.statistics.fieldGoalsPercentage * 100
                              ).toFixed(1)
                            )}
                          </td>
                          <td className="border-t pt-2 hidden md:table-cell">
                            {player.statistics.threePointersMade}
                          </td>
                          <td className="border-t pt-2 hidden md:table-cell">
                            {player.statistics.threePointersAttempted}
                          </td>
                          <td className="border-t pt-2 hidden md:table-cell">
                            {parseFloat(
                              (
                                player.statistics.threePointersPercentage * 100
                              ).toFixed(1)
                            )}
                          </td>
                          <td className="border-t pt-2 hidden md:table-cell">
                            {player.statistics.freeThrowsMade}
                          </td>
                          <td className="border-t pt-2 hidden md:table-cell">
                            {player.statistics.freeThrowsAttempted}
                          </td>
                          <td className="border-t pt-2 hidden md:table-cell">
                            {parseFloat(
                              (
                                player.statistics.freeThrowsPercentage * 100
                              ).toFixed(1)
                            )}
                          </td>
                          <td className="border-t pt-2 hidden lg:table-cell">
                            {player.statistics.blocks}
                          </td>
                        </>
                      ) : (
                        <td
                          className="border-t pt-2 whitespace-nowrap"
                          colSpan={20}
                        >
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
      <section className="p-2 text-sm">
        <div>
          <div className="border-solid border-b border-[#ebe9e7] mb-2">
            <h1 className="uppercase text-lg">Inactive Players</h1>
          </div>
          {game.homeTeam.players.some(
            (player: Player) => player.status === "INACTIVE"
          ) && (
            <p>
              {game.homeTeam.teamTricode}:{" "}
              {game.homeTeam.players
                .filter((player: Player) => player.status === "INACTIVE")
                .map((player: Player) => player.name)
                .join(", ")}
            </p>
          )}
          {game.awayTeam.players.some(
            (player: Player) => player.status === "INACTIVE"
          ) && (
            <p>
              {game.awayTeam.teamTricode}:{" "}
              {game.awayTeam.players
                .filter((player: Player) => player.status === "INACTIVE")
                .map((player: Player) => player.name)
                .join(", ")}{" "}
            </p>
          )}
        </div>
      </section>
    </div>
  );
};

export default Boxscore;
