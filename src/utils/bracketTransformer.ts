import type { Edge, Node } from '@xyflow/react';
import type { SeriesGame, TeamsInSeries } from '@/helpers/helpers';
import type { BracketSizing } from '@/utils/bracketSizing';
import { buildSeriesSlug } from '@/utils/seriesSlug';
import type { PlayoffBracketModel, RenderSeries } from '@/utils/playoffBracketModel';

export type BracketLane = 'left' | 'right' | 'center';

export type BracketNodeData = {
  seriesKey: string;
  seriesSlug: string;
  round: number;
  roundName: string;
  team1: TeamsInSeries;
  team2: TeamsInSeries;
  team1Wins: number;
  team2Wins: number;
  winnerTeamId: number | null;
  lane: BracketLane;
  bracketGroupId: string;
  bracketGroupLabel: string;
  games: SeriesGame[];
  season: string;
  isRevealed: boolean;
  sizing: BracketSizing;
  targetWins: number | null;
  isFinals: boolean;
  seriesRouteBase: 'production' | 'design';
};

function groupBy<T>(items: T[], getKey: (item: T) => string): Record<string, T[]> {
  return items.reduce<Record<string, T[]>>((acc, item) => {
    const key = getKey(item);
    acc[key] = acc[key] ?? [];
    acc[key].push(item);
    return acc;
  }, {});
}

export function groupSeriesByBracketGroup(model: PlayoffBracketModel): Record<string, RenderSeries[]> {
  return groupBy(model.series, series => series.bracketGroupId);
}

function isModernTwoConferenceModel(model: PlayoffBracketModel): boolean {
  const groupIds = new Set(model.groups.map(group => group.id));
  return groupIds.has('west-conference') && groupIds.has('east-conference') && groupIds.has('finals');
}

function getFinalsRound(model: PlayoffBracketModel): number {
  if (model.format.finalsRound !== null) return model.format.finalsRound;
  if (model.rounds.length === 0) return 1;
  return Math.max(...model.rounds.map(item => item.round));
}

function getModernPosition(
  series: RenderSeries,
  model: PlayoffBracketModel,
  sizing: BracketSizing,
): { position: { x: number; y: number }; lane: BracketLane } {
  const { hSpacing, vSpacing } = sizing;
  const round = series.round;
  const order = series.bracketOrder;
  const lane = series.bracketGroupId.startsWith('east') ? 'right' : series.bracketGroupId.startsWith('west') ? 'left' : 'center';
  const finalsRound = getFinalsRound(model);
  const maxConferenceRound = Math.max(1, finalsRound - 1);
  const rightEdge = hSpacing * maxConferenceRound * 2;

  const multiplier = Math.max(1, Math.pow(2, round - 1));
  const y = series.isFinals
    ? (vSpacing * (Math.pow(2, Math.max(0, maxConferenceRound - 1)) - 1)) / 2
    : (order * vSpacing * multiplier) + ((vSpacing * (multiplier - 1)) / 2);

  if (series.isFinals) {
    return { position: { x: hSpacing * maxConferenceRound, y }, lane: 'center' };
  }
  if (lane === 'right') {
    return { position: { x: rightEdge - ((round - 1) * hSpacing), y }, lane };
  }
  return { position: { x: (round - 1) * hSpacing, y }, lane };
}

function getHistoricalPosition(
  series: RenderSeries,
  model: PlayoffBracketModel,
  sizing: BracketSizing,
): { position: { x: number; y: number }; lane: BracketLane } {
  const { hSpacing, vSpacing } = sizing;
  const nonFinalGroups = model.groups.filter(group => group.kind !== 'finals');
  const groupIndex = Math.max(0, nonFinalGroups.findIndex(group => group.id === series.bracketGroupId));
  const maxRows = Math.max(1, ...nonFinalGroups.map(group => {
    return Math.max(
      1,
      ...model.rounds.map(round => model.series.filter(item => item.bracketGroupId === group.id && item.round === round.round).length),
    );
  }));
  const laneHeight = Math.max(vSpacing * (maxRows + 1), vSpacing * 2);
  const x = (model.rounds.findIndex(round => round.round === series.round)) * hSpacing;

  if (series.isFinals) {
    return {
      position: {
        x,
        y: (nonFinalGroups.length * laneHeight) / 2 - (vSpacing / 2),
      },
      lane: 'center',
    };
  }

  return {
    position: {
      x,
      y: groupIndex * laneHeight + (series.bracketOrder * vSpacing),
    },
    lane: 'center',
  };
}

function shouldShowSeries(series: RenderSeries, model: PlayoffBracketModel, revealedRounds: Set<number>): boolean {
  const roundIndex = model.rounds.findIndex(round => round.round === series.round);
  if (roundIndex <= 0) return true;
  return model.rounds.slice(0, roundIndex).every(round => revealedRounds.has(round.round));
}

function buildNode(
  series: RenderSeries,
  model: PlayoffBracketModel,
  revealedRounds: Set<number>,
  season: string,
  sizing: BracketSizing,
  modernLayout: boolean,
  seriesRouteBase: 'production' | 'design',
): Node<BracketNodeData> | null {
  if (!shouldShowSeries(series, model, revealedRounds)) return null;
  const [team1, team2] = series.teams;
  if (!team1 || !team2) return null;
  const { position, lane } = modernLayout
    ? getModernPosition(series, model, sizing)
    : getHistoricalPosition(series, model, sizing);

  return {
    id: series.seriesKey,
    type: 'seriesNode',
    position,
    data: {
      seriesKey: series.seriesKey,
      seriesSlug: buildSeriesSlug(series, model.series),
      round: series.round,
      roundName: series.roundName,
      team1,
      team2,
      team1Wins: series.wins[team1.id] || 0,
      team2Wins: series.wins[team2.id] || 0,
      winnerTeamId: series.winnerTeamId,
      lane,
      bracketGroupId: series.bracketGroupId,
      bracketGroupLabel: series.bracketGroupLabel,
      games: series.games,
      season,
      isRevealed: revealedRounds.has(series.round),
      sizing,
      targetWins: series.targetWins,
      isFinals: series.isFinals,
      seriesRouteBase,
    },
  };
}

function createBracketEdges(
  nodes: Node<BracketNodeData>[],
  model: PlayoffBracketModel,
  revealedRounds: Set<number>,
): Edge[] {
  const nodeIds = new Set(nodes.map(node => node.id));
  const seriesByKey = new Map(model.series.map(series => [series.seriesKey, series]));

  if (!model.format.supportsExactBracket && model.edges.length === 0) {
    return [];
  }

  return model.edges.flatMap(edge => {
    const source = seriesByKey.get(edge.sourceSeriesKey);
    const target = seriesByKey.get(edge.targetSeriesKey);
    if (!source || !target) return [];
    if (!nodeIds.has(source.seriesKey) || !nodeIds.has(target.seriesKey)) return [];
    if (!source.winnerTeamId || !revealedRounds.has(source.round)) return [];

    const sourceLane = nodes.find(node => node.id === source.seriesKey)?.data.lane ?? 'center';
    const targetLane = nodes.find(node => node.id === target.seriesKey)?.data.lane ?? 'center';
    const sourceHandle = sourceLane === 'right' ? 'src-left' : 'src-right';
    const targetHandle = targetLane === 'right' ? 'tgt-right' : 'tgt-left';

    return [{
      id: `e-${source.seriesKey}-${target.seriesKey}`,
      source: source.seriesKey,
      sourceHandle,
      target: target.seriesKey,
      targetHandle,
      animated: false,
      style: {
        stroke: '#f59e0b',
        strokeWidth: 2,
      },
      type: 'bracketEdge',
    }];
  });
}

function createGroupLabels(
  model: PlayoffBracketModel,
  sizing: BracketSizing,
  modernLayout: boolean,
): Node[] {
  const { hSpacing, nodeWidth, vSpacing } = sizing;
  if (modernLayout) {
    const finalsRound = getFinalsRound(model);
    const maxConferenceRound = Math.max(1, finalsRound - 1);
    return [
      {
        id: 'group-label-west',
        type: 'conferenceLabel',
        position: { x: nodeWidth / 2, y: -40 },
        data: { label: 'Western Conference' },
        selectable: false,
        draggable: false,
      },
      {
        id: 'group-label-east',
        type: 'conferenceLabel',
        position: { x: hSpacing * maxConferenceRound * 2 + nodeWidth / 2, y: -40 },
        data: { label: 'Eastern Conference' },
        selectable: false,
        draggable: false,
      },
    ];
  }

  const nonFinalGroups = model.groups.filter(group => group.kind !== 'finals');
  const maxRows = Math.max(1, ...nonFinalGroups.map(group => {
    return Math.max(
      1,
      ...model.rounds.map(round => model.series.filter(item => item.bracketGroupId === group.id && item.round === round.round).length),
    );
  }));
  const laneHeight = Math.max(vSpacing * (maxRows + 1), vSpacing * 2);

  return nonFinalGroups.map((group, index) => ({
    id: `group-label-${group.id}`,
    type: 'conferenceLabel',
    position: { x: nodeWidth / 2, y: index * laneHeight - 40 },
    data: { label: group.label },
    selectable: false,
    draggable: false,
  }));
}

export function transformToBracketData(
  model: PlayoffBracketModel,
  revealedRounds: Set<number>,
  season: string,
  sizing: BracketSizing,
  seriesRouteBase: 'production' | 'design' = 'production',
): { nodes: Node[]; edges: Edge[] } {
  const modernLayout = isModernTwoConferenceModel(model);
  const seriesNodes = model.series
    .map(series => buildNode(series, model, revealedRounds, season, sizing, modernLayout, seriesRouteBase))
    .filter((node): node is Node<BracketNodeData> => node !== null);
  const labelNodes = createGroupLabels(model, sizing, modernLayout);
  const edges = createBracketEdges(seriesNodes, model, revealedRounds);

  return { nodes: [...seriesNodes, ...labelNodes], edges };
}
