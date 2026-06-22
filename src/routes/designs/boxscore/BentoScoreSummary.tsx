import TeamLogos from "@/components/TeamLogos";

interface SummaryTeam {
  teamId: number;
  teamTricode: string;
  teamName: string;
  periods: Array<{period: number; score: string}>;
  score: string;
}

interface BentoScoreSummaryProps {
  game: {
    homeTeam: SummaryTeam;
    awayTeam: SummaryTeam;
    period: number;
    gameStatusText: string;
  };
}

function BentoScoreSummary({game}: BentoScoreSummaryProps) {
  const homeScore = Number(game.homeTeam.score);
  const awayScore = Number(game.awayTeam.score);
  const homeWon = homeScore > awayScore;
  const awayWon = awayScore > homeScore;

  return (
    <section className="rounded-[2.5rem] border border-slate-200/70 bg-white p-6 shadow-[0_20px_40px_-15px_rgba(15,118,110,0.12)] dark:border-white/10 dark:bg-zinc-950/75 lg:col-span-7">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.24em] text-teal-700 dark:text-teal-300">
            Score summary
          </p>
          <h2 className="mt-2 text-4xl font-black tracking-tighter">
            {game.gameStatusText}
          </h2>
        </div>
        <div className="rounded-full border border-teal-200 bg-teal-50 px-4 py-2 text-sm font-black uppercase tracking-[0.16em] text-teal-900 dark:border-teal-300/20 dark:bg-teal-300/10 dark:text-teal-100">
          Game file
        </div>
      </div>

      <div className="mt-8 grid gap-5 md:grid-cols-[1fr_auto_1fr] md:items-center">
        {[game.awayTeam, game.homeTeam].map((team) => {
          const isWinner =
            (team.teamId === game.homeTeam.teamId && homeWon) ||
            (team.teamId === game.awayTeam.teamId && awayWon);
          return (
            <div
              key={team.teamId || team.teamTricode}
              className="grid grid-cols-[auto_1fr_auto] items-center gap-4"
            >
              <TeamLogos
                teamName={team.teamName}
                teamId={team.teamId}
                size={64}
                tricode={team.teamTricode}
              />
              <div className="min-w-0">
                <p className="truncate text-3xl font-black tracking-tighter">
                  {team.teamTricode}
                </p>
                <p className="truncate text-xs font-bold uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400">
                  {team.teamName}
                </p>
              </div>
              <p
                className={`font-mono text-5xl font-black tabular-nums ${
                  isWinner ? "text-teal-700 dark:text-teal-300" : ""
                }`}
              >
                {team.score}
              </p>
            </div>
          );
        })}
      </div>
    </section>
  );
}

export default BentoScoreSummary;
