"use client";

// import Image from "next/image";
import {Fragment, useState, useEffect} from "react";
import {Separator} from "@/components/ui/separator";
import DatePicker from "@/app/components/DatePicker";
import {format} from "date-fns";

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
  todaysDate: Date;
  showScores: boolean;
  dateSelected: Date;
}

const Scores = ({showScores, todaysDate, dateSelected}: Scores) => {
  const [gameData, setGameData] = useState<Game[]>([]);
  const [formattedDate, setFormattedDate] = useState<Date | String>('');

  useEffect(() => {
    async function fetchData() {
      // const date = moment(selectedDate)
      // the api returns results a day behind, this adds a day to the selected date to compensate
      // .add(1, "days")
      // .add(5, "hours")
      // .format("YYYY-MM-DD");
      try {
        let url: string;
        console.log(dateSelected)
        if (dateSelected != null) {
          setFormattedDate(format(
            dateSelected,
            "YYYY-MM-DD"
          ))
          url = `https://api-nba-v1.p.rapidapi.com/games?date=${formattedDate}`;
        } else {
          const dd = String(todaysDate.getDate()).padStart(2, "0");
          const mm = String(todaysDate.getMonth() + 1).padStart(2, "0");
          const yyyy = todaysDate.getFullYear();
          const today = `${yyyy}-${mm}-${dd}`;
          setFormattedDate(today)

          url = `https://api-nba-v1.p.rapidapi.com/games?date=${formattedDate}`;
        }
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
  });

  function noImage(event: React.SyntheticEvent<HTMLImageElement, Event>) {
    event.currentTarget.src = "https://placehold.co/48x48?text=No+logo";
  }

  return (
    <div>
      <DatePicker dateSelectedProp={dateSelected} />
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
          </Fragment>
        );
      })}
    </div>
  );
};

export default Scores;
