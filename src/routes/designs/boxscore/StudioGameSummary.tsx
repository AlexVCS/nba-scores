import TeamLogos from "@/components/TeamLogos";
import StatusPill from "@/components/designs/StatusPill";

interface SummaryTeam {
  teamId: number;
  teamTricode: string;
  teamName: string;
  periods: Array<{period: number; score: string}>;
  score: string;
}

interface StudioGameSummaryProps {
  game: {
    homeTeam: SummaryTeam;
    awayTeam: SummaryTeam;
    period: number;
    gameStatusText: string;
  };
}

function StudioGameSummary({game}: StudioGameSummaryProps) {
  const homeScore = Number(game.homeTeam.score);
  const awayScore = Number(game.awayTeam.score);
  const homeWon = homeScore > awayScore;
  const awayWon = awayScore > homeScore;
  const periods = game.homeTeam.periods.length
    ? game.homeTeam.periods
    : game.awayTeam.periods;

  return (
    <section className="overflow-hidden rounded-lg border border-white/70 bg-white/82 shadow-2xl shadow-cyan-200/25 dark:border-white/10 dark:bg-slate-950/68 dark:shadow-black/25">
      <div className="grid gap-5 p-5 sm:p-7 lg:grid-cols-[1fr_auto_1fr] lg:items-center">
        <div className="flex items-center gap-4">
          <TeamLogos
            teamName={game.awayTeam.teamName}
            teamId={game.awayTeam.teamId}
            size={72}
            tricode={game.awayTeam.teamTricode}
          />
          <div className="min-w-0">
            <p className="text-xs font-black uppercase tracking-[0.22em] text-slate-500 dark:text-slate-400">
              Away
            </p>
            <h2 className="truncate text-3xl font-black">
              {game.awayTeam.teamTricode}
            </h2>
            <p className="truncate text-sm text-slate-500 dark:text-slate-400">
              {game.awayTeam.teamName}
            </p>
          </div>
          <p
            className={`ml-auto font-mono text-5xl font-black tabular-nums ${
              awayWon ? "text-emerald-600 dark:text-emerald-300" : ""
            }`}
          >
            {game.awayTeam.score}
          </p>
        </div>

        <div className="rounded-lg border border-slate-300 bg-slate-50 px-5 py-4 text-center dark:border-white/10 dark:bg-white/5">
          <StatusPill tone={game.gameStatusText === "Final" ? "final" : "live"}>
            {game.gameStatusText}
          </StatusPill>
          <p className="mt-3 text-xs font-black uppercase tracking-[0.22em] text-slate-500 dark:text-slate-400">
            Boxscore analysis
          </p>
        </div>

        <div className="flex items-center gap-4 lg:justify-end lg:text-right">
          <p
            className={`font-mono text-5xl font-black tabular-nums ${
              homeWon ? "text-emerald-600 dark:text-emerald-300" : ""
            }`}
          >
            {game.homeTeam.score}
          </p>
          <div className="min-w-0">
            <p className="text-xs font-black uppercase tracking-[0.22em] text-slate-500 dark:text-slate-400">
              Home
            </p>
            <h2 className="truncate text-3xl font-black">
              {game.homeTeam.teamTricode}
            </h2>
            <p className="truncate text-sm text-slate-500 dark:text-slate-400">
              {game.homeTeam.teamName}
            </p>
          </div>
          <TeamLogos
            teamName={game.homeTeam.teamName}
            teamId={game.homeTeam.teamId}
            size={72}
            tricode={game.homeTeam.teamTricode}
          />
        </div>
      </div>

      <div className="overflow-x-auto border-t border-slate-200 bg-slate-50/80 p-3 dark:border-white/10 dark:bg-white/5">
        <table className="mx-auto min-w-[520px] text-sm">
          <thead>
            <tr>
              <th className="px-3 py-2 text-left text-xs font-black uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">
                Team
              </th>
              {periods.map((period) => (
                <th
                  key={period.period}
                  className="px-3 py-2 text-center text-xs font-black uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400"
                >
                  {period.period <= 4 ? period.period : `OT${period.period - 4}`}
                </th>
              ))}
              <th className="px-3 py-2 text-center text-xs font-black uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400">
                T
              </th>
            </tr>
          </thead>
          <tbody className="font-mono font-black tabular-nums">
            <tr>
              <td className="px-3 py-2">{game.awayTeam.teamTricode}</td>
              {game.awayTeam.periods.map((period) => (
                <td key={period.period} className="px-3 py-2 text-center">
                  {period.score}
                </td>
              ))}
              <td className="px-3 py-2 text-center">{game.awayTeam.score}</td>
            </tr>
            <tr>
              <td className="px-3 py-2">{game.homeTeam.teamTricode}</td>
              {game.homeTeam.periods.map((period) => (
                <td key={period.period} className="px-3 py-2 text-center">
                  {period.score}
                </td>
              ))}
              <td className="px-3 py-2 text-center">{game.homeTeam.score}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default StudioGameSummary;
