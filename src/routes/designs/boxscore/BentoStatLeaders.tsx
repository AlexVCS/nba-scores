import PlayerHeadshot from "@/components/PlayerHeadshot";
import type {Player, Team} from "@/helpers/helpers";

interface BentoStatLeadersProps {
  teams: Team[];
}

type Leader = {
  label: string;
  value: number;
  player: Player;
  teamName: string;
};

function getLeader(
  teams: Team[],
  label: string,
  getValue: (player: Player) => number,
): Leader | null {
  const candidates = teams.flatMap((team) =>
    team.players
      .filter((player) => player.statistics.minutes !== "")
      .map((player) => ({
        label,
        value: getValue(player),
        player,
        teamName: team.teamName,
      })),
  );
  return candidates.sort((a, b) => b.value - a.value)[0] ?? null;
}

function BentoStatLeaders({teams}: BentoStatLeadersProps) {
  const leaders = [
    getLeader(teams, "Points", (player) => player.statistics.points),
    getLeader(teams, "Rebounds", (player) => player.statistics.reboundsTotal),
    getLeader(teams, "Assists", (player) => player.statistics.assists),
  ].filter((leader): leader is Leader => leader !== null);

  return (
    <section className="rounded-[2.5rem] border border-slate-200/70 bg-white p-6 shadow-[0_20px_40px_-15px_rgba(15,118,110,0.12)] dark:border-white/10 dark:bg-zinc-950/75 lg:col-span-5">
      <p className="text-xs font-black uppercase tracking-[0.24em] text-teal-700 dark:text-teal-300">
        Stat leaders
      </p>
      <div className="mt-6 grid gap-4">
        {leaders.map((leader) => (
          <div
            key={leader.label}
            className="grid grid-cols-[auto_1fr_auto] items-center gap-3 border-t border-slate-200 pt-4 first:border-t-0 first:pt-0 dark:border-white/10"
          >
            <PlayerHeadshot player={leader.player} />
            <div className="min-w-0">
              <p className="truncate font-black">
                {leader.player.firstName} {leader.player.familyName}
              </p>
              <p className="truncate text-xs font-bold uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400">
                {leader.label} · {leader.teamName}
              </p>
            </div>
            <p className="font-mono text-3xl font-black tabular-nums text-teal-700 dark:text-teal-300">
              {leader.value}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}

export default BentoStatLeaders;
