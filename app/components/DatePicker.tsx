"use client";

import {useCallback, useState} from "react";
import {format} from "date-fns";
import {Calendar as CalendarIcon} from "lucide-react";
import {cn} from "@/lib/utils";
import {Button} from "@/components/ui/button";
import {Calendar} from "@/components/ui/calendar";
import {Popover, PopoverContent, PopoverTrigger} from "@/components/ui/popover";
import {usePathname, useRouter, useSearchParams} from "next/navigation";

function DatePicker() {
  const [calendarOpen, setCalendarOpen] = useState(false);
  const [dateSelected, setDateSelected] = useState<Date>();

  const searchParams = useSearchParams();
  const pathname = usePathname();
  const router = useRouter();

  // const createQueryString = useCallback(
  //   (dateSelected: string | number | Date) => {
  //     const params = new URLSearchParams(searchParams.toString());

  //     const formattedDate = format(dateSelected, "yyyy-MM-dd");
  //     params.set("selectedDate", formattedDate);
  //     return params.toString();
  //   },
  //   [searchParams]
  // )

  function handleSelectedDate(dateSelected: Date | undefined) {
    // const params = new URLSearchParams(searchParams)

    const params = new URLSearchParams(Array.from(searchParams.entries()));
    if (dateSelected) {
      const formattedDate = format(dateSelected, "yyyy-MM-dd");
      params.set("selectedDate", formattedDate);
    } else {
      params.set("", "");
    }
    router.replace(`${pathname}?${params.toString()}`);
  }

  return (
    <div className="mb-4">
      <Popover open={calendarOpen} onOpenChange={setCalendarOpen}>
        <PopoverTrigger asChild>
          <Button
            variant={"outline"}
            className={cn(
              "w-[280px] justify-start items-center text-left font-normal",
              !dateSelected && "text-muted-foreground"
            )}
          >
            <CalendarIcon className="mr-2 h-4 w-4" />
            {dateSelected ? (
              format(dateSelected, "PPP")
            ) : (
              <span>Pick a date</span>
            )}
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-auto p-0">
          <Calendar
            mode="single"
            selected={dateSelected}
            onSelect={(date) => {
              // router.push(
              //   pathname + "?" + createQueryString('dateSelected')
              // );
              handleSelectedDate(date)
              setDateSelected(date);
              setCalendarOpen(false);
            }}
            initialFocus
          />
        </PopoverContent>
      </Popover>
    </div>
  );
}

export default DatePicker;
