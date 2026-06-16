import {
  Button,
  ComboBox,
  Input,
  Label,
  ListBox,
  ListBoxItem,
  Popover,
} from "react-aria-components";
import ChevronUpDownIcon from "@spectrum-icons/workflow/ChevronUpDown";
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router";

const current_year = new Date().getFullYear();
const first_playoff_end_year = 1951;
const playoff_start_month = 3; // April (0-indexed)
const playoff_start_day = 15;

const getDefaultPlayoffEndYear = (date = new Date()) => {
  const year = date.getFullYear();

  const playoffStartDate = new Date(
    year,
    playoff_start_month,
    playoff_start_day,
  );

  return date >= playoffStartDate ? year : year - 1;
};

const default_playoff_end_year = getDefaultPlayoffEndYear();

const season_years = Array.from(
  { length: current_year - first_playoff_end_year + 1 },
  (_, i) => first_playoff_end_year + i,
).reverse();

const formatSeason = (year: number) =>
  `${year - 1}-${String(year).slice(-2)}`;

const parseSeasonInput = (value: string): number | null => {
  const trimmed = value.trim();

  const rangeMatch = trimmed.match(/^(\d{4})-(\d{2})$/);

  if (rangeMatch) {
    const startYear = Number(rangeMatch[1]);
    const endYearSuffix = Number(rangeMatch[2]);
    const century = Math.floor(startYear / 100) * 100;

    let endYear = century + endYearSuffix;

    if (endYear < startYear) {
      endYear += 100;
    }

    return endYear;
  }

  const yearMatch = trimmed.match(/^\d{4}$/);

  if (yearMatch) {
    return Number(trimmed);
  }

  return null;
};

const PlayoffYearPicker = () => {
  const [searchParams, setSearchParams] = useSearchParams();

  const seasonParam = searchParams.get("season") ?? "";

  const endYear = parseSeasonInput(seasonParam) || default_playoff_end_year;

  const selectedYear = season_years.includes(endYear) ? endYear : default_playoff_end_year;

  const [inputValue, setInputValue] = useState(formatSeason(selectedYear));

  useEffect(() => {
    setInputValue(formatSeason(selectedYear));
  }, [selectedYear]);

  const setSeason = (year: number) => {
    setInputValue(formatSeason(year));

    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.set("season", formatSeason(year));
      return next;
    });
  };

  const handleSelectionChange = (key: React.Key | null) => {
    if (key === null) return;

    setSeason(Number(key));
  };

  const handleCommitInput = () => {
    const parsedYear = parseSeasonInput(inputValue);

    if (parsedYear) {
      setSeason(parsedYear);
      return;
    }

    setInputValue(formatSeason(selectedYear));
  };

  return (
    <div className="flex justify-center mt-2 mb-4">
      <ComboBox
        selectedKey={String(selectedYear)}
        inputValue={inputValue}
        onInputChange={setInputValue}
        onSelectionChange={handleSelectionChange}
        defaultItems={season_years.map((year) => ({
          id: String(year),
          label: formatSeason(year),
        }))}
        className="group flex flex-col gap-1 w-[160px] sm:w-[200px]"
        menuTrigger="focus"
      >
        <Label className="cursor-default dark:text-slate-50 text-neutral-950 text-sm sm:text-base">
          Playoff Season
        </Label>

        <div className="flex rounded-lg bg-white/90 focus-within:bg-white group-open:bg-white transition pl-3 shadow-md text-gray-700 text-sm sm:text-base focus-visible:ring-2 ring-black outline-none">
          <Input
            onBlur={handleCommitInput}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                handleCommitInput();
              }
            }}
            className="flex flex-1 min-w-0 py-1.5 sm:py-2 text-left bg-transparent outline-none"
          />

          <Button className="px-2 sm:px-3 flex items-center text-gray-700 rounded-r-lg pressed:bg-purple-100 outline-none">
            <ChevronUpDownIcon size="XS" />
          </Button>
        </div>

        <Popover className="w-[--trigger-width] overflow-auto rounded-lg drop-shadow-lg ring-1 ring-black/10 bg-white max-h-60">
          <ListBox className="outline-none p-1">
            {(item: { id: string; label: string }) => (
              <ListBoxItem
                key={item.id}
                id={item.id}
                textValue={item.label}
                className="px-3 py-2 rounded-md cursor-default outline-none text-gray-700 hover:bg-gray-100 focus:bg-violet-700 focus:text-white selected:bg-violet-100 selected:font-semibold"
              >
                {item.label}
              </ListBoxItem>
            )}
          </ListBox>
        </Popover>
      </ComboBox>
    </div>
  );
};

export default PlayoffYearPicker;
