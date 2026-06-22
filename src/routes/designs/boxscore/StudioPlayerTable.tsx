import PlayerHeadshot from "@/components/PlayerHeadshot";
import {
  formatMinutesPlayed,
  formatPlayerNameLink,
  Player,
  Team,
} from "@/helpers/helpers";
import StudioMobilePlayerCard from "./StudioMobilePlayerCard";

interface StudioPlayerTableProps {
  team: Team & {
    teamId?: number;
    teamCity?: string;
    teamTricode?: string;
  };
}

const columns = [
  "PTS",
  "REB",
  "AST",
  "STL",
  "BLK",
  "TO",
  "+/-",
  "MIN",
  "FG",
  "3PT",
  "FT",
  "OREB",
  "DREB",
  "PF",
];

function pct(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

function statValues(player: Player) {
  return [
    player.statistics.points,
    player.statistics.reboundsTotal,
    player.statistics.assists,
    player.statistics.steals,
    player.statistics.blocks,
    player.statistics.turnovers,
    player.statistics.plusMinusPoints,
    formatMinutesPlayed(player.statistics.minutes),
    `${player.statistics.fieldGoalsMade}-${player.statistics.fieldGoalsAttempted} (${pct(player.statistics.fieldGoalsPercentage)})`,
    `${player.statistics.threePointersMade}-${player.statistics.threePointersAttempted} (${pct(player.statistics.threePointersPercentage)})`,
    `${player.statistics.freeThrowsMade}-${player.statistics.freeThrowsAttempted} (${pct(player.statistics.freeThrowsPercentage)})`,
    player.statistics.reboundsOffensive,
    player.statistics.reboundsDefensive,
    player.statistics.foulsPersonal,
  ];
}

function StudioPlayerTable({team}: StudioPlayerTableProps) {
  const activePlayers = team.players.filter((player) => player.comment === "");
  const dnpPlayers = team.players.filter((player) => player.comment !== "");

  return (
    <section className="rounded-lg border border-white/70 bg-white/82 p-3 shadow-xl shadow-cyan-200/20 dark:border-white/10 dark:bg-slate-950/68 dark:shadow-black/25 sm:p-5">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.24em] text-teal-700 dark:text-teal-300">
            Rotation file
          </p>
          <h2 className="text-2xl font-black tracking-tight">
            {team.teamName}
          </h2>
        </div>
        <p className="rounded-full border border-slate-300 px-3 py-1 text-xs font-black uppercase tracking-[0.18em] text-slate-500 dark:border-white/15 dark:text-slate-400">
          {activePlayers.length} active
        </p>
      </div>

      <div className="grid gap-3 md:hidden">
        {activePlayers.map((player) => (
          <StudioMobilePlayerCard key={player.personId} player={player} />
        ))}
      </div>

      <div className="hidden overflow-x-auto md:block">
        <table className="w-full min-w-[1120px] border-separate border-spacing-0 text-sm">
          <thead>
            <tr>
              <th className="sticky left-0 z-10 border-b border-slate-300 bg-white/95 py-3 pr-4 text-left text-xs font-black uppercase tracking-[0.18em] text-slate-500 dark:border-white/10 dark:bg-slate-950 dark:text-slate-400">
                Player
              </th>
              {columns.map((column) => (
                <th
                  key={column}
                  className="border-b border-slate-300 px-3 py-3 text-right text-xs font-black uppercase tracking-[0.12em] text-slate-500 dark:border-white/10 dark:text-slate-400"
                >
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {activePlayers.map((player) => {
              const fullName = `${player.firstName} ${player.familyName}`;
              const playerMeta = [
                player.position,
                player.jerseyNum ? `#${player.jerseyNum}` : "",
              ]
                .filter(Boolean)
                .join(" ");
              const nameLinkFormat = formatPlayerNameLink({
                ...player,
                nameI: fullName,
              });
              return (
                <tr key={player.personId} className="group">
                  <td className="sticky left-0 z-10 border-b border-slate-200 bg-white/95 py-3 pr-4 dark:border-white/10 dark:bg-slate-950">
                    <a
                      href={`http://www.nba.com/player/${nameLinkFormat}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex min-w-64 items-center gap-3 text-sky-700 hover:text-sky-900 dark:text-sky-300 dark:hover:text-sky-100"
                    >
                      <PlayerHeadshot player={player} />
                      <span className="min-w-0">
                        <span className="block truncate font-black">
                          {fullName}
                        </span>
                        {playerMeta && (
                          <span className="text-xs font-bold uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400">
                            {playerMeta}
                          </span>
                        )}
                      </span>
                    </a>
                  </td>
                  {statValues(player).map((value, index) => (
                    <td
                      key={`${player.personId}-${columns[index]}`}
                      className="border-b border-slate-200 px-3 py-3 text-right font-mono font-bold tabular-nums dark:border-white/10"
                    >
                      {value}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {dnpPlayers.length > 0 && (
        <div className="mt-5 rounded-lg border border-dashed border-slate-300 bg-slate-50/75 p-3 dark:border-white/15 dark:bg-white/5">
          <h3 className="mb-2 text-xs font-black uppercase tracking-[0.22em] text-slate-500 dark:text-slate-400">
            Did not play
          </h3>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {dnpPlayers.map((player) => (
              <div
                key={player.personId}
                className="rounded-md bg-white/80 px-3 py-2 text-sm dark:bg-slate-950/55"
              >
                <span className="font-bold">
                  {player.firstName} {player.familyName}
                </span>
                <span className="ml-2 text-slate-500 dark:text-slate-400">
                  {player.comment || "DNP - Coach's Decision"}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

export default StudioPlayerTable;
