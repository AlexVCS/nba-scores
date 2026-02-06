import {Link} from "react-router-dom";
import type {GameData} from "../shared/types";
import {placeholderTeamLogoUrl} from "@/helpers/helpers";

interface C4GameCardProps {
  game: GameData;
  showScores: boolean;
}

const C4GameCard = ({game, showScores}: C4GameCardProps) => {
  const gameHasStarted = game.gameStatus !== 1;
  const isLive = game.gameStatus === 2;
  const watchGameLink = `https://www.nba.com/game/${game.awayTeam.teamTricode}-vs-${game.homeTeam.teamTricode}-${game.gameId}?watch`;
  const endOf1819Season = new Date("2019-06-15T00:00:00Z");
  const gameDateUtc = new Date(game.gameTimeUTC);

  const getLogoUrl = (teamId: number) => `https://cdn.nba.com/logos/nba/${teamId}/global/L/logo.svg`;

  return (
    <article className="cyber-game-card">
      <div className="cyber-matchup">
        {/* Home Team */}
        <div className="cyber-team">
          <img
            src={getLogoUrl(game.homeTeam.teamId)}
            alt={`${game.homeTeam.teamName} logo`}
            className="cyber-team-logo"
            onError={(e) => {
              e.currentTarget.src = placeholderTeamLogoUrl;
            }}
          />
          <div className="cyber-score-box">
            <div className="cyber-tricode">{game.homeTeam.teamTricode}</div>
            {showScores && gameHasStarted && (
              <div className="cyber-score">{game.homeTeam.score}</div>
            )}
          </div>
        </div>

        {/* Center */}
        <div className="cyber-vs">
          <span className="cyber-vs-text">VS</span>
          <span className={`cyber-status-text ${isLive ? "cyber-status-live" : ""}`}>
            {game.gameStatusText}
          </span>
          {!game.gameStatusText.includes(":") && (
            <div className="cyber-links">
              {showScores && gameDateUtc >= endOf1819Season && (
                <Link to={`/4/games/${game.gameId}/boxscore`} className="cyber-link">
                  Box Score
                </Link>
              )}
              <Link to={watchGameLink} target="_blank" className="cyber-link">
                Watch
              </Link>
            </div>
          )}
        </div>

        {/* Away Team */}
        <div className="cyber-team">
          <img
            src={getLogoUrl(game.awayTeam.teamId)}
            alt={`${game.awayTeam.teamName} logo`}
            className="cyber-team-logo"
            onError={(e) => {
              e.currentTarget.src = placeholderTeamLogoUrl;
            }}
          />
          <div className="cyber-score-box">
            <div className="cyber-tricode">{game.awayTeam.teamTricode}</div>
            {showScores && gameHasStarted && (
              <div className="cyber-score">{game.awayTeam.score}</div>
            )}
          </div>
        </div>
      </div>

      {game.gameLabel.length > 0 && (
        <div className="cyber-game-label">
          {game.gameLabel}: {game.gameSubLabel}
        </div>
      )}
    </article>
  );
};

export default C4GameCard;
