import {useQuery} from "@tanstack/react-query";
import {useState, useEffect} from "react";
import GameCard from "./GameCard.jsx";
import {Switch} from "@adobe/react-spectrum";
import {useSearchParams} from "react-router";
import {setItem, getItem} from "@/helpers/helpers.jsx";
import {parseDate} from "@internationalized/date";

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
  setDatesWithNoGames: React.Dispatch<React.SetStateAction<Set<string>>>;
  setGamesToday: React.Dispatch<React.SetStateAction<boolean>>;
}

const convertDatesToRanges = (dateStrings: Set<string>) => {
  if (dateStrings.size === 0) return [];

  const sortedDates = Array.from(dateStrings)
    .map((dateStr) => parseDate(dateStr))
    .sort((a, b) => a.compare(b));

  const ranges = [];
  let rangeStart = sortedDates[0];
  let rangeEnd = sortedDates[0];

  for (let i = 1; i < sortedDates.length; i++) {
    const currentDate = sortedDates[i];
    const prevDate = sortedDates[i - 1];

    // Check if current date is consecutive to previous date
    if (currentDate.compare(prevDate.add({days: 1})) === 0) {
      rangeEnd = currentDate;
    } else {
      // End current range and start new one
      ranges.push([rangeStart, rangeEnd]);
      rangeStart = currentDate;
      rangeEnd = currentDate;
    }
  }

  // Add the last range
  ranges.push([rangeStart, rangeEnd]);

  return ranges;
};

const Games = ({setDatesWithNoGames, setGamesToday}: GamesProps) => {
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

  // Convert unavailable dates to ranges for the calendar
  const unavailableRanges = convertDatesToRanges(new Set()); 

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
