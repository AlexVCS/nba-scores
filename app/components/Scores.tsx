"use client";

// import Image from "next/image";
import {useState, useEffect} from "react";
import {Separator} from "@/components/ui/separator";
import {error} from "console";

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

interface Scores {
  date: Date;
  showScores: boolean;
}

const Scores = ({showScores, date}: Scores) => {
  const [gameData, setGameData] = useState<Game[]>([]);

  useEffect(() => {
    async function fetchData() {
      // const date = moment(selectedDate)
      // the api returns results a day behind, this adds a day to the selected date to compensate
      // .add(1, "days")
      // .add(5, "hours")
      // .format("YYYY-MM-DD");
      try {
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
      } catch (error) {
        if (error) {
          throw new Error("Unable to get scores", error);
        }
      }
    }

    fetchData();
  }, []);

  function noImage(event: React.SyntheticEvent<HTMLImageElement, Event>) {
    event.currentTarget.src = "https://placehold.co/48x48?text=No+logo";
  }

  return (
    <div>
      {gameData?.map((game) => {
        return (
          <>
            <div className="flex flex-row justify-evenly mt-2" key={game.id}>
              <div>
                <img
                  src={game.teams.home.logo}
                  onError={noImage}
                  className="object-contain w-12 h-12"
                  alt={`${game.teams.home.code} logo`}
                />
                <p className="mt-2">{game.teams.home.code}</p>
                <h2 className="mb-2">
                  {showScores ? `${game.scores.home.points}` : "-"}
                </h2>
              </div>
              <div>
                <img
                  src={game.teams.visitors.logo}
                  onError={noImage}
                  className="object-contain w-12 h-12"
                  alt={`${game.teams.visitors.code} logo`}
                />
                <p className="mt-2">{game.teams.visitors.code}</p>
                <h2 className="mb-2">
                  {showScores ? `${game.scores.visitors.points}` : "-"}
                </h2>
              </div>
            </div>
            <Separator className="h-1 bg-slate-950 w-full last:hidden" />
          </>
        );
      })}
    </div>
  );
};

export default Scores;
