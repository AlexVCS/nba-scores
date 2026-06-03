import { Link } from 'react-router-dom';
import TeamLogos from './TeamLogos';
import type { BracketNodeData } from '@/utils/bracketTransformer';

interface BracketSeriesNodeProps {
  data: BracketNodeData;
}

function BracketSeriesNode({ data }: BracketSeriesNodeProps) {
  const { team1, team2, team1Wins, team2Wins, winnerTeamId, isRevealed, seriesKey } = data;

  const team1IsWinner = winnerTeamId === team1.id;
  const team2IsWinner = winnerTeamId === team2.id;

  return (
    <Link
      to={`/playoffs/series/${seriesKey}`}
      className="block border-2 border-gray-400 dark:border-gray-600 rounded-lg bg-white dark:bg-slate-800 hover:border-blue-500 dark:hover:border-blue-400 hover:shadow-lg transition-all duration-200"
      style={{ width: '210px' }}
    >
      {/* Team 1 */}
      <div className="flex items-center justify-between gap-2 p-3 border-b-2 border-gray-300 dark:border-gray-700 bg-gray-50 dark:bg-slate-900">
        <div className="flex items-center gap-2 min-w-0">
          <div className="bg-white rounded p-1 flex-shrink-0">
            <TeamLogos teamName={team1.tricode} teamId={team1.id} size={32} />
          </div>
          <span className="text-base font-semibold truncate text-gray-700 dark:text-slate-200">
            {team1.tricode}
          </span>
        </div>
        {isRevealed && (
          <span className="text-lg font-bold tabular-nums text-gray-700 dark:text-slate-200">
            {team1Wins}
          </span>
        )}
      </div>

      {/* Team 2 */}
      <div className="flex items-center justify-between gap-2 p-3 bg-gray-50 dark:bg-slate-900">
        <div className="flex items-center gap-2 min-w-0">
          <div className="bg-white rounded p-1 flex-shrink-0">
            <TeamLogos teamName={team2.tricode} teamId={team2.id} size={32} />
          </div>
          <span className="text-base font-semibold truncate text-gray-700 dark:text-slate-200">
            {team2.tricode}
          </span>
        </div>
        {isRevealed && (
          <span className="text-lg font-bold tabular-nums text-gray-700 dark:text-slate-200">
            {team2Wins}
          </span>
        )}
      </div>
    </Link>
  );
}

export default BracketSeriesNode;
