import type { Node, Edge } from '@xyflow/react';
import type { SeriesData, TeamsInSeries, SeriesGame } from '@/helpers/helpers';
import { getTeamConference } from '@/constants/nbaTeams';
import type { BracketSizing } from '@/utils/bracketSizing';
import { buildSeriesSlug } from '@/utils/seriesSlug';

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
  conference: 'East' | 'West' | 'Finals';
  games: SeriesGame[];
  season: string;
  isRevealed: boolean;
  sizing: BracketSizing;
};

type ConferenceGroups = {
  east: SeriesData[];
  west: SeriesData[];
  finals: SeriesData[];
};

/**
 * Groups playoff series by conference (East, West, Finals)
 */
export function groupSeriesByConference(series: SeriesData[]): ConferenceGroups {
  const east: SeriesData[] = [];
  const west: SeriesData[] = [];
  const finals: SeriesData[] = [];

  for (const s of series) {
    // NBA Finals is round 4
    if (s.round === 4) {
      finals.push(s);
      continue;
    }

    // Determine conference by first team's ID
    const team1Conference = getTeamConference(s.teams[0].id);

    if (team1Conference === 'East') {
      east.push(s);
    } else if (team1Conference === 'West') {
      west.push(s);
    } else {
      // Fallback: if we can't determine, try second team
      const team2Conference = getTeamConference(s.teams[1].id);
      if (team2Conference === 'East') {
        east.push(s);
      } else if (team2Conference === 'West') {
        west.push(s);
      }
    }
  }

  return { east, west, finals };
}

/**
 * Calculates the x,y position for a node in the bracket layout.
 * West progresses left→right; East progresses right→left; Finals sits between.
 */
function getNodePosition(
  conference: 'East' | 'West' | 'Finals',
  round: number,
  indexInRound: number,
  hSpacing: number,
  vSpacing: number
): { x: number; y: number } {
  // Calculate Y position
  let y: number;

  if (conference === 'Finals') {
    // Finals sits at the same vertical level as Conference Finals (round 3)
    const confFinalsMultiplier = Math.pow(2, 3 - 1);
    y = (vSpacing * (confFinalsMultiplier - 1)) / 2;
  } else {
    // Each subsequent round has fewer series; space them out and center vs previous round
    const roundMultiplier = Math.pow(2, round - 1);
    y = (indexInRound * vSpacing * roundMultiplier) +
        (vSpacing * (roundMultiplier - 1) / 2);
  }

  // Calculate X position based on conference and round
  // 6 = 3 conference rounds × 2 (mirrored East/West layout)
  const TOTAL_HORIZONTAL_UNITS = 6;
  let x: number;
  const eastRightEdge = hSpacing * TOTAL_HORIZONTAL_UNITS;

  if (conference === 'Finals') {
    x = hSpacing * 3; // midpoint between West Conf Finals (2*hSpacing) and East Conf Finals (4*hSpacing)
  } else if (conference === 'West') {
    x = (round - 1) * hSpacing;
  } else { // East
    x = eastRightEdge - ((round - 1) * hSpacing);
  }

  return { x, y };
}

/**
 * Creates edges connecting series winners to their next round matchups
 */
function createBracketEdges(
  nodes: Node<BracketNodeData>[],
  revealedRounds: Set<number>
): Edge[] {
  const edges: Edge[] = [];

  // Group nodes by conference and round for easier lookup
  const nodesByConference: Record<string, Record<number, Node<BracketNodeData>[]>> = {
    East: {},
    West: {},
    Finals: {}
  };

  nodes.forEach(node => {
    const conf = node.data.conference;
    const round = node.data.round;
    if (!nodesByConference[conf][round]) {
      nodesByConference[conf][round] = [];
    }
    nodesByConference[conf][round].push(node);
  });

  // Create edges for each conference
  ['East', 'West'].forEach(conf => {
    const conferenceNodes = nodesByConference[conf];
    const rounds = Object.keys(conferenceNodes).map(Number).sort((a, b) => a - b);

    rounds.forEach(round => {
      const nextRound = round + 1;
      const currentRoundNodes = conferenceNodes[round] || [];
      const nextRoundNodes = conferenceNodes[nextRound] || [];

      // Sort current round nodes by their Y position to match them correctly
      const sortedCurrentNodes = [...currentRoundNodes].sort((a, b) =>
        a.position.y - b.position.y
      );

      sortedCurrentNodes.forEach((sourceNode, idx) => {
        // Only create edge if the series has a winner and the round is revealed
        if (sourceNode.data.winnerTeamId && revealedRounds.has(round)) {
          // Each pair of series feeds into one series in the next round
          const targetNodeIndex = Math.floor(idx / 2);
          const targetNode = nextRoundNodes[targetNodeIndex];

          if (targetNode) {
            const winnerIsTeam1 = sourceNode.data.winnerTeamId === sourceNode.data.team1.id;
            edges.push({
              id: `e-${sourceNode.id}-${targetNode.id}`,
              source: sourceNode.id,
              sourceHandle: winnerIsTeam1 ? 'src-top' : 'src-bot',
              target: targetNode.id,
              targetHandle: 'tgt',
              animated: false,
              style: {
                stroke: '#f59e0b',
                strokeWidth: 2,
              },
              type: 'bracketEdge',
            });
          }
        }
      });
    });
  });

  // Create edges from Conference Finals to NBA Finals
  const eastConfFinals = nodesByConference.East[3]?.[0];
  const westConfFinals = nodesByConference.West[3]?.[0];
  const finals = nodesByConference.Finals[4]?.[0];

  if (eastConfFinals && finals && eastConfFinals.data.winnerTeamId && revealedRounds.has(3)) {
    const winnerIsTeam1 = eastConfFinals.data.winnerTeamId === eastConfFinals.data.team1.id;
    edges.push({
      id: `e-${eastConfFinals.id}-${finals.id}`,
      source: eastConfFinals.id,
      sourceHandle: winnerIsTeam1 ? 'src-top' : 'src-bot',
      target: finals.id,
      targetHandle: 'tgt-right',
      animated: false,
      style: { stroke: '#f59e0b', strokeWidth: 2 },
      type: 'bracketEdge',
    });
  }

  if (westConfFinals && finals && westConfFinals.data.winnerTeamId && revealedRounds.has(3)) {
    const winnerIsTeam1 = westConfFinals.data.winnerTeamId === westConfFinals.data.team1.id;
    edges.push({
      id: `e-${westConfFinals.id}-${finals.id}`,
      source: westConfFinals.id,
      sourceHandle: winnerIsTeam1 ? 'src-top' : 'src-bot',
      target: finals.id,
      targetHandle: 'tgt-left',
      animated: false,
      style: { stroke: '#f59e0b', strokeWidth: 2 },
      type: 'bracketEdge',
    });
  }

  return edges;
}

/**
 * Determines if a round should be visible based on revealed rounds
 */
function shouldShowRound(round: number, revealedRounds: Set<number>): boolean {
  // Round 1 is always visible
  if (round === 1) return true;

  // Round 2 is visible if Round 1 is revealed
  if (round === 2) return revealedRounds.has(1);

  // Round 3 is visible if Round 2 is revealed
  if (round === 3) return revealedRounds.has(2);

  // Round 4 (Finals) is visible if Round 3 is revealed
  if (round === 4) return revealedRounds.has(3);

  return false;
}

/**
 * Transforms playoff series data into React Flow nodes and edges
 */
export function transformToBracketData(
  playoffSeries: SeriesData[],
  revealedRounds: Set<number>,
  season: string,
  sizing: BracketSizing
): { nodes: Node[]; edges: Edge[] } {
  const { east, west, finals } = groupSeriesByConference(playoffSeries);
  const { hSpacing, vSpacing } = sizing;

  const nodes: Node[] = [];

  // Process East conference series
  const eastByRound: Record<number, SeriesData[]> = {};
  east.forEach(series => {
    if (!eastByRound[series.round]) eastByRound[series.round] = [];
    eastByRound[series.round].push(series);
  });

  Object.entries(eastByRound).forEach(([round, seriesList]) => {
    const roundNum = parseInt(round);
    if (!shouldShowRound(roundNum, revealedRounds)) return;

    seriesList.forEach((series, index) => {
      const [team1, team2] = series.teams;
      const position = getNodePosition('East', roundNum, index, hSpacing, vSpacing);

      nodes.push({
        id: series.seriesKey,
        type: 'seriesNode',
        position,
        data: {
          seriesKey: series.seriesKey,
          seriesSlug: buildSeriesSlug(series, playoffSeries),
          round: series.round,
          roundName: series.roundName,
          team1,
          team2,
          team1Wins: series.wins[team1.id] || 0,
          team2Wins: series.wins[team2.id] || 0,
          winnerTeamId: series.winnerTeamId,
          conference: 'East',
          games: series.games,
          season,
          isRevealed: revealedRounds.has(series.round),
          sizing,
        },
      });
    });
  });

  // Process West conference series
  const westByRound: Record<number, SeriesData[]> = {};
  west.forEach(series => {
    if (!westByRound[series.round]) westByRound[series.round] = [];
    westByRound[series.round].push(series);
  });

  Object.entries(westByRound).forEach(([round, seriesList]) => {
    const roundNum = parseInt(round);
    if (!shouldShowRound(roundNum, revealedRounds)) return;

    seriesList.forEach((series, index) => {
      const [team1, team2] = series.teams;
      const position = getNodePosition('West', roundNum, index, hSpacing, vSpacing);

      nodes.push({
        id: series.seriesKey,
        type: 'seriesNode',
        position,
        data: {
          seriesKey: series.seriesKey,
          seriesSlug: buildSeriesSlug(series, playoffSeries),
          round: series.round,
          roundName: series.roundName,
          team1,
          team2,
          team1Wins: series.wins[team1.id] || 0,
          team2Wins: series.wins[team2.id] || 0,
          winnerTeamId: series.winnerTeamId,
          conference: 'West',
          games: series.games,
          season,
          isRevealed: revealedRounds.has(series.round),
          sizing,
        },
      });
    });
  });

  // Process NBA Finals (round 4) — visible once round 3 is revealed
  if (shouldShowRound(4, revealedRounds)) {
    finals.forEach(series => {
      const [team1, team2] = series.teams;
      const position = getNodePosition('Finals', 4, 0, hSpacing, vSpacing);

      nodes.push({
        id: series.seriesKey,
        type: 'seriesNode',
        position,
        data: {
          seriesKey: series.seriesKey,
          seriesSlug: buildSeriesSlug(series, playoffSeries),
          round: series.round,
          roundName: series.roundName,
          team1,
          team2,
          team1Wins: series.wins[team1.id] || 0,
          team2Wins: series.wins[team2.id] || 0,
          winnerTeamId: series.winnerTeamId,
          conference: 'Finals',
          games: series.games,
          season,
          isRevealed: revealedRounds.has(series.round),
          sizing,
        },
      });
    });
  }

  // Conference label nodes, centered above round 1 columns
  const { nodeWidth } = sizing;
  nodes.push(
    {
      id: 'conf-label-west',
      type: 'conferenceLabel',
      position: { x: nodeWidth / 2, y: -40 },
      data: { label: 'Western Conference' },
      selectable: false,
      draggable: false,
    },
    {
      id: 'conf-label-east',
      type: 'conferenceLabel',
      position: { x: hSpacing * 6 + nodeWidth / 2, y: -40 },
      data: { label: 'Eastern Conference' },
      selectable: false,
      draggable: false,
    }
  );

  const seriesNodes = nodes.filter(n => n.type === 'seriesNode') as Node<BracketNodeData>[];
  const edges = createBracketEdges(seriesNodes, revealedRounds);

  return { nodes, edges };
}
