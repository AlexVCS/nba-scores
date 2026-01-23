import PlayerHeadshot from "@/components/PlayerHeadshot";
import {
  firstNameInitial,
  formatMinutesPlayed,
  formatPlayerNameLink,
  Player,
} from "@/helpers/helpers";

interface StatsTableProps {
  player: Player;
}

const StatsTable = ({ player }: StatsTableProps) => {
  const fullName = `${player.firstName} ${player.familyName}`;
  const nameLinkFormat = formatPlayerNameLink({
    ...player,
    nameI: fullName,
  });

  const renderStat = (value: number | string) => (
    <td className="border-t pt-2">{value}</td>
  );

  const renderHiddenStat = (value: number | string, breakpoint: string) => (
    <td
      className={`border-t pt-2 hidden ${breakpoint}:table-cell`}
    >
      {value}
    </td>
  );

  const didPlay = player.statistics.minutes !== "";

  return (
    <>
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
                {firstNameInitial(fullName)}
              </span>
              <span className="hidden md:block md:place-self-center">
                {fullName}
              </span>
            </a>
          </td>
          {didPlay ? (
            <>
              {renderStat(player.statistics.points)}
              {renderStat(player.statistics.reboundsTotal)}
              {renderHiddenStat(player.statistics.reboundsOffensive, "lg")}
              {renderHiddenStat(player.statistics.reboundsDefensive, "lg")}
              {renderStat(player.statistics.assists)}
              {renderStat(player.statistics.turnovers)}
              {renderStat(player.statistics.steals)}
              {renderStat(player.statistics.foulsPersonal)}
              {renderHiddenStat(
                player.statistics.plusMinusPoints,
                "md"
              )}
              {renderHiddenStat(
                formatMinutesPlayed(player.statistics.minutes),
                "md"
              )}
              {renderHiddenStat(player.statistics.fieldGoalsMade, "md")}
              {renderHiddenStat(player.statistics.fieldGoalsAttempted, "md")}
              {renderHiddenStat(
                parseFloat(
                  (
                    player.statistics.fieldGoalsPercentage * 100
                  ).toFixed(1)
                ),
                "md"
              )}
              {renderHiddenStat(player.statistics.threePointersMade, "md")}
              {renderHiddenStat(
                player.statistics.threePointersAttempted,
                "md"
              )}
              {renderHiddenStat(
                parseFloat(
                  (
                    player.statistics.threePointersPercentage * 100
                  ).toFixed(1)
                ),
                "md"
              )}
              {renderHiddenStat(player.statistics.freeThrowsMade, "md")}
              {renderHiddenStat(
                player.statistics.freeThrowsAttempted,
                "md"
              )}
              {renderHiddenStat(
                parseFloat(
                  (player.statistics.freeThrowsPercentage * 100).toFixed(1)
                ),
                "md"
              )}
              {renderHiddenStat(player.statistics.blocks, "lg")}
            </>
          ) : (
            <td
              className="border-t pt-2 whitespace-nowrap"
              colSpan={20}
            >
              {player.comment || "DNP - Coach's Decision"}
            </td>
          )}
        </tr>
      </tbody>
    </>
  );
};

export default StatsTable;