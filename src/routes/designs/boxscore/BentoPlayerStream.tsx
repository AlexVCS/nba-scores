import {memo} from "react";
import {motion, useReducedMotion} from "framer-motion";
import PlayerHeadshot from "@/components/PlayerHeadshot";
import type {Player, Team} from "@/helpers/helpers";

interface BentoPlayerStreamProps {
  teams: Team[];
}

function getTopPlayers(teams: Team[]) {
  return teams
    .flatMap((team) =>
      team.players
        .filter((player) => player.statistics.minutes !== "")
        .map((player) => ({player, teamName: team.teamName})),
    )
    .sort((a, b) => b.player.statistics.points - a.player.statistics.points)
    .slice(0, 8);
}

function PlayerChip({
  player,
  teamName,
}: {
  player: Player;
  teamName: string;
}) {
  return (
    <div className="mr-3 grid w-56 shrink-0 grid-cols-[auto_1fr] items-center gap-3 rounded-[1.5rem] border border-slate-200 bg-slate-50 p-3 dark:border-white/10 dark:bg-white/5">
      <PlayerHeadshot player={player} />
      <div className="min-w-0">
        <p className="truncate font-black">
          {player.firstName} {player.familyName}
        </p>
        <p className="truncate text-xs font-bold uppercase tracking-[0.14em] text-slate-500 dark:text-slate-400">
          {teamName}
        </p>
        <p className="font-mono text-sm font-black text-teal-700 dark:text-teal-300">
          {player.statistics.points} PTS · {player.statistics.reboundsTotal} REB
        </p>
      </div>
    </div>
  );
}

function BentoPlayerStream({teams}: BentoPlayerStreamProps) {
  const prefersReducedMotion = useReducedMotion();
  const players = getTopPlayers(teams);
  const track = [...players, ...players];

  return (
    <section className="overflow-hidden rounded-[2.5rem] border border-slate-200/70 bg-white p-6 shadow-[0_20px_40px_-15px_rgba(15,118,110,0.12)] dark:border-white/10 dark:bg-zinc-950/75 lg:col-span-4">
      <p className="text-xs font-black uppercase tracking-[0.24em] text-teal-700 dark:text-teal-300">
        Player stream
      </p>
      <p className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-300">
        Top contributors drift across the board without changing parent state.
      </p>
      <div className="mt-6 overflow-hidden">
        <motion.div
          className="flex w-max"
          animate={prefersReducedMotion ? undefined : {x: ["0%", "-50%"]}}
          transition={
            prefersReducedMotion
              ? undefined
              : {
                  duration: 24,
                  repeat: Infinity,
                  ease: "linear",
                }
          }
        >
          {track.map(({player, teamName}, index) => (
            <PlayerChip
              key={`${player.personId}-${index}`}
              player={player}
              teamName={teamName}
            />
          ))}
        </motion.div>
      </div>
    </section>
  );
}

export default memo(BentoPlayerStream);
