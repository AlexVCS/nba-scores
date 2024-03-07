"use client"

import DatePicker from "@/app/components/DatePicker";
import Scores from "@/app/components/Scores";
import { useState } from "react";

function Home() {
  const [datePickerValue, setDatePickerValue] = useState("");
  const [selectedDate, setSelectedDate] = useState(new Date());

  return (
    <div>
      <h1>NBA Scores</h1>
      <h1>Current Date Selected</h1>
      <h1>Pick the day you want games from</h1>
      <DatePicker
        setSelectedDate={setSelectedDate}
        datePickerValue={datePickerValue}
        setDatePickerValue={setDatePickerValue}
      />
      <Scores selectedDate={selectedDate} />
    </div>
  );
}

export default Home;
