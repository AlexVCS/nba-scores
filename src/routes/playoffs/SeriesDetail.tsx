import { useState } from 'react';
import { useParams, useSearchParams, Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { usePlayoffData } from '@/hooks/usePlayoffData';
import { generateWatchLink } from '@/helpers/helpers';
import TeamLogos from '@/components/TeamLogos';

function SeriesDetail() {
  const { seriesKey } = useParams<{ seriesKey: string }>();
  const [searchParams] = useSearchParams();
  const season = searchParams.get('season');
  const [isRevealed, setIsRevealed] = useState(false);

  const { data, isLoading, error } = usePlayoffData(season);

  if (isLoading) return <p className="p-4 dark:text-slate-50">Loading...</p>;
  if (error) return <p className="p-4 dark:text-slate-50">Error: {String(error)}</p>;
  if (!data) return <p className="p-4 dark:text-slate-50">No data available</p>;

  // Find the series
  const series = data.series.find(s => s.seriesKey === seriesKey);

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

  return (
    <div className="p-4 max-w-4xl mx-auto">
      {/* Back button */}
      <Link
        to={`/playoffs${season ? `?season=${season}` : ''}`}
        className="inline-flex items-center gap-2 text-blue-500 hover:text-blue-600 dark:text-blue-400 dark:hover:text-blue-300 mb-4"
      >
        <ArrowLeft size={20} />
        Back to Bracket
      </Link>

      {/* Series header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2 dark:text-slate-50">{series.roundName}</h1>
        <p className="text-gray-600 dark:text-gray-400">{data.season} Playoffs</p>
      </div>

      {/* Reveal button */}
      <div className="flex justify-center mb-6">
        <button
          onClick={() => setIsRevealed(!isRevealed)}
          className="text-sm text-blue-500 hover:text-blue-600 dark:text-blue-400 dark:hover:text-blue-300 border border-blue-500 dark:border-blue-400 rounded px-4 py-2 transition-colors"
        >
          {isRevealed ? 'Hide Results' : 'Reveal Results'}
        </button>
      </div>

      {/* Series summary */}
      <div className="border border-gray-300 dark:border-gray-700 rounded p-6 bg-white dark:bg-slate-900 mb-6">
        <div className={`space-y-4 ${isRevealed ? "mb-6 pb-6 border-b border-gray-200 dark:border-gray-700" : ""}`}>
          <div className={`flex justify-between items-center ${isRevealed && team1.id === series.winnerTeamId ? "font-bold" : ""}`}>
            <div className="flex items-center gap-3">
              <TeamLogos teamName={team1.tricode} teamId={team1.id} size={48} />
              <span className="text-xl dark:text-slate-50">{team1.tricode}</span>
            </div>
            {isRevealed && <span className="text-2xl dark:text-slate-50">{team1Wins}</span>}
          </div>
          <div className={`flex justify-between items-center ${isRevealed && team2.id === series.winnerTeamId ? "font-bold" : ""}`}>
            <div className="flex items-center gap-3">
              <TeamLogos teamName={team2.tricode} teamId={team2.id} size={48} />
              <span className="text-xl dark:text-slate-50">{team2.tricode}</span>
            </div>
            {isRevealed && <span className="text-2xl dark:text-slate-50">{team2Wins}</span>}
          </div>
        </div>

        {/* Games */}
        {isRevealed && (
          <div className="space-y-3">
            <h2 className="text-lg font-semibold dark:text-slate-50 mb-3">Games</h2>
            {series.games.map((game) => {
              const shouldShowWatch = seasonYear >= 2012;
              const watchLink = generateWatchLink(game.awayTeam.tricode, game.homeTeam.tricode, game.gameId);

              return (
                <div
                  key={game.gameId}
                  className="text-sm dark:text-slate-300 flex justify-between items-center gap-3 p-3 border border-gray-200 dark:border-gray-700 rounded bg-gray-50 dark:bg-slate-800"
                >
                  <span className="font-medium">{new Date(game.date).toLocaleDateString()}</span>
                  <span className="text-xs text-gray-500 dark:text-gray-400 flex-1 text-center">
                    {game.homeTeam.tricode} vs {game.awayTeam.tricode}
                  </span>
                  <span className="flex items-center gap-3">
                    <span className="font-semibold">
                      {game.homeTeam.tricode} {game.homeTeam.score} - {game.awayTeam.score} {game.awayTeam.tricode}
                    </span>
                    {shouldShowWatch && (
                      <a
                        href={watchLink}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-500 hover:text-blue-600 dark:text-blue-400 dark:hover:text-blue-300 text-xs"
                      >
                        Watch
                      </a>
                    )}
                  </span>
                </div>
              );
            })}
          </div>
        )}

        {/* Winner */}
        {isRevealed && isComplete && (
          <div className="mt-6 pt-4 border-t border-gray-200 dark:border-gray-700 text-lg font-semibold text-green-600 dark:text-green-400">
            Winner: {series.winnerTeamTricode}
          </div>
        )}
      </div>
    </div>
  );
}

export default SeriesDetail;
