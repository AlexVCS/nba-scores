import {useQuery} from "@tanstack/react-query";
import {useParams} from "react-router";
import {Fragment} from "react";
import {
  formatMinutesPlayed,
  firstNameInitial,
  formatPlayerNameLink,
  Player
} from "@/helpers/helpers.jsx";
// import GameCard from "../GameCard";
import PlayerHeadshot from "@/components/PlayerHeadshot";
import GameSummary from "@/components/GameSummary";

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
    <div>
      <GameSummary game={game} />
      <div className="pb-4">
        <h1 className="text-lg font-bold p-4">{game.homeTeam.teamName}</h1>
        <table className="table-auto ml-2 mr-2">
          <thead>
            <tr className="text-xs">
              <th className="pr-6">PLAYER</th>
              <th className="pr-6">PTS</th>
              <th className="pr-6">REB</th>
              <th className="pr-6">AST</th>
              <th className="pr-6 hidden md:table">+/-</th>
              <th className="pr-6 hidden md:table">MIN</th>
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
                          <span className="hidden md:block">{player.name}</span>
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
                          <td className="border-t pt-2 hidden md:table">
                            {player.statistics.plusMinusPoints}
                          </td>
                          <td className="border-t pt-2 hidden md:table">
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
        <h1 className="text-lg font-bold p-4">{game.awayTeam.teamName}</h1>
        <table className="table-auto">
          <thead>
            <tr className="text-xs">
              <th className="pr-6">PLAYER</th>
              <th className="pr-6">PTS</th>
              <th className="pr-6">REB</th>
              <th className="pr-6">AST</th>
              <th className="pr-6 hidden md:table">+/-</th>
              <th className="pr-6 hidden md:table">MIN</th>
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
                          <span className="hidden md:block">{player.name}</span>
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
                          <td className="border-t pt-2 hidden md:table">
                            {player.statistics.plusMinusPoints}
                          </td>
                          <td className="border-t pt-2 hidden md:table">
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
      <section className="p-2">
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
