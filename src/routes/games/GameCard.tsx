import {Link} from "react-router-dom";
import TeamLogos from "@/components/TeamLogos";
import {generateWatchLink} from "@/helpers/helpers";

interface GameCardProps {
  showScores: boolean;
  // dateParam: string;
  game: {
    gameId: string;
    gameCode: string;
    gameTimeUTC: string;
    gameStatus: number;
    gameStatusText: string;
    gameLabel: string;
    gameSubLabel: string;
    ifNecessary: boolean;
    seriesGameNumber: string;
    seriesText: string;
    boxscoreAvailable?: boolean;
    homeTeam: {
      teamName: string;
      teamTricode: string;
      score: number;
      teamId: number;
    };
    awayTeam: {
      teamName: string;
      teamTricode: string;
      score: number;
      teamId: number;
    };
  };
}

function GameCard({game, showScores = false}: GameCardProps) {
  const gameHasStarted = game.gameStatus !== 1;
  const shouldShowBoxscore =
    showScores &&
    gameHasStarted &&
    game.gameId.length > 0 &&
    game.boxscoreAvailable === true;
  const watchGameLink = generateWatchLink(game.awayTeam.teamTricode, game.homeTeam.teamTricode, game.gameId);

  return (
    <div className="flex justify-center lg:justify-start">
      <article className="grid grid-cols-3 w-[336px] h-[178px] justify-items-center items-center">
        <div className="flex flex-col items-center text-center">
          <TeamLogos
            teamName={game.homeTeam.teamName}
            teamId={game.homeTeam.teamId}
            size={48}
            tricode={game.homeTeam.teamTricode}
          />
          <div className="text-sm mt-1 w-full">
            <div className="bg-gray-900 border-2 border-gray-700 rounded w-full p-2">
              <div
                className="font-mono text-xl md:text-2xl text-amber-500 text-center font-bold tracking-wider"
                style={{textShadow: "0 0 5px rgba(245, 158, 11, 0.7)"}}
              >
                <span>{game.homeTeam.teamId > 0 ? game.homeTeam.teamTricode : "TBD"}</span>
              </div>
              {showScores && gameHasStarted && (
                <div className="mt-3 border-t-2 border-gray-700 pt-3">
                  <div
                    className="font-mono text-xl md:text-2xl text-amber-500 text-center tabular-nums font-bold"
                    style={{textShadow: "0 0 10px rgba(245, 158, 11, 0.7)"}}
                  >
                    {game.homeTeam.score}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="text-base text-center place-self-center dark:text-slate-50 text-neutral-950">
          {game.gameStatusText}
          <div className="text-xs mt-2">
            {game.gameStatusText.includes(":") ? (
              ""
            ) : (
              <div className="flex flex-col gap-1">
                {shouldShowBoxscore && (
                  <Link to={`/games/${game.gameId}/boxscore`}>Box score</Link>
                )}
                <Link to={`${watchGameLink}`} target="_blank">
                  Watch
                </Link>
              </div>
            )}
          </div>
          {game.gameLabel.length > 0 && (
            <div className="text-xs mt-2">
              {game.gameLabel}: {game.gameSubLabel}
            </div>
          )}
        </div>

        <div className="flex flex-col items-center text-center">
          <TeamLogos
            teamName={game.awayTeam.teamName}
            teamId={game.awayTeam.teamId}
            size={48}
            tricode={game.awayTeam.teamTricode}
          />
          <div className="text-sm mt-1 w-full">
            <div className="bg-gray-900 border-2 border-gray-700 rounded w-full p-2">
              <div
                className="font-mono text-xl md:text-2xl text-amber-500 text-center font-bold tracking-wider"
                style={{textShadow: "0 0 5px rgba(245, 158, 11, 0.7)"}}
              >
                <span>{game.awayTeam.teamId > 0 ? game.awayTeam.teamTricode : "TBD"}</span>
              </div>
              {showScores && gameHasStarted && (
                <div className="mt-3 border-t-2 border-gray-700 pt-3">
                  <div
                    className="font-mono text-xl md:text-2xl text-amber-500 text-center tabular-nums font-bold"
                    style={{textShadow: "0 0 10px rgba(245, 158, 11, 0.7)"}}
                  >
                    {game.awayTeam.score}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </article>
    </div>
  );
}

export default GameCard;
