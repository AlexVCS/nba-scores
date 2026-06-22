import {Link} from "react-router";
import TeamLogos from "@/components/TeamLogos";
import BreathingStatusDot from "@/components/designs/motion/BreathingStatusDot";
import type {RenderSeries} from "@/utils/playoffBracketModel";
import {buildSeriesSlug, seasonToYear} from "@/utils/seriesSlug";

interface TransitSeriesStopProps {
  series: RenderSeries;
  allSeries: RenderSeries[];
  season: string;
  isRevealed: boolean;
}

function TransitSeriesStop({
  series,
  allSeries,
  season,
  isRevealed,
}: TransitSeriesStopProps) {
  const [team1, team2] = series.teams;
  const team1Wins = team1 ? series.wins[team1.id] || 0 : 0;
  const team2Wins = team2 ? series.wins[team2.id] || 0 : 0;
  const seriesSlug = buildSeriesSlug(series, allSeries);

  if (!team1 || !team2) return null;

  return (
    <Link
      to={`/designs/series-feature/${seasonToYear(season)}/${seriesSlug}`}
      className="group relative block rounded-[1.25rem] border border-emerald-200/70 bg-white/85 p-3 shadow-[0_20px_50px_-38px_rgba(16,185,129,0.45)] transition-transform hover:-translate-y-0.5 active:scale-[0.98] dark:border-emerald-300/15 dark:bg-slate-950/70"
    >
      <span className="absolute left-[-18px] top-1/2 hidden h-3 w-3 -translate-y-1/2 rounded-full border-2 border-emerald-600 bg-white dark:bg-slate-950 md:block" />
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-xs font-black uppercase tracking-[0.18em] text-emerald-700 dark:text-emerald-300">
          <BreathingStatusDot tone={isRevealed ? "final" : "scheduled"} />
          <span>{series.roundName}</span>
        </div>
        {series.targetWins && (
          <span className="text-xs font-bold text-slate-500 dark:text-slate-400">
            Best of {series.targetWins * 2 - 1}
          </span>
        )}
      </div>
      {[team1, team2].map((team) => {
        const wins = team.id === team1.id ? team1Wins : team2Wins;
        const isWinner = isRevealed && series.winnerTeamId === team.id;
        return (
          <div
            key={`${series.seriesKey}-${team.id}`}
            className="grid grid-cols-[auto_1fr_auto] items-center gap-3 border-t border-slate-200 py-2 first:border-t-0 dark:border-white/10"
          >
            <TeamLogos
              teamName={team.name}
              teamId={team.id}
              size={30}
              tricode={team.tricode}
            />
            <span
              className={`truncate font-black ${
                isWinner ? "text-emerald-700 dark:text-emerald-300" : ""
              }`}
            >
              {team.tricode}
            </span>
            <span className="font-mono font-black tabular-nums">
              {isRevealed ? wins : "--"}
            </span>
          </div>
        );
      })}
    </Link>
  );
}

export default TransitSeriesStop;
