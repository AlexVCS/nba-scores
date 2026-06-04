import { useState, useMemo, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ReactFlow, Controls, useReactFlow } from '@xyflow/react';
import type { Node, EdgeTypes } from '@xyflow/react';
import { Switch } from '@adobe/react-spectrum';
import '@xyflow/react/dist/style.css';
import type { SeriesData } from '@/helpers/helpers';
import { transformToBracketData } from '@/utils/bracketTransformer';
import type { BracketNodeData } from '@/utils/bracketTransformer';
import { bracketSizing } from '@/utils/bracketSizing';
import { useViewportSize } from '@/hooks/useViewportSize';
import type { ViewportSize } from '@/hooks/useViewportSize';
import BracketSeriesNode from './BracketSeriesNode';
import BracketEdge from './BracketEdge';

function FitOnResize({ viewportSize }: { viewportSize: ViewportSize }) {
  const { fitView } = useReactFlow();
  useEffect(() => {
    fitView({ padding: 0.05, includeHiddenNodes: false });
  }, [viewportSize, fitView]);
  return null;
}

function ConferenceLabelNode({ data }: { data: { label: string } }) {
  return (
    <div
      style={{ transform: 'translateX(-50%)' }}
      className="text-2xl font-bold tracking-wide text-neutral-900 dark:text-neutral-100 select-none pointer-events-none whitespace-nowrap"
    >
      {data.label}
    </div>
  );
}

const nodeTypes = {
  seriesNode: BracketSeriesNode,
  labelNode: ConferenceLabelNode,
};

const edgeTypes: EdgeTypes = {
  bracketEdge: BracketEdge,
};

interface PlayoffBracketFlowProps {
  playoffPicture: SeriesData[];
  season: string;
}

function PlayoffBracketFlow({ playoffPicture, season }: PlayoffBracketFlowProps) {
  const navigate = useNavigate();
  const viewportSize = useViewportSize();
  const sizing = bracketSizing[viewportSize];
  const [revealedRounds, setRevealedRounds] = useState<Set<number>>(new Set());

  // Get unique rounds and sort them
  const rounds = useMemo(
    () => [...new Set(playoffPicture.map(s => s.round))].sort((a, b) => a - b),
    [playoffPicture]
  );

  const revealRound = (round: number) => {
    setRevealedRounds(prev => new Set([...prev, round]));
  };

  const hideRound = (round: number) => {
    setRevealedRounds(prev => {
      const next = new Set(prev);
      for (const r of next) {
        if (r >= round) next.delete(r);
      }
      return next;
    });
  };

  const handleNodeClick = useCallback((_event: React.MouseEvent, node: Node) => {
    if (node.type !== 'seriesNode') return;
    const data = node.data as BracketNodeData;
    navigate(`/playoffs/series/${data.seriesKey}?season=${encodeURIComponent(data.season)}`);
  }, [navigate]);

  const { nodes, edges } = useMemo(
    () => transformToBracketData(playoffPicture, revealedRounds, season, sizing),
    [playoffPicture, revealedRounds, season, sizing]
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
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:flex lg:flex-row lg:flex-wrap lg:justify-center gap-x-8 gap-y-3 mb-6 mx-auto w-fit lg:w-auto justify-items-start">
        {rounds.map(round => {
          const isRevealed = revealedRounds.has(round);
          const canReveal = canRevealRound(round);
          const roundName = playoffPicture.find(s => s.round === round)?.roundName || `Round ${round}`;

          if (!canReveal) return null;

          return (
            <Switch
              key={round}
              isSelected={isRevealed}
              onChange={(selected) => selected ? revealRound(round) : hideRound(round)}
            >
              <div className="dark:text-slate-50 text-neutral-950">
                {isRevealed ? `Hide ${roundName}` : `Show ${roundName}`}
              </div>
            </Switch>
          );
        })}
      </div>

      {/* Bracket visualization */}
      <div className="w-full" style={{ height: sizing.canvasHeight }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          fitView
          fitViewOptions={{
            padding: 0.05,
            includeHiddenNodes: false,
          }}
          minZoom={0.2}
          maxZoom={2}
          proOptions={{ hideAttribution: true }}
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable={false}
          onNodeClick={handleNodeClick}
        >
          <FitOnResize viewportSize={viewportSize} />
          <Controls
            showInteractive={false}
            orientation="horizontal"
            position="top-right"
            style={{
              background: '#1a1a1a',
              border: 'none',
              borderRadius: '8px',
              boxShadow: '0 2px 8px rgba(0,0,0,0.5)',
              padding: '4px',
              margin: '12px',
            }}
          />
        </ReactFlow>
      </div>
    </>
  );
}

export default PlayoffBracketFlow;
