import { Player, Team } from "@/helpers/helpers";
import StatsTable from "./StatsTable";

interface PlayerTableProps {
  team: Team;
}
const PlayerTable = ({team}: PlayerTableProps) => {
  return (
    <div className="pb-4">
      <h1 className="text-lg font-bold p-4 text-center md:text-start dark:text-slate-50 text-neutral-950">
        {team.teamName}
      </h1>

      <table className="table-auto ml-2 mr-2 overflow-scroll dark:text-slate-50 text-neutral-950">
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
        {team.players
          .filter((player: Player) => player.comment === "")
          .map((player: Player) => (
            <StatsTable key={player.personId} player={player} />
          ))}
      </table>
    </div>
  );
};

export default PlayerTable