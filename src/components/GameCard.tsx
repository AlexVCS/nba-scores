import * as NBAIcons from "react-nba-logos";
import {Switch} from "@adobe/react-spectrum";
import {useState} from "react";
import {useQuery} from "@tanstack/react-query";


interface GameData {
  games: {
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
  }[];
}

  const getBoxScores = async (game) => {
    try {
      //  const gameYear = gameCode.slice(0,4)
      // const gameId = searchParams.get("id");
      const url = `http://localhost:3000/boxscore`;
      const response = await fetch(url);
      return response.json();
    } catch (error) {
      console.error(`This call didn't work, this is the ${error}`);
    }
  };


  // const {
  //   isLoading,
  //   data: boxscore,
  //   error,
  // } = useQuery({
  //   queryKey: ["boxscore"],
  //   queryFn: () => getBoxScores(game),
  // });

type NBAIconsType = typeof NBAIcons;
type TeamCodeType = keyof NBAIconsType;

const GameCard: React.FC<GameData> = ({games}) => {
  const [showScores, setShowScores] = useState(false);
  return (
    <div>
      <div className="flex justify-center">
        <Switch isSelected={showScores} onChange={setShowScores}>
          {showScores ? "Hide Scores" : "Show Scores"}
        </Switch>
      </div>
      {games?.map((game) => {
        const HomeTeamLogo =
          NBAIcons[game.homeTeam.teamTricode as TeamCodeType];
        const AwayTeamLogo =
          NBAIcons[game.awayTeam.teamTricode as TeamCodeType];

          //  console.log(game.gameId)
        return (
          <section key={game.gameId} className="flex justify-center">
            <article className="grid grid-cols-3 w-[336px] h-[178px] justify-items-center content-center items-start">
              <div className="text-center">
                <figure className="place-self-center">
                  {HomeTeamLogo && <HomeTeamLogo size={48} />}
                </figure>
                <figcaption className="sr-only">
                  {game.homeTeam.teamName} logo
                </figcaption>
                <div className="self-center text-sm mt-1">
                  {game.homeTeam.teamName}
                </div>
                {showScores && <div>{game.homeTeam.score}</div>}
              </div>

              <div className="text-lg text-center place-self-center">
                {game.gameStatusText}
                <div className="text-sm mt-1">
                  <a
                    onClick={() =>
                      getBoxScores(game.gameId, game.gameCode.slice(0, 4))
                    }
                    href={
                      "/game=" +
                      game.gameId +
                      "&year=" +
                      game.gameCode.slice(0, 4)
                    }
                  >
                    Box score
                  </a>
                </div>
              </div>

              <div className="text-center">
                <figure className="place-self-center">
                  {AwayTeamLogo && <AwayTeamLogo size={48} />}
                </figure>
                <figcaption className="sr-only">
                  {game.awayTeam.teamName} logo
                </figcaption>
                <div className="self-center text-sm mt-1">
                  {game.awayTeam.teamName}
                </div>
                {showScores && <div>{game.awayTeam.score}</div>}
              </div>
            </article>
          </section>
        );
      })}
    </div>
  );
};

export default GameCard;
