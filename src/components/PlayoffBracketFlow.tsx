import { useState, useMemo, useCallback, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { ReactFlow, ReactFlowProvider, useNodes, useReactFlow } from '@xyflow/react';
import type { Node, EdgeTypes } from '@xyflow/react';
import { Switch } from '@adobe/react-spectrum';
import '@xyflow/react/dist/style.css';
import type { PlayoffBracketResponse } from '@/helpers/helpers';
import { transformToBracketData } from '@/utils/bracketTransformer';
import type { BracketNodeData } from '@/utils/bracketTransformer';
import { buildPlayoffBracketModel, canRevealRound as canRevealRoundFromModel } from '@/utils/playoffBracketModel';
import { useBracketSeriesPath } from './bracketSeriesPath';
import { bracketSizing } from '@/utils/bracketSizing';
import { useViewportSize } from '@/hooks/useViewportSize';
import type { ViewportSize } from '@/hooks/useViewportSize';
import BracketSeriesNode from './BracketSeriesNode';
import BracketEdge from './BracketEdge';
import MobileBracket from './MobileBracket';

interface FitOnResizeProps {
  width: number;
  height: number;
  hasSeriesNodes: boolean;
  fitKey: string;
}

const BRACKET_FIT_OPTIONS = {
  padding: 0.08,
  includeHiddenNodes: false,
} as const;

const FINALS_CLEARANCE = 24;

function FitOnResize({ width, height, hasSeriesNodes, fitKey }: FitOnResizeProps) {
  const { fitView } = useReactFlow();

  useEffect(() => {
    if (width === 0 || height === 0 || !hasSeriesNodes) return;
    const timer = setTimeout(() => {
      fitView({
        ...BRACKET_FIT_OPTIONS,
        duration: 180,
      });
    }, 150);
    return () => clearTimeout(timer);
  }, [width, height, hasSeriesNodes, fitKey, fitView]);
  return null;
}

function LegacyFitOnResize({ viewportSize }: { viewportSize: ViewportSize }) {
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

function BracketControls({ fitFullBracket }: { fitFullBracket: boolean }) {
  const { zoomIn, zoomOut, fitView } = useReactFlow();
  const controlClassName = 'group relative inline-flex size-11 cursor-pointer items-center justify-center rounded-[7px] border-0 bg-transparent text-inherit hover:bg-[#f2e8d2] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#d7a500] dark:hover:bg-[#2b2f28]';
  const controlLabelClassName = 'pointer-events-none absolute right-0 top-[calc(100%+8px)] w-max -translate-y-[3px] whitespace-nowrap rounded-[7px] bg-[#d7a500] px-2 py-1.5 text-[10px] font-extrabold uppercase leading-none tracking-[0.08em] text-[#131210] opacity-0 transition-[opacity,transform] duration-[140ms] ease-in-out group-hover:translate-y-0 group-hover:opacity-100 group-focus-visible:translate-y-0 group-focus-visible:opacity-100';

  return (
    <div className="bracket-controls-row absolute right-3 top-3 z-10" aria-label="Bracket view controls">
      <div className="bracket-controls flex gap-0.5 rounded-lg border border-neutral-300 bg-white p-1 text-neutral-900 shadow-sm dark:border-neutral-700 dark:bg-neutral-950 dark:text-neutral-100">
        <button className={`${controlClassName} bracket-control bracket-control--zoom-in`} type="button" onClick={() => zoomIn()} aria-label="Zoom in">
          <svg aria-hidden="true" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="14" height="14" fill="currentColor">
            <path d="M32 18.133H18.133V32h-4.266V18.133H0v-4.266h13.867V0h4.266v13.867H32z" />
          </svg>
          <span className={`${controlLabelClassName} bracket-control__label`} aria-hidden="true">Zoom in</span>
        </button>
        <button className={`${controlClassName} bracket-control bracket-control--zoom-out`} type="button" onClick={() => zoomOut()} aria-label="Zoom out">
          <svg aria-hidden="true" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 5" width="14" height="5" fill="currentColor">
            <path d="M0 0h32v4.2H0z" />
          </svg>
          <span className={`${controlLabelClassName} bracket-control__label`} aria-hidden="true">Zoom out</span>
        </button>
        <button
          className={`${controlClassName} bracket-control bracket-control--fit`}
          type="button"
          onClick={() => fitView(fitFullBracket
            ? { ...BRACKET_FIT_OPTIONS, duration: 180 }
            : { padding: 0.05, includeHiddenNodes: false })}
          aria-label="Fit bracket to view"
        >
          <svg aria-hidden="true" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 30" width="14" height="14" fill="currentColor">
            <path d="M3.692 4.63c0-.53.4-.938.939-.938h5.215V0H4.708C2.13 0 0 2.054 0 4.63v5.216h3.692V4.63zM27.354 0h-5.2v3.692h5.17c.53 0 .984.4.984.939v5.215H32V4.631A4.624 4.624 0 0027.354 0zm.954 24.83c0 .532-.4.94-.939.94h-5.215V29.5h5.215c2.577 0 4.631-2.054 4.631-4.63v-5.216h-3.692v5.176zm-23.677.94a.938.938 0 01-.939-.94v-5.215H0v5.215c0 2.577 2.054 4.631 4.631 4.631h5.215V25.77H4.631z" />
          </svg>
          <span className={`${controlLabelClassName} bracket-control__label`} aria-hidden="true">Fit bracket</span>
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
      className="bracket-conference-label select-none text-xl font-bold tracking-wide text-neutral-950 dark:text-neutral-50"
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
  fitFullBracket?: boolean;
}

function PlayoffBracketFlowInner({ playoffPicture, fitFullBracket = false }: PlayoffBracketFlowProps) {
  const navigate = useNavigate();
  const buildSeriesPath = useBracketSeriesPath();
  const viewportSize = useViewportSize();
  const canvasRef = useRef<HTMLDivElement>(null);
  const [canvasSize, setCanvasSize] = useState({ width: 0, height: 0 });
  const sizingProfile: ViewportSize = viewportSize === 'sm'
    ? 'sm'
    : canvasSize.width > 0 && canvasSize.width < 1180 ? 'md' : 'lg';
  const useFullBracketFit = fitFullBracket && viewportSize === 'lg';
  const sizing = useMemo(() => {
    const baseSizing = bracketSizing[sizingProfile];
    if (!useFullBracketFit) return baseSizing;

    return {
      ...baseSizing,
      hSpacing: Math.max(
        baseSizing.hSpacing,
        Math.ceil((baseSizing.nodeWidth + baseSizing.finalsNodeWidth) / 2) + FINALS_CLEARANCE,
      ),
    };
  }, [sizingProfile, useFullBracketFit]);
  const [revealedRounds, setRevealedRounds] = useState<Set<number>>(new Set());
  const model = useMemo(() => buildPlayoffBracketModel(playoffPicture), [playoffPicture]);
  const season = model.season;
  const isModernLayout = useMemo(() => {
    const groupIds = new Set(model.groups.map(group => group.id));
    return model.format.era === 'modern-play-in-era'
      && groupIds.has('west-conference')
      && groupIds.has('east-conference')
      && groupIds.has('finals');
  }, [model.format.era, model.groups]);

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
    navigate(buildSeriesPath(data.season, data.seriesSlug));
  }, [navigate, buildSeriesPath]);

  const { nodes, edges } = useMemo(
    () => transformToBracketData(model, revealedRounds, season, sizing),
    [model, revealedRounds, season, sizing]
  );
  const hasSeriesNodes = nodes.some(node => node.type === 'seriesNode');
  const visibleSeriesKey = nodes
    .filter(node => node.type === 'seriesNode')
    .map(node => node.id)
    .sort()
    .join('|');

  const canRevealRound = (round: number): boolean => {
    return canRevealRoundFromModel(round, model.rounds, revealedRounds);
  };

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const updateSize = () => {
      const { width, height } = canvas.getBoundingClientRect();
      setCanvasSize(previous => previous.width === width && previous.height === height
        ? previous
        : { width, height });
    };
    updateSize();

    const observer = new ResizeObserver(updateSize);
    observer.observe(canvas);
    return () => observer.disconnect();
  }, [sizing.canvasHeight]);

  if (viewportSize === 'sm') {
    return (
      <MobileBracket
        model={model}
        revealedRounds={revealedRounds}
        revealRound={revealRound}
        hideRound={hideRound}
        canRevealRound={canRevealRound}
        revealThroughRound={round => {
          const roundIndex = rounds.findIndex(item => item.round === round);
          setRevealedRounds(previous => new Set([
            ...previous,
            ...rounds.slice(0, roundIndex + 1).map(item => item.round),
          ]));
        }}
        showAllResults={() => setRevealedRounds(new Set(rounds.map(round => round.round)))}
        hideAllResults={() => setRevealedRounds(new Set())}
      />
    );
  }

  return (
    <>
      {/* Per-round reveal controls */}
      <div className="bracket-round-controls bracket-stage-controls mx-auto mb-6 grid w-full max-w-6xl grid-cols-2 gap-x-8 gap-y-3 min-[1350px]:grid-cols-4">
        {rounds.map(roundDef => {
          const round = roundDef.round;
          const isRevealed = revealedRounds.has(round);
          const canReveal = canRevealRound(round);
          const roundName = roundDef.label;

          if (!canReveal) {
            return (
              <div
                key={round}
                className="bracket-stage-control bracket-stage-control--locked bracket-round-switch bracket-round-switch--locked"
                role="group"
                aria-disabled="true"
                aria-label={`${roundName} results locked until the previous round is shown`}
              >
                <span className="bracket-round-switch__lock" aria-hidden="true" />
                <span className="bracket-round-switch__label">{roundName}</span>
              </div>
            );
          }

          return (
            <div key={round} className="bracket-stage-control bracket-stage-control--interactive">
              <Switch
                isSelected={isRevealed}
                onChange={(selected) => selected ? revealRound(round) : hideRound(round)}
                UNSAFE_className={`bracket-round-switch ${isRevealed ? 'bracket-round-switch--selected' : 'bracket-round-switch--unselected'}`}
              >
                <div className="bracket-round-switch__label text-neutral-950 dark:text-neutral-50">
                  {isRevealed ? `Hide ${roundName}` : `Show ${roundName} Results`}
                </div>
              </Switch>
            </div>
          );
        })}
      </div>

      {/* Bracket visualization */}
      <div
        ref={canvasRef}
        className={`playoff-bracket-flow bracket-canvas relative w-full ${isModernLayout ? 'bracket-layout--modern' : 'bracket-layout--historical'} ${useFullBracketFit ? 'bracket-canvas--full-fit' : ''}`}
        style={{ height: sizing.canvasHeight }}
      >
        <BracketControls fitFullBracket={useFullBracketFit} />
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          minZoom={0.2}
          maxZoom={2}
          proOptions={{ hideAttribution: true }}
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable={false}
          onNodeClick={handleNodeClick}
        >
          {useFullBracketFit ? (
            <FitOnResize
              width={canvasSize.width}
              height={canvasSize.height}
              hasSeriesNodes={hasSeriesNodes}
              fitKey={`${season}-${sizingProfile}-${visibleSeriesKey}`}
            />
          ) : (
            <LegacyFitOnResize viewportSize={viewportSize} />
          )}
        </ReactFlow>
      </div>
    </>
  );
}

function PlayoffBracketFlow(props: PlayoffBracketFlowProps) {
  return (
    <ReactFlowProvider>
      <PlayoffBracketFlowInner key={props.playoffPicture.season} {...props} />
    </ReactFlowProvider>
  );
}

export default PlayoffBracketFlow;
