import {Link} from "react-router-dom";
import type {GameData} from "../shared/types";
import {placeholderTeamLogoUrl} from "@/helpers/helpers";
import {getTeamColors} from "../shared/teamColors";

interface A5GameCardProps {
  game: GameData;
  showScores: boolean;
}

const A5GameCard = ({game, showScores}: A5GameCardProps) => {
  const gameHasStarted = game.gameStatus !== 1;
  const isLive = game.gameStatus === 2;
  const isFinal = game.gameStatus === 3;
  const watchGameLink = `https://www.nba.com/game/${game.awayTeam.teamTricode}-vs-${game.homeTeam.teamTricode}-${game.gameId}?watch`;
  const endOf1819Season = new Date("2019-06-15T00:00:00Z");
  const gameDateUtc = new Date(game.gameTimeUTC);

  const getLogoUrl = (teamId: number) => `https://cdn.nba.com/logos/nba/${teamId}/global/L/logo.svg`;

  const homeColors = getTeamColors(game.homeTeam.teamId);
  const awayColors = getTeamColors(game.awayTeam.teamId);

  const homeWinning = game.homeTeam.score > game.awayTeam.score;
  const awayWinning = game.awayTeam.score > game.homeTeam.score;

  // Calculate score percentage for progress bar
  const totalScore = game.homeTeam.score + game.awayTeam.score;
  const homePercent = totalScore > 0 ? (game.homeTeam.score / totalScore) * 100 : 50;

  return (
    <article 
      className="analytics-game-card"
      style={{
        '--home-color': homeColors.primary,
        '--away-color': awayColors.primary,
      } as React.CSSProperties}
    >
      <div className="analytics-card-header" />
      
      <div className="analytics-card-content">
        <div className={`analytics-status-badge ${isLive ? 'live' : ''} ${isFinal ? 'final' : ''}`}>
          {isLive && <span className="analytics-live-dot" />}
          {game.gameStatusText}
        </div>

        <div className="analytics-teams">
          {/* Home Team */}
          <div className="analytics-team-row">
            <div className="analytics-team-info">
              <img
                src={getLogoUrl(game.homeTeam.teamId)}
                alt={`${game.homeTeam.teamName} logo`}
                className="analytics-team-logo"
                onError={(e) => {
                  e.currentTarget.src = placeholderTeamLogoUrl;
                }}
              />
              <div className="analytics-team-details">
                <div className="analytics-team-name">{game.homeTeam.teamName}</div>
                <div className="analytics-team-record">{game.homeTeam.teamTricode} • Home</div>
              </div>
            </div>
            {showScores && gameHasStarted && (
              <div className={`analytics-team-score ${homeWinning ? 'winner' : ''}`}>
                {game.homeTeam.score}
              </div>
            )}
          </div>

          {/* Away Team */}
          <div className="analytics-team-row">
            <div className="analytics-team-info">
              <img
                src={getLogoUrl(game.awayTeam.teamId)}
                alt={`${game.awayTeam.teamName} logo`}
                className="analytics-team-logo"
                onError={(e) => {
                  e.currentTarget.src = placeholderTeamLogoUrl;
                }}
              />
              <div className="analytics-team-details">
                <div className="analytics-team-name">{game.awayTeam.teamName}</div>
                <div className="analytics-team-record">{game.awayTeam.teamTricode} • Away</div>
              </div>
            </div>
            {showScores && gameHasStarted && (
              <div className={`analytics-team-score ${awayWinning ? 'winner' : ''}`}>
                {game.awayTeam.score}
              </div>
            )}
          </div>
        </div>

        {/* Score differential bar */}
        {showScores && gameHasStarted && (
          <div className="analytics-score-bar">
            <div 
              className="analytics-score-fill home" 
              style={{width: `${homePercent}%`}}
            />
            <div 
              className="analytics-score-fill away" 
              style={{width: `${100 - homePercent}%`}}
            />
          </div>
        )}
      </div>

      <div className="analytics-card-footer">
        {game.gameLabel.length > 0 ? (
          <span className="analytics-game-label">
            {game.gameLabel}: {game.gameSubLabel}
          </span>
        ) : (
          <span />
        )}
        
        <div className="analytics-card-links">
          {showScores && gameDateUtc >= endOf1819Season && !game.gameStatusText.includes(":") && (
            <Link to={`/5/games/${game.gameId}/boxscore`} className="analytics-card-link">
              Box Score
            </Link>
          )}
          <Link to={watchGameLink} target="_blank" className="analytics-card-link">
            Watch
          </Link>
        </div>
      </div>
    </article>
  );
};

export default A5GameCard;
