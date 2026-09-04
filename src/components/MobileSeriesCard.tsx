import {Link} from "react-router-dom";
import type {SeriesData} from "@/helpers/helpers";
import {buildSeriesSlug} from "@/utils/seriesSlug";
import TeamLogos from "./TeamLogos";
import {useBracketSeriesPath} from "./bracketSeriesPath";

interface MobileSeriesCardProps {
  series: SeriesData;
  allSeries: SeriesData[];
  season: string;
  isRevealed: boolean;
}

function MobileSeriesCard({series, allSeries, season, isRevealed}: MobileSeriesCardProps) {
  const buildSeriesPath = useBracketSeriesPath();
  const [team1, team2] = series.teams;
  const team1Wins = series.wins[team1.id] || 0;
  const team2Wins = series.wins[team2.id] || 0;
  const team1IsWinner = series.winnerTeamId === team1.id;
  const team2IsWinner = series.winnerTeamId === team2.id;
  const seriesSlug = buildSeriesSlug(series, allSeries);
  const seriesLength = series.targetWins ? series.targetWins * 2 - 1 : null;
  const accessibleLabel = isRevealed
    ? `${team1.name} ${team1Wins}, ${team2.name} ${team2Wins}. View series details.`
    : `${team1.name} versus ${team2.name}. View series details.`;

  const renderTeam = (team: typeof team1, isWinner: boolean) => (
    <div className={`mobile-series-card__team flex min-w-0 flex-1 flex-col items-center gap-1.5 px-2 py-3 ${isRevealed && isWinner ? "mobile-series-card__team--winner" : ""}`}>
      <div className="mobile-series-card__logo flex size-16 items-center justify-center">
        <TeamLogos teamName={team.tricode} teamId={team.id} size={64} tricode={team.tricode} />
      </div>
      <span className="mobile-series-card__tricode max-w-full truncate text-2xl font-extrabold uppercase leading-none tracking-tight">{team.tricode}</span>
      <span className="mobile-series-card__winner-line h-1 w-8 rounded-full" aria-hidden="true" />
    </div>
  );

  return (
    <Link
      to={buildSeriesPath(season, seriesSlug)}
      className="mobile-series-card block overflow-hidden rounded-lg border"
      aria-label={accessibleLabel}
    >
      {seriesLength && seriesLength !== 7 && (
        <div className="mobile-series-card__format px-3 pt-2.5 text-center text-[10px] font-extrabold uppercase tracking-widest">
          Best of {seriesLength}
        </div>
      )}
      <div className="mobile-series-card__matchup flex min-h-24 items-center justify-between px-2 pb-2" aria-hidden="true">
        {renderTeam(team1, team1IsWinner)}
        <div className={`mobile-series-card__versus flex min-h-11 min-w-11 shrink-0 items-center justify-center rounded-lg px-2 font-extrabold tabular-nums ${isRevealed ? "mobile-series-card__versus--revealed text-xl" : "mobile-series-card__versus--hidden text-xs uppercase tracking-wider"}`}>
          {isRevealed ? `${team1Wins}–${team2Wins}` : "VS"}
        </div>
        {renderTeam(team2, team2IsWinner)}
      </div>
    </Link>
  );
}

export default MobileSeriesCard;
