"use client";

import {Fragment} from "react";
import {Separator} from "@/components/ui/separator";
import {format} from "date-fns";
import useSWR from "swr";

interface Game {
  id: string;
  teams: {
    home: {
      name: string;
      logo: string;
    };
    away: {
      name: string;
      logo: string;
    };
  };
  scores: {
    home: {
      total: number;
    };
    away: {
      total: number;
    };
  };
}

interface Scores {
  showScores: boolean;
  dateSelected: Date | undefined;
}

const Scores = ({showScores, dateSelected}: Scores) => {
  const devModeResponse = require("../../exampleResponse.json");
  const devModeGames: Game[] = devModeResponse.response;
  
  const todaysDate = new Date();
  const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
  
  const fetcher = (url: string) => fetch(url).then((res) => res.json());
  const {data, error, isLoading} = useSWR(
    `/api/games?date=${
          dateSelected === undefined
            ? `${format(todaysDate, "yyyy-MM-dd")}`
            : `${format(dateSelected, "yyyy-MM-dd")}`
        }&timezone=${userTimezone}&league=12&season=2024-2025`,
    fetcher
  );

  const games: Game[] = data?.response

  function noImage(event: React.SyntheticEvent<HTMLImageElement, Event>) {
    event.currentTarget.src = "https://placehold.co/48x48?text=No+logo";
  }

  return (
    <div>
      {dateSelected && games?.length === 0 && (
        <h1>No 🏀 games on {format(dateSelected, "PPP")}</h1>
      )}
      {isLoading && <div>Scores are loading!</div>}
      {/* to test by calling the API use games as what you map through, otherwise use devModeGames */}
      {games?.map((game) => {
        return (
          <Fragment key={game.id}>
            <div className="flex flex-row justify-evenly mt-2">
              <div className="flex flex-col items-center">
                <div>
                  <img
                    src={game.teams.home.logo}
                    onError={noImage}
                    className="block max-w-12 h-12"
                    alt={`${game.teams.home.name} logo`}
                  />
                </div>
                <p className="mt-2">{game.teams.home.name.split(" ").pop()}</p>
                <h2 className="mb-2">
                  {showScores && game.scores.home.total !== null
                    ? `${game.scores.home.total}`
                    : "-"}
                </h2>
              </div>
              <div className="flex flex-col items-center">
                <div>
                  <img
                    src={game.teams.away.logo}
                    onError={noImage}
                    className="block max-w-12 h-12"
                    alt={`${game.teams.away.name} logo`}
                  />
                </div>
                <p className="mt-2">{game.teams.away.name.split(" ").pop()}</p>
                <h2 className="mb-2">
                  {showScores && game.scores.away.total !== null
                    ? `${game.scores.away.total}`
                    : "-"}
                </h2>
              </div>
            </div>
            <Separator className="h-1 bg-slate-950 w-full last:hidden" />
          </Fragment>
        );
      })}
    </div>
  );
};

export default Scores;
