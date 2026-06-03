import { useState, useMemo } from 'react';
import { ReactFlow, Controls } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import type { SeriesData } from '@/helpers/helpers';
import { transformToBracketData } from '@/utils/bracketTransformer';
import BracketSeriesNode from './BracketSeriesNode';

const nodeTypes = {
  seriesNode: BracketSeriesNode,
};

interface PlayoffBracketFlowProps {
  playoffPicture: SeriesData[];
  season: string;
}

function PlayoffBracketFlow({ playoffPicture, season }: PlayoffBracketFlowProps) {
  // Reuse spoiler mode pattern from PlayoffBracket.tsx
  const [revealedRounds, setRevealedRounds] = useState<Set<number>>(new Set());
  const [unlockedRounds, setUnlockedRounds] = useState<Set<number>>(new Set());

  // Get unique rounds and sort them
  const rounds = useMemo(
    () => [...new Set(playoffPicture.map(s => s.round))].sort((a, b) => a - b),
    [playoffPicture]
  );

  const revealRound = (round: number) => {
    setRevealedRounds(prev => new Set([...prev, round]));
    const nextRound = rounds[rounds.indexOf(round) + 1];
    if (nextRound !== undefined) {
      setUnlockedRounds(prev => new Set([...prev, nextRound]));
    }
  };

  const hideRound = (round: number) => {
    setRevealedRounds(prev => {
      const next = new Set(prev);
      next.delete(round);
      return next;
    });
  };

  const { nodes, edges } = useMemo(
    () => transformToBracketData(playoffPicture, revealedRounds, season),
    [playoffPicture, revealedRounds, season]
  );

  // Determine which rounds should show reveal buttons
  const canRevealRound = (round: number): boolean => {
    if (round === 1) return true; // Round 1 can always be revealed
    if (round === 2) return revealedRounds.has(1); // Round 2 can be revealed if Round 1 is revealed
    if (round === 3) return revealedRounds.has(2); // Round 3 can be revealed if Round 2 is revealed
    if (round === 4) return revealedRounds.has(3); // Finals can be revealed if Round 3 is revealed
    return false;
  };

  return (
    <>
      {/* Per-round reveal controls */}
      <div className="flex flex-wrap gap-3 mb-6 justify-center">
        {rounds.map(round => {
          const isRevealed = revealedRounds.has(round);
          const canReveal = canRevealRound(round);
          const roundName = playoffPicture.find(s => s.round === round)?.roundName || `Round ${round}`;

          // Don't show button if round can't be revealed yet
          if (!canReveal) return null;

          return (
            <button
              key={round}
              onClick={() => isRevealed ? hideRound(round) : revealRound(round)}
              className={`px-4 py-2 rounded-lg font-medium transition-all duration-200 ${
                isRevealed
                  ? 'bg-green-500 text-white hover:bg-green-600 dark:bg-green-600 dark:hover:bg-green-700'
                  : 'bg-blue-500 text-white hover:bg-blue-600 dark:bg-blue-600 dark:hover:bg-blue-700 shadow-md hover:shadow-lg'
              }`}
            >
              {roundName}: {isRevealed ? 'Hide Results' : 'Reveal Results'}
            </button>
          );
        })}
      </div>

      {/* Bracket visualization */}
      <div className="w-full" style={{ height: '80vh' }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{
            padding: 0.15,
            includeHiddenNodes: false,
          }}
          minZoom={0.3}
          maxZoom={1.5}
          proOptions={{ hideAttribution: true }}
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable={false}
        >
          <Controls
            showInteractive={false}
            position="bottom-right"
            style={{
              background: 'white',
              border: '1px solid #d1d5db',
              borderRadius: '8px',
              boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
              padding: '4px',
              margin: '12px',
              color: '#111',
            }}
          />
        </ReactFlow>
      </div>
    </>
  );
}

export default PlayoffBracketFlow;
