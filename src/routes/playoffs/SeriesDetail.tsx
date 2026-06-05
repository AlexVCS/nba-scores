import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Switch } from '@adobe/react-spectrum';
import { usePlayoffData } from '@/hooks/usePlayoffData';
import { generateWatchLink } from '@/helpers/helpers';
import TeamLogos from '@/components/TeamLogos';
import DarkModeToggle from '@/components/DarkModeToggle';
import { TEAM_COLORS } from '@/constants/teamColors';
import { yearToSeason, findSeriesBySlug } from '@/utils/seriesSlug';

function SeriesDetail() {
  const { year, seriesSlug } = useParams<{ year: string; seriesSlug: string }>();
  const season = yearToSeason(year ?? '');
  const [isRevealed, setIsRevealed] = useState(false);

  const { data, isLoading, error } = usePlayoffData(season);

  if (isLoading) return <p className="p-4 dark:text-slate-50">Loading...</p>;
  if (error) return <p className="p-4 dark:text-slate-50">Error: {String(error)}</p>;
  if (!data) return <p className="p-4 dark:text-slate-50">No data available</p>;

  const series = findSeriesBySlug(seriesSlug ?? '', data.series);

  if (!series) {
    return (
      <div className="p-4">
        <p className="dark:text-slate-50">Series not found</p>
        <Link
          to={`/playoffs${season ? `?season=${season}` : ''}`}
          className="text-blue-500 hover:text-blue-600 dark:text-blue-400 dark:hover:text-blue-300"
        >
          Back to Playoffs
        </Link>
      </div>
    );
  }

  const [team1, team2] = series.teams;
  const team1Wins = series.wins[team1.id] || 0;
  const team2Wins = series.wins[team2.id] || 0;
  const isComplete = series.winnerTeamId !== null;
  const seasonYear = parseInt(data.season.split('-')[0]);

  const team1Color = TEAM_COLORS[team1.id] ?? '#1D428A';
  const team2Color = TEAM_COLORS[team2.id] ?? '#1D428A';

  return (
    <div className="bg-slate-50 dark:bg-neutral-950 min-h-screen">
      <DarkModeToggle />
      <div className="p-4 max-w-4xl mx-auto">
      <div className="mb-6 text-center">
        <h1 className="text-xl sm:text-3xl font-bold mb-2 text-neutral-950 dark:text-slate-50">{series.roundName}</h1>
        <p className="text-lg sm:text-xl mb-2 font-bold text-neutral-950 dark:text-slate-50">{data.season} Playoffs</p>
        <Link
        to={`/playoffs${season ? `?season=${season}` : ''}`}
        className="hidden sm:inline-flex items-center gap-2 text-blue-500 hover:text-blue-600 dark:text-blue-400 dark:hover:text-blue-300 mb-4"
      >
        Bracket
      </Link>
      </div>

      <div className="flex justify-center mb-6">
        <Switch
          isSelected={isRevealed}
          onChange={setIsRevealed}
        >
          <span className="dark:text-slate-50 text-neutral-950">
            {isRevealed ? 'Hide Results' : 'Show Results'}
          </span>
        </Switch>
      </div>

      <div className="rounded overflow-hidden mb-6">
        <div
          className="p-6 text-white"
          style={{ background: `linear-gradient(to right, ${team1Color} 0%, ${team2Color} 100%)` }}
        >
          <div className="flex items-center justify-between">
            <div className={`flex flex-col items-center gap-2 ${isRevealed && team1.id === series.winnerTeamId ? "font-bold" : ""}`}>
              <TeamLogos teamName={team1.tricode} teamId={team1.id} size={64} />
              <span className="text-lg">{team1.tricode}</span>
            </div>
            <div className="text-center">
              {isRevealed && (
                <p className="text-3xl font-bold mt-1">{team1Wins} – {team2Wins}</p>
              )}
              {isRevealed && isComplete && (
                <p className="text-xs mt-1 opacity-80">{series.winnerTeamTricode} wins</p>
              )}
            </div>
            <div className={`flex flex-col items-center gap-2 ${isRevealed && team2.id === series.winnerTeamId ? "font-bold" : ""}`}>
              <TeamLogos teamName={team2.tricode} teamId={team2.id} size={64} />
              <span className="text-lg">{team2.tricode}</span>
            </div>
          </div>
        </div>

        {series.games.length > 0 && (
          <div className="px-4 py-3 bg-white dark:bg-neutral-900">
            <h2 className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-3">Games</h2>
            <div className="divide-y divide-gray-200 dark:divide-gray-700">
              {series.games.map((game, index) => {
                const shouldShowWatch = seasonYear >= 2012;
                const watchLink = generateWatchLink(game.awayTeam.tricode, game.homeTeam.tricode, game.gameId);
                const gameDate = new Date(game.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
                const homeWon = isRevealed && game.homeTeam.score > game.awayTeam.score;
                const awayWon = isRevealed && game.awayTeam.score > game.homeTeam.score;

                return (
                  <div
                    key={game.gameId}
                    className="relative text-sm text-gray-700 dark:text-slate-300 flex items-center gap-3 py-3"
                  >
                    {isRevealed && (
                      <Link to={`/games/${game.gameId}/boxscore`} className="absolute inset-0 sm:hidden" aria-label="Box score" />
                    )}
                    <span className="text-gray-400 dark:text-gray-500 shrink-0 w-14">Game {index + 1}</span>
                    <span className="font-medium shrink-0 hidden sm:block">{gameDate}</span>
                    {isRevealed ? (
                      <span className="flex-1 text-center">
                        <span className={homeWon ? "font-bold" : ""}>{game.homeTeam.tricode} {game.homeTeam.score}</span>
                        <span className="text-gray-400 dark:text-gray-500 mx-1">–</span>
                        <span className={awayWon ? "font-bold" : ""}>{game.awayTeam.score} {game.awayTeam.tricode}</span>
                      </span>
                    ) : (
                      <span className="flex-1" />
                    )}
                    {shouldShowWatch && (
                      <a
                        href={watchLink}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="relative z-10 text-blue-500 hover:text-blue-600 dark:text-blue-400 dark:hover:text-blue-300 shrink-0"
                      >
                        Watch
                      </a>
                    )}
                    {isRevealed && (
                      <Link
                        to={`/games/${game.gameId}/boxscore`}
                        className="hidden sm:inline text-blue-500 hover:text-blue-600 dark:text-blue-400 dark:hover:text-blue-300 shrink-0"
                      >
                        Box score
                      </Link>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
      <div className="h-16 sm:hidden" />
    </div>

    <div className="fixed bottom-0 left-0 right-0 z-10 flex justify-center pb-4 pt-3 bg-slate-50/90 dark:bg-neutral-950/90 backdrop-blur-sm sm:hidden">
      <Link
        to={`/playoffs${season ? `?season=${season}` : ''}`}
        className="inline-flex items-center gap-2 text-blue-500 hover:text-blue-600 dark:text-blue-400 dark:hover:text-blue-300"
      >
        Bracket
      </Link>
    </div>
    </div>
  );
}

export default SeriesDetail;
