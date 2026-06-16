import { describe, expect, it } from 'vitest';
import type { PlayoffBracketResponse, SeriesData } from '@/helpers/helpers';
import { buildPlayoffBracketModel, canRevealRound } from './playoffBracketModel';
import { buildSeriesSlug, findSeriesBySlug } from './seriesSlug';

const bos = { id: 1610612738, tricode: 'BOS', name: 'Celtics' };
const nyk = { id: 1610612752, tricode: 'NYK', name: 'Knicks' };
const lal = { id: 1610612747, tricode: 'LAL', name: 'Lakers' };
const ftw = { id: 1610612765, tricode: 'FTW', name: 'Ft. Wayne Zollner Pistons' };

function series(seriesKey: string, round: number, teams = [bos, nyk]): SeriesData {
  return {
    seriesKey,
    round,
    roundName: round === 1 ? 'First Round' : 'Conference Semifinals',
    teams,
    wins: { [teams[0].id]: 1 },
    winnerTeamId: teams[0].id,
    winnerTeamTricode: teams[0].tricode,
    gameCount: 1,
    games: [{
      gameId: `${seriesKey}-1`,
      date: `1951-04-0${round}`,
      round,
      roundName: round === 1 ? 'First Round' : 'Conference Semifinals',
      homeTeam: { ...teams[0], score: 100 },
      awayTeam: { ...teams[1], score: 90 },
      winnerTeamId: teams[0].id,
      winnerTeamTricode: teams[0].tricode,
    }],
  };
}

describe('buildPlayoffBracketModel', () => {
  it('creates fallback metadata for legacy responses', () => {
    const response: PlayoffBracketResponse = {
      season: '1950-51',
      teamGameRowCount: 4,
      gameCount: 2,
      seriesCount: 2,
      series: [
        series('R1-bos-nyk', 1),
        series('R2-bos-lal', 2, [bos, lal]),
      ],
    };

    const model = buildPlayoffBracketModel(response);

    expect(model.fallbackMode).toBe(true);
    expect(model.format.finalsRound).toBe(2);
    expect(model.series[1].isFinals).toBe(true);
    expect(model.series[1].roundName).toBe('NBA Finals');
    expect(model.groups.some(group => group.id === 'finals')).toBe(true);
  });

  it('uses fallback metadata consistently for legacy detail slugs', () => {
    const response: PlayoffBracketResponse = {
      season: '1956-57',
      teamGameRowCount: 4,
      gameCount: 2,
      seriesCount: 2,
      series: [
        series('R2-mnl-ftw', 2, [lal, ftw]),
        series('R4-bos-lal', 4, [bos, lal]),
      ],
    };

    const model = buildPlayoffBracketModel(response);
    const slug = buildSeriesSlug(model.series[0], model.series);

    expect(slug).toBe('west-conference-semifinal-1');
    expect(findSeriesBySlug(slug, model.series)?.seriesKey).toBe('R2-mnl-ftw');
  });

  it('uses provided rounds for reveal sequencing', () => {
    const response: PlayoffBracketResponse = {
      season: '1983-84',
      teamGameRowCount: 4,
      gameCount: 2,
      seriesCount: 2,
      format: {
        era: 'sixteen-team-best-of-five-first-round',
        playoffYear: 1984,
        finalsRound: 4,
        bracketType: 'single-elimination',
        supportsExactBracket: true,
        notes: [],
      },
      groups: [
        { id: 'east-conference', label: 'Eastern Conference', kind: 'conference', sortOrder: 20 },
        { id: 'finals', label: 'NBA Finals', kind: 'finals', sortOrder: 99 },
      ],
      rounds: [
        { round: 1, label: 'First Round', sortOrder: 1, defaultRevealed: true },
        { round: 4, label: 'NBA Finals', sortOrder: 4, defaultRevealed: false },
      ],
      edges: [],
      series: [
        { ...series('R1-bos-nyk', 1), bracketGroupId: 'east-conference', bracketOrder: 0, targetWins: 3, isFinals: false },
        { ...series('R4-bos-lal', 4, [bos, lal]), bracketGroupId: 'finals', bracketOrder: 0, targetWins: 4, isFinals: true },
      ],
    };

    const model = buildPlayoffBracketModel(response);

    expect(model.series[0].targetWins).toBe(3);
    expect(canRevealRound(1, model.rounds, new Set())).toBe(true);
    expect(canRevealRound(4, model.rounds, new Set())).toBe(false);
    expect(canRevealRound(4, model.rounds, new Set([1]))).toBe(true);
  });
});
