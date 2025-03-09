import * as NBAIcons from "react-nba-logos";
import { placeholderTeamLogo } from "@/helpers/helpers";
import {Link} from "react-router-dom";

interface GameCardProps {
  showScores: boolean;
  game: {
    gameId: string;
    gameCode: string;
    gameStatus: number;
    gameStatusText: string;
    ifNecessary: boolean;
    seriesGameNumber: string;
    seriesText: string;
    homeTeam: {
      teamName: string;
      teamTricode: string;
      score: number;
    };
    awayTeam: {
      teamName: string;
      teamTricode: string;
      score: number;
    };
  };
}

type NBAIconsType = typeof NBAIcons;
type TeamCodeType = keyof NBAIconsType;


const GameCard: React.FC<GameCardProps> = ({game, showScores}) => {
  const HomeTeamLogo = NBAIcons[game.homeTeam.teamTricode as TeamCodeType];
  const AwayTeamLogo = NBAIcons[game.awayTeam.teamTricode as TeamCodeType];
  const gameInProgress = game.gameStatus !== 1

  return (
    <div className="flex justify-center lg:justify-start">
      <article className="grid grid-cols-3 w-[336px] h-[178px] justify-items-center content-center lg:items-start">
        <div className="text-center">
          <figure className="place-self-center">
            {HomeTeamLogo ? <HomeTeamLogo size={48} /> : placeholderTeamLogo}
          </figure>
          <figcaption className="sr-only">
            {game.homeTeam.teamName} logo
          </figcaption>
          <div className="self-center text-sm mt-1">
            {game.homeTeam.teamName}
          </div>
          {showScores && gameInProgress && <div>{game.homeTeam.score}</div>}
        </div>

        <div className="text-lg text-center place-self-center">
          {game.gameStatusText}
          <div className="text-sm mt-1">
            {game.gameStatusText.includes("ET") ? (
              ""
            ) : (
              <Link to={`/games/${game.gameId}/boxscore`}>Box score</Link>
            )}
          </div>
        </div>

        <div className="text-center">
          <figure className="place-self-center">
            {AwayTeamLogo ? <AwayTeamLogo size={48} /> : placeholderTeamLogo}
          </figure>
          <figcaption className="sr-only">
            {game.awayTeam.teamName} logo
          </figcaption>
          <div className="self-center text-sm mt-1">
            {game.awayTeam.teamName}
          </div>
          {showScores && gameInProgress && <div>{game.awayTeam.score}</div>}
        </div>
      </article>
    </div>
  );
};

export default GameCard;
