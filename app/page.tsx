"use client";

import Image from "next/image";
import {useState, useEffect} from "react";

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
  // ... other properties of a game
}

function Home() {
  const [gameData, setGameData] = useState<Game[]>([]);

  useEffect(() => {
    async function fetchData() {
      const url = `https://api-nba-v1.p.rapidapi.com/games?date=2022-02-13`;
      const options = {
        method: "GET",
        headers: {
          "X-RapidAPI-Key": process.env.NEXT_PUBLIC_XRapidAPIKey,
          "X-RapidAPI-Host": process.env.NEXT_PUBLIC_XRapidAPIHost,
        },
      };
      const res = await fetch(url, options);
      const jsonRes = await res.json();
      console.log("Fetched game data:", jsonRes.response);
      setGameData(jsonRes.response);
      // console.log(gameData)
    }

    fetchData();
  }, []);

  

  return (
    <div>
      <h1>NBA Scores</h1>
      {/* Render gameData here */}
      {gameData.map((game) => {
        return (
          <div className="mb-2 flex justify-center space-between" key={game.id}>
            <Image
              src={game.teams.home.logo}
              width={50}
              height={50}
              alt={`${game.teams.home.code} logo`}
            />
            <h1>
              {game.teams.home.code} {game.scores.home.points}
            </h1>
            vs.
            <Image
              src={game.teams.visitors.logo}
              width={50}
              height={50}
              alt={`${game.teams.visitors.code} logo`}
            />
            <h1>
              {game.teams.visitors.code} {game.scores.visitors.points}
            </h1>
          </div>
        );
      })}
    </div>
  );
}

export default Home;
