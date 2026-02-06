import {Link} from "react-router-dom";
import type {GameData} from "../shared/types";
import {placeholderTeamLogoUrl} from "@/helpers/helpers";

interface LED1GameCardProps {
  game: GameData;
  showScores: boolean;
  index: number;
}

const LED1GameCard = ({game, showScores}: LED1GameCardProps) => {
  const gameHasStarted = game.gameStatus !== 1;
  const isLive = game.gameStatus === 2;
  const watchGameLink = `https://www.nba.com/game/${game.awayTeam.teamTricode}-vs-${game.homeTeam.teamTricode}-${game.gameId}?watch`;
  const endOf1819Season = new Date("2019-06-15T00:00:00Z");
  const gameDateUtc = new Date(game.gameTimeUTC);

  const getLogoUrl = (teamId: number) => `https://cdn.nba.com/logos/nba/${teamId}/global/L/logo.svg`;

  return (
    <article className="led-game-card">
      <div className="led-teams-row">
        {/* Home Team */}
        <div className="led-team">
          <img
            src={getLogoUrl(game.homeTeam.teamId)}
            alt={`${game.homeTeam.teamName} logo`}
            className="led-team-logo"
            onError={(e) => {
              e.currentTarget.src = placeholderTeamLogoUrl;
            }}
          />
          <div className="led-scoreboard">
            <div className="led-tricode">{game.homeTeam.teamTricode}</div>
            {showScores && gameHasStarted && (
              <div className="led-score">{game.homeTeam.score}</div>
            )}
          </div>
        </div>

        {/* Center Status */}
        <div className="led-status">
          <span className={`led-status-text ${isLive ? "led-status-live" : ""}`}>
            {game.gameStatusText}
          </span>
          {!game.gameStatusText.includes(":") && (
            <div className="led-links">
              {showScores && gameDateUtc >= endOf1819Season && (
                <Link to={`/1/games/${game.gameId}/boxscore`} className="led-link">
                  Box Score
                </Link>
              )}
              <Link to={watchGameLink} target="_blank" className="led-link">
                Watch
              </Link>
            </div>
          )}
        </div>

        {/* Away Team */}
        <div className="led-team">
          <img
            src={getLogoUrl(game.awayTeam.teamId)}
            alt={`${game.awayTeam.teamName} logo`}
            className="led-team-logo"
            onError={(e) => {
              e.currentTarget.src = placeholderTeamLogoUrl;
            }}
          />
          <div className="led-scoreboard">
            <div className="led-tricode">{game.awayTeam.teamTricode}</div>
            {showScores && gameHasStarted && (
              <div className="led-score">{game.awayTeam.score}</div>
            )}
          </div>
        </div>
      </div>

      {game.gameLabel.length > 0 && (
        <div className="led-game-label">
          {game.gameLabel}: {game.gameSubLabel}
        </div>
      )}
    </article>
  );
};

export default LED1GameCard;
