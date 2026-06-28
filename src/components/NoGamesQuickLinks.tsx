import {useMemo} from "react";
import {useQueries} from "@tanstack/react-query";
import {Link} from "react-router-dom";
import {getDefaultPlayoffSeason} from "@/helpers/helpers";
import {getGameDays} from "@/services/nbaService";

interface NoGamesQuickLinksProps {
  today?: Date;
  randomIndex?: number;
  selectedDateParam?: string;
}

interface QuickLink {
  label: string;
  detail?: string;
  to: string;
}

const GAME_DAYS_MIN_YEAR = 2000;
const GAME_DAYS_MAX_YEAR = 2100;

const formatDateParam = (date: Date): string => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

const isSupportedGameDaysYear = (date: Date): boolean => {
  const year = date.getFullYear();
  return year >= GAME_DAYS_MIN_YEAR && year <= GAME_DAYS_MAX_YEAR;
};

const parseDateParam = (dateParam: string): Date | undefined => {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(dateParam);
  if (!match) return undefined;

  const [, year, month, day] = match;
  const date = new Date(Number(year), Number(month) - 1, Number(day));

  if (formatDateParam(date) !== dateParam) return undefined;
  return date;
};

const getRecentMonths = (date: Date, count = 12): Date[] =>
  Array.from({length: count}, (_, index) => {
    const month = new Date(date);
    month.setDate(1);
    month.setMonth(month.getMonth() - index);
    return month;
  });

const formatShortDate = (dateParam: string): string => {
  const [year, month, day] = dateParam.split("-").map(Number);
  return new Date(year, month - 1, day).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
};

const pickRandomDate = (
  dates: string[],
  fallbackDate: string,
  randomIndex?: number,
): string => {
  if (dates.length === 0) return fallbackDate;

  const index = randomIndex ?? Math.floor(Math.random() * dates.length);
  return dates[Math.abs(index) % dates.length];
};

function NoGamesQuickLinks({
  today = new Date(),
  randomIndex,
  selectedDateParam,
}: NoGamesQuickLinksProps) {
  const selectedDate = useMemo(
    () => parseDateParam(selectedDateParam ?? ""),
    [selectedDateParam],
  );
  const activeDate = useMemo(
    () => selectedDate ?? today,
    [selectedDate, today],
  );
  const activeDateSupportsGameDays = isSupportedGameDaysYear(activeDate);
  const selectedDateLabel = selectedDate
    ? formatShortDate(formatDateParam(selectedDate))
    : undefined;
  const recentMonths = useMemo(
    () => activeDateSupportsGameDays
      ? getRecentMonths(activeDate).filter(isSupportedGameDaysYear)
      : [],
    [activeDate, activeDateSupportsGameDays],
  );
  const gameDayQueries = useQueries({
    queries: recentMonths.map((month) => {
      const year = month.getFullYear();
      const monthNumber = month.getMonth() + 1;

      return {
        queryKey: ["gameDays", year, monthNumber],
        queryFn: () => getGameDays(year, monthNumber),
        staleTime: 1000 * 60 * 60,
        gcTime: 1000 * 60 * 60 * 24,
      };
    }),
  });

  const previousDateParam = useMemo(() => {
    const date = new Date(activeDate);
    date.setDate(date.getDate() - 1);
    return formatDateParam(date);
  }, [activeDate]);

  const availableGameDays = useMemo(() => {
    const activeDateParam = formatDateParam(activeDate);

    return gameDayQueries
      .flatMap((query) => query.data?.game_days ?? [])
      .filter((dateParam) => dateParam < activeDateParam)
      .sort((a, b) => b.localeCompare(a));
  }, [gameDayQueries, activeDate]);

  const lastGameDay = availableGameDays[0] ?? previousDateParam;

  const randomGameDay = useMemo(() => {
    return pickRandomDate(availableGameDays, lastGameDay, randomIndex);
  }, [availableGameDays, lastGameDay, randomIndex]);

  const currentPlayoffSeason = getDefaultPlayoffSeason(activeDate);

  const quickLinks: QuickLink[] = [
    {
      label: "Yesterday",
      detail: formatShortDate(previousDateParam),
      to: `/?date=${previousDateParam}`,
    },
    {
      label: "Last Game of the Season",
      detail: formatShortDate(lastGameDay),
      to: `/?date=${lastGameDay}`,
    },
    {
      label: "Random Game Day",
      to: `/?date=${randomGameDay}`,
    },
    {
      label: "Year's Playoffs",
      detail: currentPlayoffSeason,
      to: `/playoffs?season=${currentPlayoffSeason}`,
    },
  ];

  return (
    <section className="px-4 py-6">
      <div className="relative isolate mx-auto max-w-3xl overflow-visible p-4 sm:p-5">
        <div className="relative z-10 pb-4 text-center">
          <h2 className="relative z-10 text-2xl font-bold text-neutral-950 dark:text-slate-50">
            {selectedDateLabel
              ? `No games on ${selectedDateLabel}`
              : "No games today"}
          </h2>
          <p className="relative z-10 mt-1 text-sm text-slate-600 dark:text-slate-300">
            Try another night.
          </p>
        </div>
        <div className="relative z-10 mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
          {quickLinks.map(({label, detail, to}) => (
            <Link
              key={`${label}-${to}`}
              to={to}
              className="flex min-h-20 flex-col items-center justify-center rounded-md border border-slate-200 bg-white px-4 py-3 text-center transition-colors hover:border-blue-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:border-neutral-800 dark:bg-neutral-950 dark:hover:border-amber-400 dark:focus-visible:ring-amber-400"
            >
              <span className="min-w-0">
                <span className="block text-sm font-semibold text-neutral-950 dark:text-slate-50">
                  {label}
                </span>
                <span className="mt-0.5 block min-h-4 text-xs text-slate-600 dark:text-slate-400">
                  {detail}
                </span>
              </span>
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}

export default NoGamesQuickLinks;
