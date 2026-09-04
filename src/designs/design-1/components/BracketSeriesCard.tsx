import {Link} from "react-router-dom";
import TeamLogos from "@/components/TeamLogos";
import type {RenderSeries} from "@/utils/playoffBracketModel";

interface BracketSeriesCardProps {
  series: RenderSeries;
  href: string;
  isRevealed: boolean;
  className?: string;
  showFullNames?: boolean;
}

function BracketSeriesCard({series, href, isRevealed, className = "", showFullNames = false}: BracketSeriesCardProps) {
  const seriesLength = series.targetWins ? series.targetWins * 2 - 1 : null;
  const teamSummary = series.teams.map(team => {
    const wins = series.wins[String(team.id)] ?? 0;
    return isRevealed ? `${team.name} ${wins}` : team.name;
  }).join(isRevealed ? ", " : " versus ");

  return (
    <Link
      to={href}
      className={`group block overflow-hidden rounded-hw border border-hw-line bg-hw-surface text-hw-ink shadow-hw-small transition-[box-shadow,transform] duration-160 ease-out hover:-translate-y-0.5 hover:shadow-hw-card-hover focus-visible:outline-3 focus-visible:outline-offset-3 focus-visible:outline-hw-accent active:translate-y-px motion-reduce:transition-none motion-reduce:hover:translate-y-0 ${className}`}
      aria-label={`${teamSummary}. View series details.`}
    >
      {seriesLength && (showFullNames || seriesLength !== 7) ? (
        <p className="border-b border-hw-line px-3 py-1.5 text-[10px] font-extrabold tracking-[.1em] text-hw-muted uppercase">
          Best of {seriesLength}
        </p>
      ) : null}
      <div aria-hidden="true">
        {series.teams.map(team => {
          const isWinner = isRevealed && series.winnerTeamId === team.id;
          const wins = series.wins[String(team.id)] ?? 0;
          return (
            <div
              key={team.id}
              className={`flex min-h-12 items-center gap-2.5 px-3 py-2 text-hw-muted not-first:border-t not-first:border-hw-line ${isWinner ? "bg-hw-surface-muted text-hw-ink" : ""}`}
            >
              <TeamLogos teamName={team.name} teamId={team.id} size={30} tricode={team.tricode} />
              <span className={showFullNames ? "min-w-0 flex-1 text-xs leading-4 font-extrabold text-hw-ink" : "min-w-0 flex-1 truncate text-xs font-extrabold tracking-[.1em] uppercase"}>
                {showFullNames ? team.name : team.tricode}
              </span>
              {isRevealed ? (
                <span className={`text-base font-extrabold tabular-nums ${isWinner ? "text-hw-accent-ink dark:text-hw-accent" : "text-hw-ink"}`}>
                  {wins}
                </span>
              ) : null}
            </div>
          );
        })}
      </div>
    </Link>
  );
}

export default BracketSeriesCard;
