"use client"

import {useState} from "react";
import {Label} from "@/components/ui/label";
import {Switch} from "@/components/ui/switch";
import { useRouter } from "next/navigation";

const ShowScores = () => {
  const [showScores, setShowScores] = useState(false);
  const [dateSelected, setDateSelected] = useState<Date>();

  const todaysDate = new Date();
  const router = useRouter();


  const toggleShowScores = () => {
    setShowScores(!showScores);
    router.push(`?showscores=true`)
  }


  return (
    <>
      {dateSelected && dateSelected < todaysDate && (
        <div>
          <Switch
            className="mr-2 data-[state=unchecked]:bg-[#E47041] data-[state=checked]:bg-[#E47041]"
            id="show-scores"
            onCheckedChange={toggleShowScores}
          />
          <Label htmlFor="show-scores">
            {showScores ? "Hide Scores" : "Show Scores"}
          </Label>
        </div>
      )}
    </>
  );
};

export default ShowScores;
