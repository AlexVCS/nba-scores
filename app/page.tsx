"use client";

import Image from "next/image";
import {useState, useEffect} from "react";
import DatePicker from "@/app/components/DatePicker";
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

function Home() {
  const [gameData, setGameData] = useState<Game[]>([]);
  const [selectedDate, setSelectedDate] = useState('');

  useEffect(() => {
    async function fetchData() {
      const url = `https://api-nba-v1.p.rapidapi.com/games?date=${selectedDate}`;
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
      // getDate()
      // console.log(gameData)
    }

    fetchData();
  }, [selectedDate]);

  const handleDateChange = (event) => {
    // let dateEntered = new Date(event.target.value);
    // dateEntered.setMinutes(
    //   dateEntered.getMinutes() + dateEntered.getTimezoneOffset()
    // );
    // const year = dateEntered.getFullYear();
    // let month = dateEntered.getMonth() + 1;
    // let day = dateEntered.getDate();

    // month = month < 10 ? `0${month}` : month;
    // day = day < 10 ? `0${day}` : day;
    
    // const newDateString = `${year}-${month}-${day}`;
    const date = moment().format(event.target.value);
    console.log("here is the date", date);
    setSelectedDate(date);
  };

  return (
    <div>
      <h1>NBA Scores</h1>
      <h1>Current Date Selected</h1>
      <h1>Pick the day you want games from</h1>
      <DatePicker value={selectedDate} onChange={handleDateChange} />
      <p>
        Selected Date:{" "}
        {selectedDate ? selectedDate.toLocaleString() : "No date selected"}
      </p>
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
}

export default Home;
