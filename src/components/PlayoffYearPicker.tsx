import {
  Button,
  Label,
  ListBox,
  ListBoxItem,
  Popover,
  Select,
  SelectValue,
} from "react-aria-components";
import ChevronUpDownIcon from "@spectrum-icons/workflow/ChevronUpDown";
import { useSearchParams } from "react-router";

const toSeasonId = (endYear: number) => `2${endYear}`;

const CURRENT_YEAR = new Date().getFullYear();

const SEASON_YEARS = Array.from(
  { length: CURRENT_YEAR - 2000 + 1 },
  (_, i) => 2001 + i,
).reverse();

const PlayoffYearPicker = () => {
  const [searchParams, setSearchParams] = useSearchParams();

  const rawParam = searchParams.get("seasonId") ?? "";
  const endYear =
    rawParam.length === 5
      ? Number(rawParam.slice(1))
      : Number(rawParam) || CURRENT_YEAR;

  const handleChange = (key: React.Key) => {
    setSearchParams({ seasonId: toSeasonId(Number(key)) });
  };

  return (
    <div className="flex justify-center mt-2 mb-4">
      <Select
        selectedKey={String(endYear)}
        onSelectionChange={handleChange}
        className="group flex flex-col gap-1 w-[200px]"
      >
        <Label className="cursor-default dark:text-slate-50 text-neutral-950">
          Playoff Season
        </Label>
        <Button className="flex rounded-lg bg-white/90 focus-within:bg-white group-open:bg-white transition pl-3 shadow-md text-gray-700 focus-visible:ring-2 ring-black outline-none">
          <SelectValue className="flex flex-1 py-2 text-left">
            {({ selectedText }) => {
              const year = SEASON_YEARS.find(
                (y) =>
                  `${y - 1}-${String(y).slice(-2)} Playoffs` === selectedText,
              );
              return year
                ? `${year - 1}-${String(year).slice(-2)}`
                : "Select season";
            }}
          </SelectValue>
          <span className="px-3 flex items-center text-gray-700 border-0 border-solid border-l border-l-purple-200 rounded-r-lg pressed:bg-purple-100">
            <ChevronUpDownIcon size="XS" />
          </span>
        </Button>
        <Popover className="w-[--trigger-width] overflow-auto rounded-lg drop-shadow-lg ring-1 ring-black/10 bg-white max-h-60">
          <ListBox className="outline-none p-1">
            {SEASON_YEARS.map((year) => (
              <ListBoxItem
                key={year}
                id={String(year)}
                className="px-3 py-2 rounded-md cursor-default outline-none text-gray-700 hover:bg-gray-100 focus:bg-violet-700 focus:text-white selected:bg-violet-100 selected:font-semibold"
              >
                {`${year - 1}-${String(year).slice(-2)} Playoffs`}
              </ListBoxItem>
            ))}
          </ListBox>
        </Popover>
      </Select>
    </div>
  );
};

export default PlayoffYearPicker;
