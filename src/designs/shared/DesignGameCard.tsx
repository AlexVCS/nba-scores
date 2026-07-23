import {ExternalLink} from "lucide-react";
import {Link} from "react-router";
import TeamLogos from "@/components/TeamLogos";
import {generateWatchLink} from "@/helpers/helpers";
import type {GameData} from "@/helpers/helpers";
import {designPath} from "../designRoutes";
import type {AlternateDesignId} from "../types";

interface DesignGameCardProps {
  designId: AlternateDesignId;
  game: GameData;
  showScores: boolean;
  index: number;
}

function Team({game, side, showScore}: {game: GameData; side: "home" | "away"; showScore: boolean}) {
  const team = side === "home" ? game.homeTeam : game.awayTeam;
  return (
    <div className={`concept-team concept-team--${side}`}>
      <span className="concept-team__designation">{side === "home" ? "HOME" : "AWAY"}</span>
      <TeamLogos teamName={team.teamName} teamId={team.teamId} size={58} tricode={team.teamTricode} />
      <div>
        <strong>{team.teamId > 0 ? team.teamTricode : "TBD"}</strong>
        <small>{team.teamName}</small>
      </div>
      {showScore && <b className="concept-team__score">{team.score}</b>}
    </div>
  );
}

function DesignGameCard({designId, game, showScores, index}: DesignGameCardProps) {
  const started = game.gameStatus !== 1;
  const reveal = showScores && started;
  const boxscore = reveal && game.boxscoreAvailable === true && game.gameId.length > 0;
  const watch = generateWatchLink(game.awayTeam.teamTricode, game.homeTeam.teamTricode, game.gameId);

  return (
    <article className="concept-game-card" style={{"--card-index": index} as React.CSSProperties}>
      <header className="concept-game-card__status">
        <span>GAME {String(index + 1).padStart(2, "0")}</span>
        <strong>{game.gameStatusText}</strong>
        {game.gameLabel && <small>{game.gameLabel} · {game.gameSubLabel}</small>}
      </header>
      <div className="concept-game-card__matchup">
        <Team game={game} side="away" showScore={reveal} />
        <span className="concept-game-card__versus">VS</span>
        <Team game={game} side="home" showScore={reveal} />
      </div>
      {!game.gameStatusText.includes(":") && (
        <footer>
          {boxscore && <Link to={designPath(designId, `/games/${game.gameId}/boxscore`)}>Box score</Link>}
          <a href={watch} target="_blank" rel="noopener noreferrer">Watch <ExternalLink aria-hidden="true" /></a>
        </footer>
      )}
    </article>
  );
}

export default DesignGameCard;
