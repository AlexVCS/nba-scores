import {Link, useLocation} from "react-router";
import TeamLogos from "@/components/TeamLogos";
import {isValidDateParam} from "@/helpers/dateParam";
import {generateWatchLink} from "@/helpers/helpers";
import type {GameData} from "@/helpers/helpers";

interface GameCardProps {
  showScores: boolean;
  game: GameData;
  dateParam: string;
}

function GameCard({game, showScores = false, dateParam}: GameCardProps) {
  const location = useLocation();
  const gameHasStarted = game.gameStatus === 2 || game.gameStatus === 3;
  const watchGameLink = generateWatchLink(game.awayTeam.teamTricode, game.homeTeam.teamTricode, game.gameId);
  const isOriginalPreview = /^\/original(?=\/|$)/.test(location.pathname);
  const boxscorePath = `${isOriginalPreview ? "/original" : ""}/games/${game.gameId}/boxscore${isValidDateParam(dateParam) ? `?date=${dateParam}` : ""}`;

  return (
    <div className="flex justify-center lg:justify-start">
      <article className="relative grid grid-cols-3 w-[336px] h-[178px] justify-items-center items-center">
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
          {!showScores && gameHasStarted ? (game.gameStatus === 3 ? "Final" : "Live") : game.gameStatusText}
          <div className="text-xs mt-2">
            <div className="flex flex-col gap-1">
              {game.gameId && <Link
                to={boxscorePath}
                state={{from: location.pathname + location.search}}
                aria-label={`View ${game.awayTeam.teamTricode} at ${game.homeTeam.teamTricode} game details`}
                className="after:absolute after:inset-0 focus-visible:outline-none focus-visible:after:outline-2 focus-visible:after:outline-blue-500"
              >Game details</Link>}
              {!game.gameStatusText.includes(":") && <a className="relative z-10" href={watchGameLink} target="_blank" rel="noopener noreferrer">Watch</a>}
            </div>
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
