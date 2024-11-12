"use client";

import {useState} from "react";
import {format} from "date-fns";
import {Calendar as CalendarIcon} from "lucide-react";
import {cn} from "@/lib/utils";
import {Button} from "@/components/ui/button";
import {Calendar} from "@/components/ui/calendar";
import {Popover, PopoverContent, PopoverTrigger} from "@/components/ui/popover";

interface DatePickerProps {
  dateSelectedProp?: Date;
}

function DatePicker({ dateSelectedProp }: DatePickerProps) {
  const [dateSelected, setDateSelected] = useState<Date>();
  const [calendarOpen, setCalendarOpen] = useState(false);

  return (
    <Popover open={calendarOpen} onOpenChange={setCalendarOpen}>
      <PopoverTrigger className="flex content-center" asChild>
        <Button
          variant={"outline"}
          className={cn(
            "w-[280px] justify-start text-left font-normal",
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
      {/* {date && <div>{date.toLocaleDateString()}</div>} */}
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
  );
}

export default DatePicker;
