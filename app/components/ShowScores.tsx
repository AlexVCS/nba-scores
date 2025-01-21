"use client";

import {useState} from "react";
import {Label} from "@/components/ui/label";
import {Switch} from "@/components/ui/switch";
import {useRouter, usePathname, useSearchParams} from "next/navigation";
import {format, formatISO} from "date-fns";
import {trpc} from "../api/trpc/client";



const ShowScores = ({
  renderScores,
  selectedDate,
  userTimezone,
}: {
  renderScores: string;
  selectedDate: string;
  userTimezone: string;
}) => {
  const [showScores, setShowScores] = useState(false);
  // const [dateSelected, setDateSelected] = useState<Date>();

  const todaysDate = new Date();

  const dateString = selectedDate;
  const year = dateString.substring(0, 4);
  const month = dateString.substring(5, 7);
  const day = dateString.substring(8, 10);

  // var date = selectedDate && new Date(year, month - 1, day);
  // console.log('is this formatted correctly?', date)
  const formattedSelectedDate = new Date(selectedDate);
  // console.log('selected', formattedSelectedDate);
  // Results below assume UTC timezone - your results may vary

  // Specify default date formatting for language (locale)
  // const newThang = new Intl.DateTimeFormat("en-US").format(formattedSelectedDate);
  // Expected output: "12/20/2020"
  // const formatSelectedDate = selectedDate && formatISO(formattedSelectedDate);
  // console.log(formatSelectedDate)
  // console.log("this is what you wanna see after the colon:", newThang);

  const searchParams = useSearchParams();
  const pathname = usePathname();
  const router = useRouter();

  function handleToggleScores() {
    // const params = new URLSearchParams(searchParams)

    const params = new URLSearchParams(Array.from(searchParams.entries()));
    if (showScores) {
      setShowScores(true);
      params.set("renderScores", "true");
    } else {
      setShowScores(false);
      params.set("", "");
    }
    router.replace(`${pathname}?${params.toString()}`);
  }

  // const toggleShowScores = () => {
  //   router.push(`?showscores=true`);
  // };

  // console.log("selectedDate", selectedDate);
  // console.log("todaysDate", todaysDate);

  return (
    <>
      {selectedDate && selectedDate < todaysDate && (
        <div>
          <Switch
            className="mr-2 data-[state=unchecked]:bg-[#E47041] data-[state=checked]:bg-[#E47041]"
            id="show-scores"
            onCheckedChange={handleToggleScores}
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
