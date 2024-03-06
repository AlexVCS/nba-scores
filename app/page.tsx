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
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [datePickerValue, setDatePickerValue] = useState('')

  useEffect(() => {
    async function fetchData() {
      console.log("calling API with", selectedDate);
      const date = moment(selectedDate)
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
      console.log("Fetched game data:", jsonRes.response);
      setGameData(jsonRes.response);
      // getDate()
      // console.log(gameData)
    }

    fetchData();
  }, [selectedDate]);

  const handleDateChange = (event) => {
    console.log("this is the event value", typeof event.target.value);
    const utcDate = new Date(event.target.value);
    // the api returns results a day behind, this adds a day to the selected date to compensate
    // console.log(date)
    setSelectedDate(utcDate);
    setDatePickerValue(event.target.value)
    // const formattedDate = utcDate.format("YYYY-MM-DD");
    // const properDate = utcDate.setUTCHours(8)

    // console.log('this is the proper date', properDate)
    // const dateWTime= `${event.target.value}T13:00:00`;
    // console.log("here is the date", formattedDate);
    // const utcDate = moment.utc(event.target.value);
    // const localDate = utcDate.local();
    // const formattedDate = localDate.format("YYYY-MM-DD");
    // console.log("Here is the local date:", localDate);
    // setSelectedDate(formattedDate);
  };

  return (
    <div>
      <h1>NBA Scores</h1>
      <h1>Current Date Selected</h1>
      <h1>Pick the day you want games from</h1>
      <DatePicker
        value={datePickerValue}
        onChange={handleDateChange}
      />
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
