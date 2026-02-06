import {Link} from "react-router-dom";
import type {GameData} from "../shared/types";
import {placeholderTeamLogoUrl} from "@/helpers/helpers";

interface B2GameCardProps {
  game: GameData;
  showScores: boolean;
}

const B2GameCard = ({game, showScores}: B2GameCardProps) => {
  const gameHasStarted = game.gameStatus !== 1;
  const isLive = game.gameStatus === 2;
  const watchGameLink = `https://www.nba.com/game/${game.awayTeam.teamTricode}-vs-${game.homeTeam.teamTricode}-${game.gameId}?watch`;
  const endOf1819Season = new Date("2019-06-15T00:00:00Z");
  const gameDateUtc = new Date(game.gameTimeUTC);

  const getLogoUrl = (teamId: number) => `https://cdn.nba.com/logos/nba/${teamId}/global/L/logo.svg`;

  const homeWinning = game.homeTeam.score > game.awayTeam.score;
  const awayWinning = game.awayTeam.score > game.homeTeam.score;

  return (
    <article className="brutal-game-card">
      <div className="brutal-matchup">
        {/* Home Team */}
        <div className="brutal-team-row">
          <div className="brutal-team-info">
            <img
              src={getLogoUrl(game.homeTeam.teamId)}
              alt={`${game.homeTeam.teamName} logo`}
              className="brutal-team-logo"
              onError={(e) => {
                e.currentTarget.src = placeholderTeamLogoUrl;
              }}
            />
            <div>
              <div className="brutal-team-name">{game.homeTeam.teamTricode}</div>
              <div className="brutal-team-tricode">{game.homeTeam.teamName}</div>
            </div>
          </div>
          {showScores && gameHasStarted && (
            <div className={`brutal-score ${homeWinning ? "winner" : ""}`}>
              {game.homeTeam.score}
            </div>
          )}
        </div>

        <div className="brutal-vs">VS</div>

        {/* Away Team */}
        <div className="brutal-team-row">
          <div className="brutal-team-info">
            <img
              src={getLogoUrl(game.awayTeam.teamId)}
              alt={`${game.awayTeam.teamName} logo`}
              className="brutal-team-logo"
              onError={(e) => {
                e.currentTarget.src = placeholderTeamLogoUrl;
              }}
            />
            <div>
              <div className="brutal-team-name">{game.awayTeam.teamTricode}</div>
              <div className="brutal-team-tricode">{game.awayTeam.teamName}</div>
            </div>
          </div>
          {showScores && gameHasStarted && (
            <div className={`brutal-score ${awayWinning ? "winner" : ""}`}>
              {game.awayTeam.score}
            </div>
          )}
        </div>
      </div>

      <div className="brutal-status">
        <span className={`brutal-status-text ${isLive ? "brutal-status-live" : ""}`}>
          {game.gameStatusText}
        </span>
        {!game.gameStatusText.includes(":") && (
          <div className="brutal-links">
            {showScores && gameDateUtc >= endOf1819Season && (
              <Link to={`/2/games/${game.gameId}/boxscore`} className="brutal-link">
                Box
              </Link>
            )}
            <Link to={watchGameLink} target="_blank" className="brutal-link">
              Watch
            </Link>
          </div>
        )}
      </div>

      {game.gameLabel.length > 0 && (
        <div className="brutal-game-label">
          {game.gameLabel}: {game.gameSubLabel}
        </div>
      )}
    </article>
  );
};

export default B2GameCard;
