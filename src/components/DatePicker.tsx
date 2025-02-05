import {useState} from "react";
import {format} from "date-fns";
import {DayPicker} from "react-day-picker";

function DatePicker({setSearchParams}: SetURLSearchParams) {
  const [calendarOpen, setCalendarOpen] = useState(false);
  const [dateSelected, setDateSelected] = useState<Date>();

  return (
    // <div className="mb-4">
    //   <Popover open={calendarOpen} onOpenChange={setCalendarOpen}>
    //     <PopoverTrigger asChild>
    //       <Button
    //         variant={"outline"}
    //         className={cn(
    //           "w-[280px] justify-start items-center text-left font-normal",
    //           !dateSelected && "text-muted-foreground"
    //         )}
    //       >
    //         <CalendarIcon className="w-4 h-4 mr-2" />
    //         {dateSelected ? (
    //           format(dateSelected, "PPP")
    //         ) : (
    //           <span>Pick a date</span>
    //         )}
    //       </Button>
    //     </PopoverTrigger>
    //     <PopoverContent className="w-auto p-0">
    //       <Calendar
    //         mode="single"
    //         selected={dateSelected}
    //         onSelect={(date) => {
    //           // router.push(
    //           //   pathname + "?" + createQueryString('dateSelected')
    //           // );
    //           handleSelectedDate(date);
    //           setDateSelected(date);
    //           setCalendarOpen(false);
    //         }}
    //         initialFocus
    //       />
    //     </PopoverContent>
    //   </Popover>
    // </div>

    <DayPicker
      showOutsideDays
      mode="single"
      selected={dateSelected}
      onSelect={(date) => {
        date && setSearchParams({date: format(date, "yyyy-MM-dd")});

        // setSearchParams(date => {
        //   date.set("date", date.toString());
        //   console.log(searchParams)
        //   return searchParams
        // });
        setCalendarOpen(false);
      }}
      footer={
        dateSelected
          ? `Selected: ${dateSelected.toLocaleDateString()}`
          : "Pick a day."
      }
    />
  );
}

export default DatePicker;
