import {useQuery} from "@tanstack/react-query";
import {useState, useEffect} from "react";
import GameCard from "./GameCard.jsx";
import {Switch} from "@adobe/react-spectrum";
import {useSearchParams} from "react-router";
import {setItem, getItem} from "@/helpers/helpers.jsx";

type GameData = {
  gameId: string;
  gameCode: string;
  gameStatus: number;
  gameLabel: string;
  gameSubLabel: string;
  gameTimeUTC: string;
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
interface GamesProps {
  setGamesToday: React.Dispatch<React.SetStateAction<boolean>>;
}

const Games = ({setGamesToday}: GamesProps) => {
  const [searchParams] = useSearchParams({date: ""});
  const dateParam: string = searchParams.get("date") ?? "";
  const [showScores, setShowScores] = useState(() => {
    const item = getItem("showScores");
    return item === undefined ? false : item;
  });

  useEffect(() => {
    setItem("showScores", showScores);
  }, [showScores]);

  const getScores = async (dateParam: string): Promise<{games: GameData[]}> => {
    try {
      const baseUrl = import.meta.env.DEV
        ? import.meta.env.VITE_API_URL_DEV
        : import.meta.env.VITE_API_URL_PROD;
      const url = `${baseUrl}/?date=${dateParam}`;
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
  });

  useEffect(() => {
    if (data && dateParam) {
      const hasGames = data.games.length > 0;

      // Update the calendar unavailable dates
      setDatesWithNoGames((prev) => {
        const newSet = new Set(prev);
        if (hasGames) {
          newSet.delete(dateParam);
        } else {
          newSet.add(dateParam);
        }
        return newSet;
      });

      // Update gamesToday state
      setGamesToday(hasGames);
    }
  }, [data, dateParam, setDatesWithNoGames, setGamesToday]);

  if (isLoading) return <h1>Loading...</h1>;
  if (error) return <h1>{JSON.stringify(error)}</h1>;
  if (!data) return <h1>Didn't receive any games</h1>;
  const {games} = data;
  return (
    <>
      {games.some((game) => game.gameStatus !== 1) && (
        <div className="flex justify-center items-center">
          <Switch isSelected={showScores} onChange={setShowScores}>
            <div className="dark:text-slate-50 text-neutral-950">
              {showScores ? "Hide Scores" : "Show Scores"}
            </div>
          </Switch>
        </div>
      )}
      {games.length === 0 ? (
        <div className="flex justify-center text-lg dark:text-slate-50 text-neutral-950">
          No games today
        </div>
      ) : (
        <section className="px-4 py-6">
          <div
            className={`grid gap-8 max-w-4xl mx-auto ${
              games.length === 1
                ? "grid-cols-1 place-items-center"
                : "grid-cols-1 lg:grid-cols-2"
            }`}
          >
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
