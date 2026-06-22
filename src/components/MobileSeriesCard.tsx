import { Link } from 'react-router-dom';
import TeamLogos from './TeamLogos';
import type { SeriesData } from '@/helpers/helpers';
import { buildSeriesSlug, seasonToYear } from '@/utils/seriesSlug';

interface MobileSeriesCardProps {
  series: SeriesData;
  allSeries: SeriesData[];
  season: string;
  isRevealed: boolean;
  seriesRouteBase?: 'production' | 'design';
}

function MobileSeriesCard({ series, allSeries, season, isRevealed, seriesRouteBase = 'production' }: MobileSeriesCardProps) {
  const [team1, team2] = series.teams;
  const team1Wins = series.wins[team1.id] || 0;
  const team2Wins = series.wins[team2.id] || 0;
  const team1IsWinner = series.winnerTeamId === team1.id;
  const team2IsWinner = series.winnerTeamId === team2.id;
  const seriesSlug = buildSeriesSlug(series, allSeries);
  const seriesPath = seriesRouteBase === 'design'
    ? `/designs/playoffz/${seasonToYear(season)}/${seriesSlug}`
    : `/playoffs/${seasonToYear(season)}/${seriesSlug}`;

  const renderRow = (
    team: typeof team1,
    wins: number,
    isWinner: boolean,
    isTopRow: boolean
  ) => (
    <div
      className={`flex items-center justify-between px-3 py-2 bg-gray-900 ${
        isTopRow ? 'border-b-2 border-gray-700' : ''
      }`}
    >
      <div className="flex items-center gap-2 min-w-0">
        <div className="p-0.5 flex-shrink-0">
          <TeamLogos teamName={team.tricode} teamId={team.id} size={28} tricode={team.tricode} />
        </div>
        <span
          className={`font-mono text-base truncate tracking-wider text-amber-500 ${
            isRevealed && isWinner ? 'font-bold' : 'font-semibold'
          }`}
          style={{ textShadow: '0 0 5px rgba(245, 158, 11, 0.7)' }}
        >
          {team.tricode}
        </span>
      </div>
      {isRevealed && (
        <span
          className="font-mono text-base font-bold tabular-nums text-amber-500"
          style={{ textShadow: '0 0 10px rgba(245, 158, 11, 0.7)' }}
        >
          {wins}
        </span>
      )}
    </div>
  );

  return (
    <Link
      to={seriesPath}
      className="block border-2 border-gray-700 rounded-lg overflow-hidden hover:border-blue-400 dark:hover:border-blue-400 transition-colors duration-200"
    >
      {series.targetWins && (
        <div className="px-3 py-1 bg-gray-800 text-[10px] uppercase tracking-widest text-gray-400">
          Best of {series.targetWins * 2 - 1}
        </div>
      )}
      {renderRow(team1, team1Wins, team1IsWinner, true)}
      {renderRow(team2, team2Wins, team2IsWinner, false)}
    </Link>
  );
}

export default MobileSeriesCard;
