import { getTeamConference } from '@/constants/nbaTeams';
import type { SeriesData } from '@/helpers/helpers';

const ROUND_SLUGS: Record<number, string> = {
  1: 'first-round',
  2: 'semifinal',
  3: 'final',
};

function getSeriesConference(series: SeriesData): 'east' | 'west' {
  const conf = getTeamConference(series.teams[0].id) ?? getTeamConference(series.teams[1].id);
  if (!conf) {
    throw new Error(
      `Cannot determine conference for series "${series.seriesKey}" (team ids: ${series.teams.map(t => t.id).join(', ')})`
    );
  }
  return conf.toLowerCase() as 'east' | 'west';
}

export function seasonToYear(season: string): string {
  return String(parseInt(season.split('-')[0]) + 1);
}

export function yearToSeason(year: string): string {
  if (!/^\d{4}$/.test(year)) throw new Error('Invalid year provided to yearToSeason');
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
  const idx = sameGroup.findIndex(s => s.seriesKey === series.seriesKey);
  if (idx === -1) {
    throw new Error(
      `buildSeriesSlug: series not found in group (seriesKey=${series.seriesKey}, round=${series.round}, conf=${conf})`
    );
  }
  const matchupNum = idx + 1;

  return `${conf}-${roundSlug}-${matchupNum}`;
}

export function buildSlugMap(allSeries: SeriesData[]): Map<string, SeriesData> {
  const groups = new Map<string, SeriesData[]>();
  for (const s of allSeries) {
    if (s.round === 4) continue;
    const conf = getSeriesConference(s);
    const key = `${s.round}-${conf}`;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(s);
  }

  const map = new Map<string, SeriesData>();
  for (const s of allSeries) {
    if (s.round === 4) {
      map.set('the-finals', s);
      continue;
    }
    const conf = getSeriesConference(s);
    const roundSlug = ROUND_SLUGS[s.round];
    if (s.round === 3) {
      map.set(`${conf}-${roundSlug}`, s);
      continue;
    }
    const sameGroup = groups.get(`${s.round}-${conf}`)!;
    const matchupNum = sameGroup.findIndex(s2 => s2.seriesKey === s.seriesKey) + 1;
    map.set(`${conf}-${roundSlug}-${matchupNum}`, s);
  }
  return map;
}

export function findSeriesBySlug(slug: string, allSeries: SeriesData[]): SeriesData | undefined {
  return buildSlugMap(allSeries).get(slug);
}
