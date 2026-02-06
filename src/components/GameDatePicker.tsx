import {
  Button,
  Calendar,
  CalendarCell,
  CalendarGrid,
  CalendarGridBody,
  CalendarGridHeader,
  CalendarHeaderCell,
  DateInput,
  DatePicker,
  DateSegment,
  Dialog,
  Group,
  Heading,
  Label,
  Popover,
} from "react-aria-components";
import type {ButtonProps, DateValue, PopoverProps} from "react-aria-components";
import type {CalendarDate} from "@internationalized/date";
import ChevronUpDownIcon from "@spectrum-icons/workflow/ChevronUpDown";
import {useState, useCallback} from "react";
import {format} from "date-fns";
import {useSearchParams} from "react-router";
import {today, getLocalTimeZone} from "@internationalized/date";
import {useGameDays} from "@/hooks/useGameDays";

const GameDatePicker = () => {
  const [dateSelected, setDateSelected] = useState<DateValue | null>(null);
  const [, setSearchParams] = useSearchParams({date: ""});
  
  const now = today(getLocalTimeZone());
  const [focusedDate, setFocusedDate] = useState<CalendarDate>(now);
  
  const {gameDays, isLoading} = useGameDays(focusedDate.year, focusedDate.month);

  const handleDateChange = (date: DateValue | null) => {
    setDateSelected(date);
    if (date) {
      const jsDate = new Date(date.toString());
      const timezoneOffset = jsDate.getTimezoneOffset() * 60000;
      const localDate = new Date(jsDate.getTime() + timezoneOffset);
    
      setSearchParams({date: format(localDate, "yyyy-MM-dd")});
    }
  };

  const handleFocusChange = (date: CalendarDate) => {
    setFocusedDate(date);
  };

  const isDateUnavailable = useCallback((date: DateValue): boolean => {
    if (isLoading) return false;
    const dateStr = date.toString();
    return !gameDays.has(dateStr);
  }, [gameDays, isLoading]);

  return (
    <div className="flex justify-center mt-2 mb-4">
      <DatePicker
        value={dateSelected}
        onChange={handleDateChange}
        className="group flex flex-col gap-1 w-[200px]"
      >
        <Label className="cursor-default dark:text-slate-50 text-neutral-950">
          Date
        </Label>
        <Group className="flex rounded-lg bg-white/90 focus-within:bg-white group-open:bg-white transition pl-3 shadow-md text-gray-700 focus-visible:ring-2 ring-black">
          <DateInput className="flex flex-1 py-2">
            {(segment) => (
              <DateSegment
                segment={segment}
                className="px-0.5 tabular-nums outline-none rounded-sm focus:bg-violet-700 focus:text-white caret-transparent placeholder-shown:italic"
              />
            )}
          </DateInput>
          <Button className="outline-none px-3 flex items-center text-gray-700 transition border-0 border-solid border-l border-l-purple-200 bg-transparent rounded-r-lg pressed:bg-purple-100 focus-visible:ring-2 ring-black">
            <ChevronUpDownIcon size="XS" />
          </Button>
        </Group>
        <MyPopover>
          <Dialog className="p-6 text-gray-600">
            <Calendar
              value={dateSelected}
              onChange={handleDateChange}
              focusedValue={focusedDate}
              onFocusChange={handleFocusChange}
              isDateUnavailable={isDateUnavailable}
            >
              <header className="flex items-center gap-1 pb-4 px-1 font-serif w-full">
                <Heading className="flex-1 font-semibold text-2xl ml-2" />
                <RoundButton slot="previous">
                  <span className="block text-lg font-bold">&larr;</span>
                </RoundButton>
                <RoundButton slot="next">
                  <span className="block text-lg font-bold">&rarr;</span>
                </RoundButton>
              </header>
              <CalendarGrid className="border-spacing-1 border-separate">
                <CalendarGridHeader>
                  {(day) => (
                    <CalendarHeaderCell className="text-xs text-gray-500 font-semibold">
                      {day}
                    </CalendarHeaderCell>
                  )}
                </CalendarGridHeader>
                <CalendarGridBody>
                  {(date) => (
                    <CalendarCell
                      date={date}
                      className="w-9 h-9 outline-none cursor-default rounded-full flex items-center justify-center outside-month:text-gray-300 hover:bg-gray-100 pressed:bg-gray-200 selected:bg-violet-700 selected:text-white focus-visible:ring ring-violet-600/70 ring-offset-2 [&[data-unavailable]]:text-gray-300 [&[data-unavailable]]:line-through [&[data-unavailable]]:cursor-not-allowed"
                    />
                  )}
                </CalendarGridBody>
              </CalendarGrid>
            </Calendar>
          </Dialog>
        </MyPopover>
      </DatePicker>
    </div>
  );
};

function RoundButton(props: ButtonProps) {
  return (
    <Button
      {...props}
      className="w-9 h-9 outline-none cursor-default bg-transparent text-gray-600 border-0 rounded-full flex items-center justify-center hover:bg-gray-100 pressed:bg-gray-200 focus-visible:ring ring-violet-600/70 ring-offset-2"
    />
  );
}

function MyPopover(props: PopoverProps) {
  return (
    <Popover
      {...props}
      className={({isEntering, isExiting}) => `
        overflow-auto rounded-lg drop-shadow-lg ring-1 ring-black/10 bg-white
        ${
          isEntering
            ? "animate-in fade-in placement-bottom:slide-in-from-top-1 placement-top:slide-in-from-bottom-1 ease-out duration-200"
            : ""
        }
        ${
          isExiting
            ? "animate-out fade-out placement-bottom:slide-out-to-top-1 placement-top:slide-out-to-bottom-1 ease-in duration-150"
            : ""
        }
      `}
    />
  );
}

export default GameDatePicker;
