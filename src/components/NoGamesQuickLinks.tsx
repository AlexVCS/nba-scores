import {Link} from "react-router-dom";
import {getDefaultPlayoffSeason} from "@/helpers/helpers";
import {useRandomGameDay} from "@/hooks/useRandomGameDay";

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

const formatShortDate = (dateParam: string): string => {
  const [year, month, day] = dateParam.split("-").map(Number);
  return new Date(year, month - 1, day).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
};

function NoGamesQuickLinks({
  today,
  randomIndex,
  selectedDateParam,
}: NoGamesQuickLinksProps) {
  const {
    activeDate,
    lastGameDay,
    previousDate,
    randomGameDay,
    selectedDate,
  } = useRandomGameDay({dateParam: selectedDateParam, randomIndex, today});
  const selectedDateLabel = selectedDate
    ? formatShortDate(selectedDateParam!)
    : undefined;

  const currentPlayoffSeason = getDefaultPlayoffSeason(activeDate);

  const quickLinks: QuickLink[] = [
    {
      label: "Yesterday",
      detail: formatShortDate(previousDate),
      to: `/?date=${previousDate}`,
    },
    {
      label: "Last Game of the Season",
      detail: formatShortDate(lastGameDay),
      to: `/?date=${lastGameDay}`,
    },
    {
      label: "Random Game Day",
      to: `/?date=${randomGameDay ?? lastGameDay}`,
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
