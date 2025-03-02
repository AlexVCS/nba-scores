import {useQuery} from "@tanstack/react-query";
import {useState} from "react";
import GameCard from "./GameCard";
import Boxscore from "./boxscore/Boxscore";
import {Switch} from "@adobe/react-spectrum";
import {useSearchParams} from "react-router";

type GameData = {
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

const Games = () => {
  const [searchParams, setSearchParams] = useSearchParams({date: ""});
  const dateParam: string = searchParams.get("date") ?? "";
  const [showScores, setShowScores] = useState(false);

  const getScores = async (dateParam: string): Promise<{games: GameData[]}> => {
    try {
      const url = `http://localhost:3000/?date=${dateParam}`;
      const response = await fetch(url);
      return response.json();
    } catch (error) {
      console.error(`This call didn't work, this is the ${error}`);
      throw error;
    }
  };

  const {isLoading, data, error} = useQuery({
    queryKey: ["games", dateParam],
    queryFn: () => getScores(dateParam),
    // enabled: () => boxscore.length > 1 && false,
  });

  if (isLoading) return <h1>Loading...</h1>;
  if (error) return <h1>{JSON.stringify(error)}</h1>;
  if (!data) return <h1>Didn't receive any games</h1>;
  const {games} = data;
  return (
    <>
      {dateParam !== "" && (
        <div className="flex justify-center items-center">
          <Switch isSelected={showScores} onChange={setShowScores}>
            {showScores ? "Hide Scores" : "Show Scores"}
          </Switch>
        </div>
      )}
      {games.length === 0 ? (
        <div className="flex justify-center text-lg">No games today</div>
      ) : (
        <section className="px-4 py-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 max-w-4xl mx-auto">
            {games.map((gamedata) => (
              <GameCard
                key={gamedata.gameId}
                showScores={showScores}
                game={gamedata}
              />
            ))}
          </div>
        </section>
      )}
    </>
  );
};

export default Games;
