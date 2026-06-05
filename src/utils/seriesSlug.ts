import { getTeamConference } from '@/constants/nbaTeams';
import type { SeriesData } from '@/helpers/helpers';

const ROUND_SLUGS: Record<number, string> = {
  1: 'first-round',
  2: 'semifinal',
  3: 'final',
};

function getSeriesConference(series: SeriesData): 'east' | 'west' {
  const conf = getTeamConference(series.teams[0].id) ?? getTeamConference(series.teams[1].id);
  return (conf?.toLowerCase() ?? 'west') as 'east' | 'west';
}

export function seasonToYear(season: string): string {
  return String(parseInt(season.split('-')[0]) + 1);
}

export function yearToSeason(year: string): string {
  const endYear = parseInt(year);
  return `${endYear - 1}-${String(endYear).slice(-2)}`;
}

export function buildSeriesSlug(series: SeriesData, allSeries: SeriesData[]): string {
  if (series.round === 4) return 'the-finals';

  const conf = getSeriesConference(series);
  const roundSlug = ROUND_SLUGS[series.round];

  if (series.round === 3) {
    return `${conf}-${roundSlug}`;
  }

  const sameGroup = allSeries.filter(
    s => s.round === series.round && s.round !== 4 && getSeriesConference(s) === conf
  );
  const matchupNum = sameGroup.findIndex(s => s.seriesKey === series.seriesKey) + 1;

  return `${conf}-${roundSlug}-${matchupNum}`;
}

export function findSeriesBySlug(slug: string, allSeries: SeriesData[]): SeriesData | undefined {
  return allSeries.find(s => buildSeriesSlug(s, allSeries) === slug);
}
