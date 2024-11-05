"use client";

// import Image from "next/image";
import {useState, useEffect} from "react";
import {Separator} from "@/components/ui/separator";

// import moment from "moment";

interface Game {
  id: string;
  teams: {
    home: {
      code: string;
      logo: string;
    };
    visitors: {
      code: string;
      logo: string;
    };
  };
  scores: {
    home: {
      points: number;
    };
    visitors: {
      points: number;
    };
  };
}

const Scores = ({showScores}) => {
  const [gameData, setGameData] = useState<Game[]>([]);

  useEffect(() => {
    async function fetchData() {
      // const date = moment(selectedDate)
      // the api returns results a day behind, this adds a day to the selected date to compensate
      // .add(1, "days")
      // .add(5, "hours")
      // .format("YYYY-MM-DD");

      const date = new Date();
      const dd = String(date.getDate()).padStart(2, "0");
      const mm = String(date.getMonth() + 1).padStart(2, "0");
      const yyyy = date.getFullYear();

      const formattedDate = `${yyyy}-${mm}-${dd}`;

      const url = `https://api-nba-v1.p.rapidapi.com/games?date=${formattedDate}`;
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
    }

    fetchData();
  }, []);

  return (
    <div>
      {gameData?.map((game) => {
        return (
          <>
            <div className="flex flex-row justify-evenly mt-2" key={game.id}>
              <div>
                <img
                  src={game.teams.home.logo}
                  width={40}
                  height={40}
                  alt={`${game.teams.home.code} logo`}
                />
                <h2>{showScores ? `${game.scores.home.points}` : "-"}</h2>
              </div>
              <div>
                <img
                  src={game.teams.visitors.logo}
                  width={40}
                  height={40}
                  alt={`${game.teams.visitors.code} logo`}
                />
                <h2>{showScores ? `${game.scores.visitors.points}` : "-"}</h2>
              </div>
            </div>
            <Separator className="h-1 bg-slate-950 w-full" />
          </>
        );
      })}
    </div>
  );
};

export default Scores;
