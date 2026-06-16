import type {
  BracketEdge,
  BracketGroup,
  BracketGroupKind,
  PlayoffBracketResponse,
  PlayoffFormat,
  RoundDefinition,
  SeriesData,
} from "@/helpers/helpers";
import { getTeamConference } from "@/constants/nbaTeams";

export type RenderSeries = SeriesData & {
  bracketGroupId: string;
  bracketGroupLabel: string;
  bracketGroupKind: BracketGroupKind;
  bracketOrder: number;
  targetWins: number | null;
  isFinals: boolean;
};

export type PlayoffBracketModel = {
  season: string;
  format: PlayoffFormat;
  groups: BracketGroup[];
  rounds: RoundDefinition[];
  edges: BracketEdge[];
  series: RenderSeries[];
  fallbackMode: boolean;
};

function playoffYearFromSeason(season: string): number {
  return Number.parseInt(season.split("-")[0], 10) + 1;
}

function makeFallbackFormat(season: string, finalsRound: number | null): PlayoffFormat {
  return {
    era: "unknown",
    playoffYear: playoffYearFromSeason(season),
    finalsRound,
    bracketType: "single-elimination",
    supportsExactBracket: true,
    notes: ["Frontend generated bracket metadata from a legacy response."],
  };
}

function fallbackGroupForSeries(series: SeriesData, isFinals: boolean): BracketGroup {
  if (isFinals) {
    return { id: "finals", label: "NBA Finals", kind: "finals", sortOrder: 99 };
  }

  const conf = getTeamConference(series.teams[0]?.id) ?? getTeamConference(series.teams[1]?.id);
  if (conf === "West") {
    return { id: "west-conference", label: "Western Conference", kind: "conference", sortOrder: 10 };
  }
  if (conf === "East") {
    return { id: "east-conference", label: "Eastern Conference", kind: "conference", sortOrder: 20 };
  }

  return { id: "league", label: "League Bracket", kind: "league", sortOrder: 30 };
}

function inferFinalsRound(series: SeriesData[]): number | null {
  if (series.length === 0) return null;
  const byRound = new Map<number, number>();
  for (const item of series) {
    byRound.set(item.round, (byRound.get(item.round) ?? 0) + 1);
  }
  const maxRound = Math.max(...series.map(item => item.round));
  return byRound.get(maxRound) === 1 ? maxRound : null;
}

function buildFallbackEdges(series: RenderSeries[]): BracketEdge[] {
  return series.flatMap(source => {
    if (!source.winnerTeamId) return [];
    const sourceEnd = source.games.length > 0 ? source.games[source.games.length - 1].date : "";
    const target = series
      .filter(candidate => {
        if (candidate.seriesKey === source.seriesKey) return false;
        if (candidate.round <= source.round) return false;
        if (!candidate.teams.some(team => team.id === source.winnerTeamId)) return false;
        const targetStart = candidate.games.length > 0 ? candidate.games[0].date : "";
        return !sourceEnd || !targetStart || targetStart >= sourceEnd;
      })
      .sort((a, b) => a.round - b.round || a.seriesKey.localeCompare(b.seriesKey))[0];

    if (!target) return [];
    return [{
      sourceSeriesKey: source.seriesKey,
      targetSeriesKey: target.seriesKey,
      winnerTeamId: source.winnerTeamId,
    }];
  });
}

export function buildPlayoffBracketModel(response: PlayoffBracketResponse): PlayoffBracketModel {
  const finalsRound = response.format?.finalsRound ?? inferFinalsRound(response.series);
  const format = response.format ?? makeFallbackFormat(response.season, finalsRound);
  const groupsById = new Map<string, BracketGroup>();
  const roundLabels = new Map<number, string>();
  const positions = new Map<string, number>();

  const series = [...response.series]
    .sort((a, b) => a.round - b.round || (a.bracketOrder ?? 0) - (b.bracketOrder ?? 0) || a.seriesKey.localeCompare(b.seriesKey))
    .map((item): RenderSeries => {
      const isFinals = item.isFinals ?? (finalsRound !== null && item.round === finalsRound);
      const fallbackGroup = fallbackGroupForSeries(item, isFinals);
      const group: BracketGroup = item.bracketGroupId
        ? {
            id: item.bracketGroupId,
            label: item.bracketGroupLabel ?? fallbackGroup.label,
            kind: item.bracketGroupKind ?? fallbackGroup.kind,
            sortOrder: fallbackGroup.sortOrder,
          }
        : fallbackGroup;

      groupsById.set(group.id, response.groups?.find(g => g.id === group.id) ?? group);
      roundLabels.set(item.round, isFinals ? "NBA Finals" : item.roundName);

      const positionKey = `${group.id}-${item.round}`;
      const nextPosition = positions.get(positionKey) ?? 0;
      positions.set(positionKey, nextPosition + 1);

      return {
        ...item,
        bracketGroupId: group.id,
        bracketGroupLabel: group.label,
        bracketGroupKind: group.kind,
        bracketOrder: item.bracketOrder ?? nextPosition,
        targetWins: item.targetWins ?? null,
        isFinals,
        roundName: isFinals ? "NBA Finals" : item.roundName,
      };
    });

  const groups = (response.groups ?? [...groupsById.values()])
    .filter(group => series.some(item => item.bracketGroupId === group.id))
    .sort((a, b) => a.sortOrder - b.sortOrder);

  const rounds = (response.rounds ?? [...roundLabels.entries()].map(([round, label]) => ({
    round,
    label,
    sortOrder: round,
    defaultRevealed: round === Math.min(...response.series.map(item => item.round)),
  }))).sort((a, b) => a.sortOrder - b.sortOrder);

  return {
    season: response.season,
    format,
    groups,
    rounds,
    edges: response.edges ?? buildFallbackEdges(series),
    series,
    fallbackMode: !response.format || !response.groups || !response.rounds || !response.edges,
  };
}

export function canRevealRound(round: number, rounds: RoundDefinition[], revealedRounds: Set<number>): boolean {
  const sortedRounds = [...rounds].sort((a, b) => a.sortOrder - b.sortOrder);
  const index = sortedRounds.findIndex(item => item.round === round);
  if (index <= 0) return true;
  return sortedRounds.slice(0, index).every(item => revealedRounds.has(item.round));
}
