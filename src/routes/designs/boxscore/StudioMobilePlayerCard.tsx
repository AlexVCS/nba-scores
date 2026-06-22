import PlayerHeadshot from "@/components/PlayerHeadshot";
import {formatMinutesPlayed, Player} from "@/helpers/helpers";

interface StudioMobilePlayerCardProps {
  player: Player;
}

function StudioMobilePlayerCard({player}: StudioMobilePlayerCardProps) {
  const fullName = `${player.firstName} ${player.familyName}`;
  const didPlay = player.statistics.minutes !== "";
  const playerMeta = [
    player.position,
    player.jerseyNum ? `#${player.jerseyNum}` : "",
  ]
    .filter(Boolean)
    .join(" ");
  const stats = [
    ["PTS", player.statistics.points],
    ["REB", player.statistics.reboundsTotal],
    ["AST", player.statistics.assists],
    ["STL", player.statistics.steals],
    ["BLK", player.statistics.blocks],
    ["TO", player.statistics.turnovers],
    ["+/-", player.statistics.plusMinusPoints],
    ["MIN", formatMinutesPlayed(player.statistics.minutes)],
  ];

  return (
    <article className="rounded-lg border border-slate-200 bg-white/85 p-3 shadow-sm dark:border-white/10 dark:bg-slate-950/55 md:hidden">
      <div className="flex items-center gap-3">
        <PlayerHeadshot player={player} />
        <div className="min-w-0">
          <h4 className="truncate text-base font-black">{fullName}</h4>
          {playerMeta && (
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">
              {playerMeta}
            </p>
          )}
        </div>
      </div>
      {didPlay ? (
        <div className="mt-3 grid grid-cols-4 gap-2">
          {stats.map(([label, value]) => (
            <div
              key={label}
              className="rounded-md border border-slate-200 bg-slate-50 p-2 text-center dark:border-white/10 dark:bg-white/5"
            >
              <p className="text-[10px] font-black uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400">
                {label}
              </p>
              <p className="font-mono text-lg font-black tabular-nums">
                {value}
              </p>
            </div>
          ))}
        </div>
      ) : (
        <p className="mt-3 rounded-md bg-slate-100 px-3 py-2 text-sm font-bold text-slate-600 dark:bg-white/5 dark:text-slate-300">
          {player.comment || "DNP - Coach's Decision"}
        </p>
      )}
    </article>
  );
}

export default StudioMobilePlayerCard;
