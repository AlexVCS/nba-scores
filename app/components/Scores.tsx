"use client"

import Image from "next/image";
import {useState, useEffect} from "react";
import moment from "moment";

interface Game {
  id: string;
  teams: {
    home: {
      code: string;
    };
    visitors: {
      home: {
        code: string;
      };
    };
  };
}

const Scores = ({selectedDate}) => {
  const [gameData, setGameData] = useState<Game[]>([]);
  

  useEffect(() => {
    async function fetchData() {
      const date = moment(selectedDate)
        // the api returns results a day behind, this adds a day to the selected date to compensate
        .add(1, "days")
        .add(5, "hours")
        .format("YYYY-MM-DD");

      const url = `https://api-nba-v1.p.rapidapi.com/games?date=${date}`;
      const options = {
        method: "GET",
        headers: {
          "X-RapidAPI-Key": process.env.NEXT_PUBLIC_XRapidAPIKey,
          "X-RapidAPI-Host": process.env.NEXT_PUBLIC_XRapidAPIHost,
        },
      };
      const res = await fetch(url, options);
      const jsonRes = await res.json();
      setGameData(jsonRes.response);
    }

    fetchData();
  }, [selectedDate]);

  return (
    <div>
      {gameData?.map((game) => {
        return (
          <div className="mb-2 flex justify-center space-between" key={game.id}>
            <div className="flex flex-col justify-center	">
              <Image
                src={game.teams.home.logo}
                width={48}
                height={48}
                alt={`${game.teams.home.code} logo`}
              />
              <h1>{game.teams.home.code}</h1>
            </div>
            <h2>{game.scores.home.points}</h2>
            vs.
            <div>
              <Image
                src={game.teams.visitors.logo}
                width={50}
                height={50}
                alt={`${game.teams.visitors.code} logo`}
              />
              <h1>{game.teams.visitors.code}</h1>
            </div>
            <h2>{game.scores.visitors.points}</h2>
          </div>
        );
      })}
    </div>
  );
};

export default Scores;
