import type {
  BracketEdge,
  BracketGroup,
  BracketGroupKind,
  PlayoffBracketResponse,
  PlayoffFormat,
  RoundDefinition,
  SeriesData,
} from "@/helpers/helpers";

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
    return { id: "finals", label: series.roundName, kind: "finals", sortOrder: 99 };
  }

  // Current team conferences cannot identify historical division membership.
  return { id: "league", label: "League Bracket", kind: "league", sortOrder: 30 };
}

function inferFinalsRound(series: SeriesData[]): number | null {
  const finals = series.filter(item => item.isFinals === true || (
    item.isFinals === undefined && (item.bracketGroupKind === "finals" || /^(?:NBA |BAA )?Finals$/i.test(item.roundName))
  ));
  const rounds = new Set(finals.map(item => item.round));
  return rounds.size === 1 ? finals[0].round : null;
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
  const finalsRound = response.format ? response.format.finalsRound : inferFinalsRound(response.series);
  const format = response.format ?? makeFallbackFormat(response.season, finalsRound);
  const groupsById = new Map<string, BracketGroup>();
  const roundLabels = new Map<number, string>();
  const positions = new Map<string, number>();

  const series = [...response.series]
    .sort((a, b) => a.round - b.round || (a.bracketOrder ?? 0) - (b.bracketOrder ?? 0) || a.seriesKey.localeCompare(b.seriesKey))
    .map((item): RenderSeries => {
      const isFinals = item.isFinals ?? (finalsRound !== null && item.round === finalsRound);
      const roundName = response.rounds?.find(round => round.round === item.round)?.label ?? item.roundName;
      const fallbackGroup = fallbackGroupForSeries({...item, roundName}, isFinals);
      const providedGroup = response.groups?.find(group => group.id === item.bracketGroupId);
      const group: BracketGroup = providedGroup ?? (item.bracketGroupId
        ? {
            id: item.bracketGroupId,
            label: item.bracketGroupLabel ?? fallbackGroup.label,
            kind: item.bracketGroupKind ?? fallbackGroup.kind,
            sortOrder: fallbackGroup.sortOrder,
          }
        : fallbackGroup);

      groupsById.set(group.id, group);
      roundLabels.set(item.round, roundName);

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
        roundName,
      };
    });

  const groups = (response.groups ?? [...groupsById.values()])
    .filter(group => series.some(item => item.bracketGroupId === group.id))
    .sort((a, b) => a.sortOrder - b.sortOrder);

  const rounds = [...(response.rounds ?? [...roundLabels.entries()].map(([round, label]) => ({
    round,
    label,
    sortOrder: round,
    defaultRevealed: round === Math.min(...response.series.map(item => item.round)),
  })))]
    .sort((a, b) => a.sortOrder - b.sortOrder);

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
  if (index === -1) return false;
  if (index === 0) return true;
  return sortedRounds.slice(0, index).every(item => revealedRounds.has(item.round));
}
