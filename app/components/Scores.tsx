/* eslint-disable @next/next/no-img-element */
import {format} from "date-fns";
import useSWR from "swr";
import {NextRequest} from "next/server";
import {headers} from "next/headers";
import getURL from "@/lib/utils/getURL";

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

const Scores = async ({
  selectedDate,
  url,
}: {
  selectedDate: string;
  url: string;
}) => {
  const devModeResponse = require("../../exampleResponse.json");
  const devModeGames: Game[] = devModeResponse.response;

  const todaysDate = new Date();
  const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
  const headerList = headers();
  const pathname = headerList.get("x-current-path");

  // console.log("this is the url", getURL());

  // const fetcher = (url: string) => fetch(url).then((res) => res.json());
  console.log('selected', selectedDate)
  const data = await fetch(
    getURL(`/api/games?date=${!selectedDate ? `${format(todaysDate, "yyyy-MM-dd")}` : `${format(selectedDate, "yyyy-MM-dd")}`}&timezone=${userTimezone}&league=12&season=2024-2025`)
  );
  const res = await data.json();
  console.log(res);
  const games: Game[] = res?.response;

  // const {data, error, isLoading} = useSWR(
  //   `/api/games?date=${selectedDate}
  //   &timezone=${userTimezone}&league=12&season=2024-2025`,

  // ${
  //   selectedDate === undefined
  //     ? `${format(todaysDate, "yyyy-MM-dd")}`
  //     : `${format(selectedDate, "yyyy-MM-dd")}`
  // }
  // fetcher
  // );

  // function noImage(event: React.SyntheticEvent<HTMLImageElement, Event>) {
  //   event.currentTarget.src = "https://placehold.co/56x56?text=No+logo";
  // }

  // const noImage = event.currentTarget.src = "https://placehold.co/56x56?text=No+logo";

  return (
    <>
      {/* {selectedDate && games?.length === 0 && (
        <h1>No 🏀 games on {format(selectedDate, "PPP")}</h1>
      )}
      {isLoading && <div>Games are loading!</div>} */}
      <div className="flex flex-col">
        {games?.map((game) => {
          return (
            <div key={game.id} className="grid grid-cols-2 mb-6 items-center">
              <div>
                <div className="h-16 w-1/2 mx-auto content-center dark:bg-primary rounded pl-2 pr-2">
                  <img
                    src={game.teams.home.logo}
                    // onError={noImage}
                    className="inline max-w-full max-h-14"
                    alt={`${game.teams.home.name} logo`}
                  />
                </div>
                <p className="mt-5">{game.teams.home.name.split(" ").pop()}</p>
                {/* <h2 className="mt-4">
                  {selectedScores && game.scores.home.total !== null
                    ? `${game.scores.home.total}`
                    : "-"}
                </h2> */}
              </div>

              <div>
                <div className="h-16 w-1/2 mx-auto content-center dark:bg-primary rounded pl-2 pr-2">
                  <img
                    src={game.teams.away.logo}
                    // onError={noImage}
                    className="inline max-w-full max-h-14"
                    alt={`${game.teams.away.name} logo`}
                  />
                </div>
                <p className="mt-5">{game.teams.away.name.split(" ").pop()}</p>
                {/* <h2 className="mt-4">
                  {selectedScores && game.scores.away.total !== null
                    ? `${game.scores.away.total}`
                    : "-"}
                </h2> */}
              </div>
            </div>
          );
        })}
      </div>
    </>
  );
};

export default Scores;
