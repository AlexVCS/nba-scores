"use client";

import Scores from "@/app/components/Scores";
import {useState} from "react";
import {Label} from "@/components/ui/label";
import {Switch} from "@/components/ui/switch";

function Home() {
  // const [datePickerValue, setDatePickerValue] = useState("");
  const [showScores, setShowScores] = useState(false);

  const date = new Date();

  return (
    <div className="text-center flex flex-col">
      <h1>NBA Scores</h1>
      <div>Today is {date.toDateString().toString()}</div>
      <div>
        <Switch
          className="mr-2 data-[state=unchecked]:bg-[#E47041] data-[state=checked]:bg-[#E47041]"
          id="show-scores"
          onCheckedChange={() => setShowScores(!showScores)}
        />
        <Label htmlFor="show-scores">
          {showScores ? "Hide Scores" : "Show Scores"}
        </Label>
      </div>
      <Scores date={date} showScores={showScores} />
    </div>
  );
}

export default Home;
