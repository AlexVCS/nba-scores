import { useState, useMemo, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ReactFlow, ReactFlowProvider, useReactFlow, useNodes } from '@xyflow/react';
import type { Node, EdgeTypes } from '@xyflow/react';
import { Switch } from '@adobe/react-spectrum';
import '@xyflow/react/dist/style.css';
import type { PlayoffBracketResponse } from '@/helpers/helpers';
import { transformToBracketData } from '@/utils/bracketTransformer';
import type { BracketNodeData } from '@/utils/bracketTransformer';
import { buildPlayoffBracketModel, canRevealRound as canRevealRoundFromModel } from '@/utils/playoffBracketModel';
import { seasonToYear } from '@/utils/seriesSlug';
import { bracketSizing } from '@/utils/bracketSizing';
import { useViewportSize } from '@/hooks/useViewportSize';
import type { ViewportSize } from '@/hooks/useViewportSize';
import BracketSeriesNode from './BracketSeriesNode';
import BracketEdge from './BracketEdge';
import MobileBracket from './MobileBracket';

interface FitOnResizeProps {
  viewportSize: ViewportSize;
}

function FitOnResize({ viewportSize }: FitOnResizeProps) {
  const { fitView } = useReactFlow();
  const nodes = useNodes();
  useEffect(() => {
    const timer = setTimeout(() => {
      fitView({ padding: 0.05, includeHiddenNodes: false });
    }, 150);
    return () => clearTimeout(timer);
  }, [viewportSize, nodes.length, fitView]);
  return null;
}

const btnStyle: React.CSSProperties = {
  width: 26,
  height: 26,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  background: 'none',
  border: 'none',
  color: '#fff',
  cursor: 'pointer',
  borderRadius: 4,
  padding: 0,
};

function BracketControls() {
  const { zoomIn, zoomOut, fitView } = useReactFlow();
  return (
    <div className="flex justify-end mb-3">
      <div
        style={{
          background: '#1a1a1a',
          borderRadius: 8,
          boxShadow: '0 2px 8px rgba(0,0,0,0.5)',
          padding: 4,
          display: 'flex',
          gap: 2,
        }}
      >
        <button style={btnStyle} onClick={() => zoomIn()} title="Zoom in" aria-label="Zoom in">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="14" height="14" fill="currentColor">
            <path d="M32 18.133H18.133V32h-4.266V18.133H0v-4.266h13.867V0h4.266v13.867H32z" />
          </svg>
        </button>
        <button style={btnStyle} onClick={() => zoomOut()} title="Zoom out" aria-label="Zoom out">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 5" width="14" height="5" fill="currentColor">
            <path d="M0 0h32v4.2H0z" />
          </svg>
        </button>
        <button
          style={btnStyle}
          onClick={() => fitView({ padding: 0.05, includeHiddenNodes: false })}
          title="Fit view"
          aria-label="Fit view"
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 30" width="14" height="14" fill="currentColor">
            <path d="M3.692 4.63c0-.53.4-.938.939-.938h5.215V0H4.708C2.13 0 0 2.054 0 4.63v5.216h3.692V4.63zM27.354 0h-5.2v3.692h5.17c.53 0 .984.4.984.939v5.215H32V4.631A4.624 4.624 0 0027.354 0zm.954 24.83c0 .532-.4.94-.939.94h-5.215V29.5h5.215c2.577 0 4.631-2.054 4.631-4.63v-5.216h-3.692v5.176zm-23.677.94a.938.938 0 01-.939-.94v-5.215H0v5.215c0 2.577 2.054 4.631 4.631 4.631h5.215V25.77H4.631z" />
          </svg>
        </button>
      </div>
    </div>
  );
}

type ConferenceLabelData = {
  label: string;
};

function ConferenceLabelNode({ data }: { data: ConferenceLabelData }) {
  return (
    <div
      className="text-xl font-bold tracking-wide dark:text-slate-50 text-neutral-950 select-none"
      style={{ pointerEvents: 'none', whiteSpace: 'nowrap', transform: 'translateX(-50%)' }}
    >
      {data.label}
    </div>
  );
}

const nodeTypes = {
  seriesNode: BracketSeriesNode,
  conferenceLabel: ConferenceLabelNode,
};

const edgeTypes: EdgeTypes = {
  bracketEdge: BracketEdge,
};

interface PlayoffBracketFlowProps {
  playoffPicture: PlayoffBracketResponse;
}

function PlayoffBracketFlowInner({ playoffPicture }: PlayoffBracketFlowProps) {
  const navigate = useNavigate();
  const viewportSize = useViewportSize();
  const sizing = bracketSizing[viewportSize];
  const [revealedRounds, setRevealedRounds] = useState<Set<number>>(new Set());
  const model = useMemo(() => buildPlayoffBracketModel(playoffPicture), [playoffPicture]);
  const season = model.season;

  const rounds = useMemo(
    () => model.rounds,
    [model.rounds]
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
    navigate(`/playoffs/${seasonToYear(data.season)}/${data.seriesSlug}`);
  }, [navigate]);

  const { nodes, edges } = useMemo(
    () => transformToBracketData(model, revealedRounds, season, sizing),
    [model, revealedRounds, season, sizing]
  );

  const canRevealRound = (round: number): boolean => {
    return canRevealRoundFromModel(round, model.rounds, revealedRounds);
  };

  if (viewportSize === 'sm') {
    return (
      <MobileBracket
        model={model}
        revealedRounds={revealedRounds}
        revealRound={revealRound}
        hideRound={hideRound}
        canRevealRound={canRevealRound}
      />
    );
  }

  return (
    <>
      {/* Per-round reveal controls */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:flex lg:flex-row lg:flex-wrap lg:justify-center gap-x-8 gap-y-3 mb-6 mx-auto w-fit lg:w-auto justify-items-start">
        {rounds.map(roundDef => {
          const round = roundDef.round;
          const isRevealed = revealedRounds.has(round);
          const canReveal = canRevealRound(round);
          const roundName = roundDef.label;

          if (!canReveal) return null;

          return (
            <Switch
              key={round}
              isSelected={isRevealed}
              onChange={(selected) => selected ? revealRound(round) : hideRound(round)}
              UNSAFE_className="origin-left scale-75 sm:scale-100"
            >
              <div className="dark:text-slate-50 text-neutral-950">
                {isRevealed ? `Hide ${roundName}` : `Show ${roundName} Results`}
              </div>
            </Switch>
          );
        })}
      </div>

      {/* Zoom controls in their own row, fully separated from bracket content */}
      <BracketControls />

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
        </ReactFlow>
      </div>
    </>
  );
}

function PlayoffBracketFlow(props: PlayoffBracketFlowProps) {
  return (
    <ReactFlowProvider>
      <PlayoffBracketFlowInner {...props} />
    </ReactFlowProvider>
  );
}

export default PlayoffBracketFlow;
