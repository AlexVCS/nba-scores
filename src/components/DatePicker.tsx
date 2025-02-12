import {useState} from "react";
import {format} from "date-fns";
import {DayPicker} from "react-day-picker";



function DatePicker({setSearchParams}: SetURLSearchParams) {
  const [calendarOpen, setCalendarOpen] = useState(false);
  const [dateSelected, setDateSelected] = useState<Date>();

  return (
    <DayPicker
      showOutsideDays
      mode="single"
      selected={dateSelected}
      onSelect={(date) => {
        date && setSearchParams({date: format(date, "yyyy-MM-dd")});
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
