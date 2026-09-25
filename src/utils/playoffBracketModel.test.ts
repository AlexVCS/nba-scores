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
        {...series('R2-bos-lal', 2, [bos, lal]), roundName: 'NBA Finals'},
      ],
    };

    const model = buildPlayoffBracketModel(response);

    expect(model.fallbackMode).toBe(true);
    expect(model.format.finalsRound).toBe(2);
    expect(model.series[1].isFinals).toBe(true);
    expect(model.series[1].roundName).toBe('NBA Finals');
    expect(model.groups.some(group => group.id === 'finals')).toBe(true);
  });

  it('does not turn the latest available series into Finals in an incomplete bracket', () => {
    const model = buildPlayoffBracketModel({
      season: '1960-61', teamGameRowCount: 2, gameCount: 1, seriesCount: 1,
      series: [{...series('east-semifinal', 1), roundName: 'Division Semifinals'}],
    });

    expect(model.format.finalsRound).toBeNull();
    expect(model.series[0].isFinals).toBe(false);
    expect(model.series[0].roundName).toBe('Division Semifinals');
    expect(model.groups).toEqual([{id: 'league', label: 'League Bracket', kind: 'league', sortOrder: 30}]);
  });

  it('honors an explicit null finals round instead of inferring a championship', () => {
    const model = buildPlayoffBracketModel({
      season: '1953-54', teamGameRowCount: 2, gameCount: 1, seriesCount: 1,
      format: {era: 'six-team-round-robin', playoffYear: 1954, finalsRound: null,
        bracketType: 'round-robin-plus-finals', supportsExactBracket: false, notes: []},
      series: [{...series('unresolved', 1), roundName: 'Finals'}],
    });

    expect(model.format.finalsRound).toBeNull();
    expect(model.series[0].isFinals).toBe(false);
  });

  it('uses canonical round and group metadata without replacing BAA Finals or division names', () => {
    const model = buildPlayoffBracketModel({
      season: '1948-49', teamGameRowCount: 4, gameCount: 2, seriesCount: 2,
      format: {era: 'eight-team-division', playoffYear: 1949, finalsRound: 3,
        bracketType: 'single-elimination', supportsExactBracket: true, notes: []},
      groups: [{id: 'east-division', label: 'Eastern Division', kind: 'division', sortOrder: 1},
        {id: 'finals', label: 'BAA Finals', kind: 'finals', sortOrder: 99}],
      rounds: [{round: 1, label: 'Division Semifinals', sortOrder: 1, defaultRevealed: true},
        {round: 3, label: 'BAA Finals', sortOrder: 3, defaultRevealed: false}],
      edges: [],
      series: [{...series('east', 1), bracketGroupId: 'east-division'},
        {...series('finals', 3), bracketGroupId: 'finals', bracketGroupLabel: 'NBA Finals'}],
    });

    expect(model.series.map(item => item.roundName)).toEqual(['Division Semifinals', 'BAA Finals']);
    expect(model.series.map(item => item.bracketGroupLabel)).toEqual(['Eastern Division', 'BAA Finals']);
    expect(model.series[1].isFinals).toBe(true);
    expect(model.rounds.map(round => round.label)).toEqual(['Division Semifinals', 'BAA Finals']);
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

    expect(slug).toBe('league-semifinal-1');
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
