import {useMemo} from "react";
import {useQueries} from "@tanstack/react-query";
import {Link} from "react-router-dom";
import {getDefaultPlayoffSeason} from "@/helpers/helpers";
import {getGameDays} from "@/services/nbaService";

interface NoGamesQuickLinksProps {
  today?: Date;
  randomIndex?: number;
}

interface QuickLink {
  label: string;
  detail?: string;
  to: string;
}

const formatDateParam = (date: Date): string => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
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

function NoGamesQuickLinks({today = new Date(), randomIndex}: NoGamesQuickLinksProps) {
  const recentMonths = useMemo(() => getRecentMonths(today), [today]);
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

  const yesterday = useMemo(() => {
    const date = new Date(today);
    date.setDate(date.getDate() - 1);
    return formatDateParam(date);
  }, [today]);

  const availableGameDays = useMemo(() => {
    const todayParam = formatDateParam(today);

    return gameDayQueries
      .flatMap((query) => query.data?.game_days ?? [])
      .filter((dateParam) => dateParam < todayParam)
      .sort((a, b) => b.localeCompare(a));
  }, [gameDayQueries, today]);

  const lastGameDay = availableGameDays[0] ?? yesterday;

  const randomGameDay = useMemo(() => {
    return pickRandomDate(availableGameDays, lastGameDay, randomIndex);
  }, [availableGameDays, lastGameDay, randomIndex]);

  const currentPlayoffSeason = getDefaultPlayoffSeason(today);

  const quickLinks: QuickLink[] = [
    {
      label: "Yesterday",
      detail: formatShortDate(yesterday),
      to: `/?date=${yesterday}`,
    },
    {
      label: "Last Game Day",
      detail: formatShortDate(lastGameDay),
      to: `/?date=${lastGameDay}`,
    },
    {
      label: "Random Game Day",
      to: `/?date=${randomGameDay}`,
    },
    {
      label: "Last Playoffs",
      detail: currentPlayoffSeason,
      to: `/playoffs?season=${currentPlayoffSeason}`,
    },
  ];

  return (
    <section className="px-4 py-6">
      <div className="relative isolate mx-auto max-w-3xl overflow-visible rounded-lg border border-slate-200 bg-white/85 p-4 shadow-sm shadow-slate-200/70 dark:border-neutral-800 dark:bg-neutral-900/80 dark:shadow-none sm:p-5">
        <div className="relative z-10 border-b border-slate-200 pb-4 text-center dark:border-neutral-800">
          <h2 className="relative z-10 text-2xl font-bold text-neutral-950 dark:text-slate-50">
            No games today
          </h2>
          <p className="relative z-10 mt-1 text-sm text-slate-600 dark:text-slate-300">
            Try another night.
          </p>
        </div>
        <div className="relative z-10 mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {quickLinks.map(({label, detail, to}) => (
            <Link
              key={`${label}-${to}`}
              to={to}
              className="group flex min-h-20 flex-col justify-center rounded-md border border-slate-200 bg-slate-50 px-4 py-3 text-left transition hover:-translate-y-0.5 hover:border-blue-300 hover:bg-white hover:shadow-md hover:shadow-blue-100/70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 dark:border-neutral-800 dark:bg-neutral-950 dark:hover:border-amber-400/70 dark:hover:bg-neutral-900 dark:hover:shadow-none dark:focus-visible:ring-amber-400 dark:focus-visible:ring-offset-neutral-950"
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
