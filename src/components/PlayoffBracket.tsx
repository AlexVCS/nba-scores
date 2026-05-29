import type { SeriesData } from "@/helpers/helpers";
import TeamLogos from './TeamLogos';

interface PlayoffBracketProps {
  conferenceName: string;
  playoffPicture: SeriesData[];
}

function PlayoffBracket({ conferenceName, playoffPicture }: PlayoffBracketProps) {
  if (!playoffPicture || playoffPicture.length === 0) {
    return <p>No playoff data available</p>;
  }

  return (
    <div className="mb-8">
      <h2 className="text-2xl font-bold mb-4 dark:text-slate-50">{conferenceName}</h2>
      <div className="space-y-6">
        {playoffPicture.map((series) => {
          const [team1, team2] = series.teams;
          const team1Wins = series.wins[team1.id] || 0;
          const team2Wins = series.wins[team2.id] || 0;
          const isComplete = series.winnerTeamId !== null;

          return (
            <div
              key={series.seriesKey}
              className="border border-gray-300 dark:border-gray-700 rounded p-4 bg-white dark:bg-slate-900"
            >
              <div className="text-sm font-semibold text-gray-600 dark:text-gray-400 mb-3">
                {series.roundName}
              </div>

              {/* Matchup Summary */}
              <div className="space-y-2 mb-4 pb-4 border-b border-gray-200 dark:border-gray-700">
                <div className={`flex justify-between items-center ${team1.id === series.winnerTeamId ? "font-bold" : ""}`}>
                  <span className="dark:text-slate-50"><TeamLogos teamName={team1.tricode} teamId={team1.id} size={48} /> {team1.tricode}</span>
                  <span className="text-lg dark:text-slate-50">{team1Wins}</span>
                </div>
                <div className={`flex justify-between items-center ${team2.id === series.winnerTeamId ? "font-bold" : ""}`}>
                  <span className="dark:text-slate-50"><TeamLogos teamName={team2.tricode} teamId={team2.id} size={48} /> {team2.tricode}</span>
                  <span className="text-lg dark:text-slate-50">{team2Wins}</span>
                </div>
              </div>

              {/* Games */}
              <div className="space-y-2">
                {series.games.map((game) => (
                  <div key={game.gameId} className="text-sm dark:text-slate-300 flex justify-between items-center">
                    <span>{new Date(game.date).toLocaleDateString()}</span>
                    <span className="text-xs text-gray-500 dark:text-gray-400 flex-1 text-center">
                      {game.homeTeam.tricode} vs {game.awayTeam.tricode}
                    </span>
                    <span>
                      {game.homeTeam.tricode} {game.homeTeam.score} - {game.awayTeam.score} {game.awayTeam.tricode}
                    </span>
                  </div>
                ))}
              </div>

              {/* Winner */}
              {isComplete && (
                <div className="mt-4 pt-3 border-t border-gray-200 dark:border-gray-700 text-sm font-semibold text-green-600 dark:text-green-400">
                  Winner: {series.winnerTeamTricode}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default PlayoffBracket;
