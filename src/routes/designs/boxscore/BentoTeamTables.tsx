import PlayerHeadshot from "@/components/PlayerHeadshot";
import {formatMinutesPlayed, Player, Team} from "@/helpers/helpers";

interface BentoTeamTablesProps {
  teams: Team[];
}

const compactStats = ["PTS", "REB", "AST", "STL", "BLK", "TO", "+/-", "MIN"];

function values(player: Player) {
  return [
    player.statistics.points,
    player.statistics.reboundsTotal,
    player.statistics.assists,
    player.statistics.steals,
    player.statistics.blocks,
    player.statistics.turnovers,
    player.statistics.plusMinusPoints,
    formatMinutesPlayed(player.statistics.minutes),
  ];
}

function BentoTeamTables({teams}: BentoTeamTablesProps) {
  return (
    <section className="rounded-[2.5rem] border border-slate-200/70 bg-white p-6 shadow-[0_20px_40px_-15px_rgba(15,118,110,0.12)] dark:border-white/10 dark:bg-zinc-950/75 lg:col-span-8">
      <p className="text-xs font-black uppercase tracking-[0.24em] text-teal-700 dark:text-teal-300">
        Team tables
      </p>
      <div className="mt-6 grid gap-8">
        {teams.map((team) => {
          const activePlayers = team.players.filter((player) => player.comment === "");
          const dnpPlayers = team.players.filter((player) => player.comment !== "");
          return (
            <div key={team.teamName}>
              <div className="mb-3 flex items-end justify-between gap-3">
                <h3 className="text-2xl font-black tracking-tighter">
                  {team.teamName}
                </h3>
                <p className="text-xs font-black uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400">
                  {activePlayers.length} active
                </p>
              </div>

              <div className="grid gap-3 md:hidden">
                {activePlayers.map((player) => (
                  <article
                    key={player.personId}
                    className="rounded-[1.5rem] border border-slate-200 bg-slate-50 p-3 dark:border-white/10 dark:bg-white/5"
                  >
                    <div className="flex items-center gap-3">
                      <PlayerHeadshot player={player} />
                      <div className="min-w-0">
                        <p className="truncate font-black">
                          {player.firstName} {player.familyName}
                        </p>
                        {player.position && (
                          <p className="text-xs font-bold uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400">
                            {player.position}
                          </p>
                        )}
                      </div>
                    </div>
                    <div className="mt-3 grid grid-cols-4 gap-2">
                      {compactStats.map((stat, index) => (
                        <div key={stat} className="text-center">
                          <p className="text-[10px] font-black uppercase tracking-[0.12em] text-slate-500 dark:text-slate-400">
                            {stat}
                          </p>
                          <p className="font-mono font-black tabular-nums">
                            {values(player)[index]}
                          </p>
                        </div>
                      ))}
                    </div>
                  </article>
                ))}
              </div>

              <div className="hidden overflow-x-auto md:block">
                <table className="w-full min-w-[760px] text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 dark:border-white/10">
                      <th className="py-3 pr-3 text-left text-xs font-black uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400">
                        Player
                      </th>
                      {compactStats.map((stat) => (
                        <th
                          key={stat}
                          className="px-3 py-3 text-right text-xs font-black uppercase tracking-[0.12em] text-slate-500 dark:text-slate-400"
                        >
                          {stat}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {activePlayers.map((player) => (
                      <tr
                        key={player.personId}
                        className="border-b border-slate-100 dark:border-white/10"
                      >
                        <td className="py-3 pr-3">
                          <div className="flex min-w-56 items-center gap-3">
                            <PlayerHeadshot player={player} />
                            <span className="min-w-0">
                              <span className="block truncate font-black">
                                {player.firstName} {player.familyName}
                              </span>
                              {player.position && (
                                <span className="text-xs font-bold uppercase tracking-[0.14em] text-slate-500 dark:text-slate-400">
                                  {player.position}
                                </span>
                              )}
                            </span>
                          </div>
                        </td>
                        {values(player).map((value, index) => (
                          <td
                            key={`${player.personId}-${compactStats[index]}`}
                            className="px-3 py-3 text-right font-mono font-black tabular-nums"
                          >
                            {value}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {dnpPlayers.length > 0 && (
                <div className="mt-4 rounded-[1.5rem] border border-dashed border-slate-300 bg-slate-50 p-3 dark:border-white/15 dark:bg-white/5">
                  <p className="text-xs font-black uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">
                    Did not play
                  </p>
                  <div className="mt-2 grid gap-2 sm:grid-cols-2">
                    {dnpPlayers.map((player) => (
                      <p key={player.personId} className="text-sm">
                        <span className="font-bold">
                          {player.firstName} {player.familyName}
                        </span>
                        <span className="ml-2 text-slate-500 dark:text-slate-400">
                          {player.comment || "DNP - Coach's Decision"}
                        </span>
                      </p>
                    ))}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}

export default BentoTeamTables;
