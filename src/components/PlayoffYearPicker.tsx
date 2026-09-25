import {
  Button,
  ComboBox,
  Group,
  Input,
  Label,
  ListBox,
  ListBoxItem,
  Popover,
} from "react-aria-components";
import ChevronUpDownIcon from "@spectrum-icons/workflow/ChevronUpDown";
import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router";

const current_year = new Date().getFullYear();
const first_playoff_end_year = 1947;
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

interface PlayoffYearPickerProps {
  align?: "left" | "center";
  variant?: "default" | "hardwood";
}

const PICKER_STYLES = {
  default: {
    container: "mt-2 mb-4",
    comboBox: "w-[160px] sm:w-[200px]",
    label: "dark:text-slate-50 text-neutral-950 text-sm sm:text-base",
    labelText: "Playoffs",
    group:
      "rounded-lg bg-white/90 focus-within:bg-white group-open:bg-white transition pl-3 shadow-md text-gray-700 focus-visible:ring-2 ring-black",
    input: "",
    inputAlignment: {left: "", center: ""},
    button: "px-2 sm:px-3 text-gray-700 rounded-r-lg pressed:bg-purple-100",
    popover: "rounded-lg drop-shadow-lg ring-1 ring-black/10 bg-white",
    popoverStyle: undefined,
    listBox: "p-1",
    option:
      "rounded-md cursor-default text-gray-700 hover:bg-gray-100 focus:bg-violet-700 focus:text-white selected:bg-violet-100 selected:font-semibold",
  },
  hardwood: {
    container: "w-full",
    comboBox: "w-full",
    label: "text-[11px] font-extrabold tracking-[.1em] text-hw-ink uppercase",
    labelText: "Season",
    group:
      "rounded-hw bg-hw-surface-muted text-hw-ink focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-hw-accent-ink",
    input: "min-h-11 tabular-nums",
    inputAlignment: {left: "pl-3 pr-11", center: "px-11"},
    button:
      "absolute inset-y-0 right-0 w-11 cursor-pointer justify-center rounded-r-hw text-hw-ink data-hovered:bg-hw-ink/5 data-pressed:bg-hw-ink/10 data-focus-visible:outline-2 data-focus-visible:outline-hw-accent-ink",
    popover:
      "design-hardwood z-50 rounded-hw border border-hw-line font-hw-display text-hw-ink shadow-hw-small",
    popoverStyle: {backgroundColor: "var(--hw-surface)"},
    listBox: "max-h-60 overflow-auto",
    option:
      "min-h-9 cursor-pointer font-sans text-sm font-normal tabular-nums text-hw-ink data-hovered:bg-hw-surface-muted data-focused:bg-hw-surface-muted data-selected:bg-hw-ink data-selected:text-hw-surface dark:data-selected:bg-hw-accent dark:data-selected:text-hw-accent-contrast data-focus-visible:outline-2 data-focus-visible:-outline-offset-2 data-focus-visible:outline-hw-accent-ink",
  },
};

const PlayoffYearPicker = ({align = "left", variant = "default"}: PlayoffYearPickerProps) => {
  const fieldRef = useRef<HTMLDivElement>(null);
  const styles = PICKER_STYLES[variant];
  const alignment = align === "center" ? "text-center" : "text-left";
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
    <div className={`flex justify-center ${styles.container}`}>
      <ComboBox
        selectedKey={String(selectedYear)}
        inputValue={inputValue}
        onInputChange={setInputValue}
        onSelectionChange={handleSelectionChange}
        defaultItems={season_years.map((year) => ({
          id: String(year),
          label: formatSeason(year),
        }))}
        className={`group flex flex-col gap-1 ${styles.comboBox}`}
        menuTrigger="focus"
      >
        <Label className={`cursor-default ${alignment} ${styles.label}`}>
          {styles.labelText}
        </Label>

        <Group
          ref={fieldRef}
          className={`relative flex text-sm sm:text-base outline-none ${styles.group}`}
        >
          <Input
            onBlur={handleCommitInput}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                handleCommitInput();
              }
            }}
            className={`flex flex-1 min-w-0 py-1.5 sm:py-2 bg-transparent outline-none ${alignment} ${styles.input} ${styles.inputAlignment[align]}`}
          />

          <Button className={`flex items-center outline-none ${styles.button}`}>
            <ChevronUpDownIcon size="XS" />
          </Button>
        </Group>

        <Popover
          triggerRef={fieldRef}
          placement="bottom start"
          offset={8}
          className={`w-[var(--trigger-width)] overflow-auto max-h-60 ${styles.popover}`}
          style={styles.popoverStyle}
        >
          <ListBox className={`outline-none ${styles.listBox}`}>
            {(item: { id: string; label: string }) => (
              <ListBoxItem
                key={item.id}
                id={item.id}
                textValue={item.label}
                className={`px-3 py-2 outline-none ${alignment} ${styles.option}`}
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
