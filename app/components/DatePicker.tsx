"use client";

import {Dispatch, SetStateAction, useState} from "react";
import {format} from "date-fns";
import {Calendar as CalendarIcon} from "lucide-react";
import {cn} from "@/lib/utils";
import {Button} from "@/components/ui/button";
import {Calendar} from "@/components/ui/calendar";
import {Popover, PopoverContent, PopoverTrigger} from "@/components/ui/popover";

interface DatePickerProps {
  dateSelected?: Date;
  setDateSelected: Dispatch<SetStateAction<Date | undefined>>;
}

function DatePicker({dateSelected, setDateSelected}: DatePickerProps) {
  const [calendarOpen, setCalendarOpen] = useState(false);

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
