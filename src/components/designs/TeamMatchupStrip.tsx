import TeamLogos from "@/components/TeamLogos";

interface MatchupTeam {
  teamId: number;
  teamName?: string;
  teamTricode: string;
  score?: number | string;
}

interface TeamMatchupStripProps {
  homeTeam: MatchupTeam;
  awayTeam: MatchupTeam;
  showScores?: boolean;
  compact?: boolean;
  winnerTeamId?: number | null;
  className?: string;
}

function TeamMatchupStrip({
  homeTeam,
  awayTeam,
  showScores = true,
  compact = false,
  winnerTeamId = null,
  className = "",
}: TeamMatchupStripProps) {
  const logoSize = compact ? 38 : 54;

  const renderTeam = (team: MatchupTeam, align: "left" | "right") => {
    const isWinner = winnerTeamId === team.teamId;
    return (
      <div
        className={`flex min-w-0 items-center gap-3 ${
          align === "right" ? "justify-end text-right" : ""
        }`}
      >
        {align === "left" && (
          <TeamLogos
            teamName={team.teamName ?? team.teamTricode}
            teamId={team.teamId}
            size={logoSize}
            tricode={team.teamTricode}
          />
        )}
        <div className="min-w-0">
          <div
            className={`truncate text-lg font-black tracking-tight sm:text-2xl ${
              isWinner ? "text-emerald-600 dark:text-emerald-300" : ""
            }`}
          >
            {team.teamTricode || "TBD"}
          </div>
          <div className="truncate text-xs font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">
            {team.teamName ?? "Team pending"}
          </div>
        </div>
        {align === "right" && (
          <TeamLogos
            teamName={team.teamName ?? team.teamTricode}
            teamId={team.teamId}
            size={logoSize}
            tricode={team.teamTricode}
          />
        )}
      </div>
    );
  };

  return (
    <div
      className={`grid grid-cols-[1fr_auto_1fr] items-center gap-2 sm:gap-5 ${className}`}
    >
      {renderTeam(awayTeam, "left")}
      <div className="flex min-w-16 flex-col items-center rounded-md border border-slate-300 bg-white/70 px-2 py-2 text-center shadow-sm dark:border-white/10 dark:bg-slate-950/60">
        {showScores ? (
          <div className="flex items-center gap-2 font-mono text-xl font-black tabular-nums sm:text-3xl">
            <span>{awayTeam.score ?? "-"}</span>
            <span className="text-slate-400">-</span>
            <span>{homeTeam.score ?? "-"}</span>
          </div>
        ) : (
          <div className="font-mono text-sm font-black uppercase tracking-[0.22em] text-slate-500 dark:text-slate-400">
            VS
          </div>
        )}
      </div>
      {renderTeam(homeTeam, "right")}
    </div>
  );
}

export default TeamMatchupStrip;
