import { Handle, Position } from '@xyflow/react';
import { Link } from 'react-router-dom';
import TeamLogos from './TeamLogos';
import type { BracketNodeData } from '@/utils/bracketTransformer';
import { seasonToYear } from '@/utils/seriesSlug';

interface BracketSeriesNodeProps {
  data: BracketNodeData;
}

const HANDLE_STYLE = { background: 'transparent', border: 'none', width: 1, height: 1 };

function BracketSeriesNode({ data }: BracketSeriesNodeProps) {
  const { team1, team2, team1Wins, team2Wins, winnerTeamId, isRevealed, sizing, seriesSlug, season, targetWins } = data;

  const team1IsWinner = winnerTeamId === team1.id;
  const team2IsWinner = winnerTeamId === team2.id;

  const renderRow = (team: typeof team1, wins: number, isWinner: boolean, isTopRow: boolean) => {
    const showWinner = isRevealed && isWinner;
    const cornerClass = isTopRow ? 'rounded-t-md' : 'rounded-b-md';

    return (
      <div
        className={`flex items-center justify-between ${sizing.rowGapClass} ${sizing.rowPadClass} bg-gray-900 ${cornerClass} ${isTopRow ? 'border-b-2 border-gray-700' : ''}`}
      >
        <div className={`flex items-center ${sizing.rowGapClass} min-w-0`}>
          <div className={`bg-white rounded ${sizing.logoPadClass} flex-shrink-0`}>
            <TeamLogos teamName={team.tricode} teamId={team.id} size={sizing.logoSize} tricode={team.tricode} />
          </div>
          <span
            className={`font-mono ${sizing.tricodeClass} truncate tracking-wider text-amber-500 ${showWinner ? 'font-bold' : 'font-semibold'}`}
            style={{ textShadow: '0 0 5px rgba(245, 158, 11, 0.7)' }}
          >
            {team.tricode}
          </span>
        </div>
        <div className={`flex items-center ${sizing.rowGapClass} flex-shrink-0`}>
          {isRevealed && (
            <span
              className={`font-mono ${sizing.scoreClass} font-bold tabular-nums text-amber-500`}
              style={{ textShadow: '0 0 10px rgba(245, 158, 11, 0.7)' }}
            >
              {wins}
            </span>
          )}
        </div>
      </div>
    );
  };

  return (
    <div style={{ width: `${sizing.nodeWidth}px`, position: 'relative' }}>
      {/* Source handles: exit from the winner row's outer edge toward the next round */}
      <Handle type="source" position={Position.Right} id="src-right" style={{ ...HANDLE_STYLE, top: '50%' }} />
      <Handle type="source" position={Position.Left} id="src-left" style={{ ...HANDLE_STYLE, top: '50%' }} />
      <Handle type="target" position={Position.Left} id="tgt-left" style={{ ...HANDLE_STYLE, top: '50%' }} />
      <Handle type="target" position={Position.Right} id="tgt-right" style={{ ...HANDLE_STYLE, top: '50%' }} />

      <Link
        to={`/playoffs/${seasonToYear(season)}/${seriesSlug}`}
        className="block border-2 border-gray-700 rounded-lg bg-gray-900 overflow-hidden hover:border-blue-500 dark:hover:border-blue-400 hover:shadow-lg transition-all duration-200"
        title={targetWins ? `Best of ${targetWins * 2 - 1}` : undefined}
      >
        {renderRow(team1, team1Wins, team1IsWinner, true)}
        {renderRow(team2, team2Wins, team2IsWinner, false)}
      </Link>
    </div>
  );
}

export default BracketSeriesNode;
