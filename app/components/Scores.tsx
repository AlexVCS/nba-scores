"use client";

// import Image from "next/image";
import {Fragment, useState, useEffect} from "react";
import {Separator} from "@/components/ui/separator";
import DatePicker from "@/app/components/DatePicker";
import {format} from "date-fns";


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
  const [gameData, setGameData] = useState<Game[]>([]);
  const [formattedDate, setFormattedDate] = useState<Date | String>("");

  const devModeGameData: Game[] = require("../../exampleResponse.json");

  useEffect(() => {
    async function fetchData() {
      try {
        // const dd = String(todaysDate.getDate()).padStart(2, "0");
        // const mm = String(todaysDate.getMonth() + 1).padStart(2, "0");
        // const yyyy = todaysDate.getFullYear();

        // const formattedDate = `${yyyy}-${mm}-${dd}`;

        // const timeOffset = new Date().getTimezoneOffset() * 60 * 1000;
        // const userDateInMilliseconds = new Date().getTime();
        const todaysDate = new Date();
        console.log(todaysDate.getFullYear());

        // console.log("timeOffset is ", timeOffset);
        // console.log("userDateInMilliseconds is ", userDateInMilliseconds);
        // console.log(finalDate.toISOString());

        const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

        const url = `https://api-basketball.p.rapidapi.com/games?date=${
          dateSelected === undefined
            ? `${format(todaysDate, "yyyy-MM-dd")}`
            : `${format(dateSelected, "yyyy-MM-dd")}`
        }&timezone=${userTimezone}&league=12&season=2024-2025`;

        const options = {
          method: "GET",
          headers: {
            "X-RapidAPI-Key": process.env.NEXT_PUBLIC_XRapidAPIKey || "",
            "X-RapidAPI-Host": process.env.NEXT_PUBLIC_XRapidAPIHost || "",
          },
        };
        const res = await fetch(url, options);
        const jsonRes = await res.json();
        setGameData(jsonRes.response);
      } catch (error) {
        if (error) {
          throw new Error("Unable to get scores", error);
        }
      }
    }

    fetchData();
  }, [dateSelected]);

  function noImage(event: React.SyntheticEvent<HTMLImageElement, Event>) {
    event.currentTarget.src = "https://placehold.co/48x48?text=No+logo";
  }

  return (
    <div>
      {dateSelected && gameData.length === 0 && (
        <h1>No 🏀 games on {format(dateSelected, "PPP")}</h1>
      )}
      {/* to test by calling the API use gameData as what you map through, otherwise use devModeGameData */}
      {gameData?.map((game) => {
        return (
          <Fragment key={game.id}>
            <div className="flex flex-row justify-evenly mt-2">
              <div>
                <img
                  src={game.teams.home.logo}
                  onError={noImage}
                  className="object-contain w-12 h-12"
                  alt={`${game.teams.home.code} logo`}
                />
                <p className="mt-2">{game.teams.home.name}</p>
                <h2 className="mb-2">
                  {showScores && game.scores.home.total !== null
                    ? `${game.scores.home.total}`
                    : "-"}
                </h2>
              </div>
              <div>
                <img
                  src={game.teams.away.logo}
                  onError={noImage}
                  className="object-contain w-12 h-12"
                  alt={`${game.teams.away.code} logo`}
                />
                <p className="mt-2">{game.teams.away.name}</p>
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
