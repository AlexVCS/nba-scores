import { Handle, Position } from '@xyflow/react';
import { Link } from 'react-router-dom';
import TeamLogos from './TeamLogos';
import type { BracketNodeData } from '@/utils/bracketTransformer';
import { useBracketSeriesPath } from './bracketSeriesPath';

interface BracketSeriesNodeProps {
  data: BracketNodeData;
}

const HANDLE_STYLE = { background: 'transparent', border: 'none', width: 1, height: 1 };

function BracketSeriesNode({ data }: BracketSeriesNodeProps) {
  const { team1, team2, team1Wins, team2Wins, winnerTeamId, isRevealed, sizing, seriesSlug, season, targetWins } = data;
  const buildSeriesPath = useBracketSeriesPath();

  const team1IsWinner = winnerTeamId === team1.id;
  const team2IsWinner = winnerTeamId === team2.id;

  const renderRow = (team: typeof team1, wins: number, isWinner: boolean, isTopRow: boolean) => {
    const showWinner = isRevealed && isWinner;
    const cornerClass = isTopRow ? 'rounded-t-md' : 'rounded-b-md';
    const rowStateClass = showWinner ? 'bracket-series-row--winner' : 'bracket-series-row--regular';

    return (
      <div
        className={`bracket-series-row ${rowStateClass} flex items-center justify-between ${sizing.rowGapClass} ${sizing.rowPadClass} bg-white dark:bg-neutral-950 ${cornerClass} ${isTopRow ? 'bracket-series-row--top border-b border-neutral-300 dark:border-neutral-700' : 'bracket-series-row--bottom'}`}
      >
        <div className={`bracket-series-team flex items-center ${sizing.rowGapClass} min-w-0`}>
          <div className={`bracket-series-logo flex-shrink-0 ${sizing.logoPadClass}`}>
            <TeamLogos teamName={team.tricode} teamId={team.id} size={sizing.logoSize} tricode={team.tricode} />
          </div>
          <span
            className={`bracket-series-tricode ${sizing.tricodeClass} truncate tracking-wide text-neutral-900 dark:text-neutral-100 ${showWinner ? 'font-bold' : 'font-semibold'}`}
          >
            {team.tricode}
          </span>
        </div>
        <div className={`bracket-series-result flex items-center ${sizing.rowGapClass} flex-shrink-0`}>
          {isRevealed && (
            <span
              className={`bracket-series-score ${sizing.scoreClass} font-bold tabular-nums text-neutral-900 dark:text-neutral-100`}
            >
              {wins}
            </span>
          )}
        </div>
      </div>
    );
  };

  return (
    <div
      className={`bracket-series-node ${data.isFinals ? 'bracket-series-node--finals' : ''} ${isRevealed ? 'bracket-series-node--revealed' : 'bracket-series-node--hidden'}`}
      style={{ width: `${data.displayWidth}px`, position: 'relative' }}
    >
      {/* Source handles: exit from the winner row's outer edge toward the next round */}
      <Handle type="source" position={Position.Right} id="src-right" style={{ ...HANDLE_STYLE, top: '50%' }} />
      <Handle type="source" position={Position.Left} id="src-left" style={{ ...HANDLE_STYLE, top: '50%' }} />
      <Handle type="target" position={Position.Left} id="tgt-left" style={{ ...HANDLE_STYLE, top: '50%' }} />
      <Handle type="target" position={Position.Right} id="tgt-right" style={{ ...HANDLE_STYLE, top: '50%' }} />

      <Link
        to={buildSeriesPath(season, seriesSlug)}
        className={`bracket-series-card nodrag nopan ${isRevealed ? 'bracket-series-card--revealed' : ''} block overflow-hidden rounded-lg border border-neutral-300 bg-white text-neutral-900 shadow-sm transition-colors duration-200 hover:border-neutral-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-500 focus-visible:ring-offset-2 dark:border-neutral-700 dark:bg-neutral-950 dark:text-neutral-100 dark:hover:border-neutral-500 dark:focus-visible:ring-offset-neutral-950`}
        title={targetWins ? `Best of ${targetWins * 2 - 1}` : undefined}
        aria-label={`${team1.tricode} vs ${team2.tricode}: view series games`}
      >
        {renderRow(team1, team1Wins, team1IsWinner, true)}
        {renderRow(team2, team2Wins, team2IsWinner, false)}
      </Link>
    </div>
  );
}

export default BracketSeriesNode;
