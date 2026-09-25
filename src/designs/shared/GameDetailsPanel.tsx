import TeamLogos from "@/components/TeamLogos";
import type {useBoxscorePage} from "../hooks/useBoxscorePage";

interface GameDetailsPanelProps {
  state: ReturnType<typeof useBoxscorePage>;
  hardwood?: boolean;
}

function GameDetailsPanel({state, hardwood = false}: GameDetailsPanelProps) {
  const {details, isHidden, isPregame, isLoading, isError, isUnavailable, reveal, retry} = state;
  const surface = hardwood ? "border-hw-line divide-hw-line bg-hw-surface" : "border-neutral-300 divide-neutral-300 bg-white dark:border-neutral-700 dark:divide-neutral-700 dark:bg-neutral-900";
  const muted = hardwood ? "text-hw-muted" : "text-neutral-600 dark:text-neutral-400";
  const action = `mt-5 min-h-12 cursor-pointer rounded-lg border px-6 py-3 text-sm font-bold focus-visible:outline-2 focus-visible:outline-offset-4 ${hardwood ? "border-hw-accent bg-hw-accent text-hw-accent-contrast focus-visible:outline-hw-accent" : "border-neutral-900 bg-neutral-900 text-white dark:border-white dark:bg-white dark:text-neutral-900 focus-visible:outline-neutral-900 dark:focus-visible:outline-white"}`;
  const scheduled = details?.gameTimeUTC ? new Date(details.gameTimeUTC) : null;
  const date = scheduled && !Number.isNaN(scheduled.getTime())
    ? new Intl.DateTimeFormat(undefined, {dateStyle: "full"}).format(scheduled)
    : details?.gameDate ? new Intl.DateTimeFormat(undefined, {dateStyle: "full"}).format(new Date(`${details.gameDate.slice(0, 10)}T12:00:00`)) : null;
  const tipoff = scheduled && !Number.isNaN(scheduled.getTime())
    ? new Intl.DateTimeFormat(undefined, {hour: "numeric", minute: "2-digit", timeZoneName: "short"}).format(scheduled)
    : "Time TBD";
  const exception = /postponed|cancelled|canceled/i.test(details?.gameStatusText ?? "");
  const title = isHidden ? "Scores hidden" : isPregame
    ? exception ? details?.gameStatusText : tipoff
    : isError ? "Game data unavailable" : isUnavailable ? "Box score unavailable" : "Loading game details";

  return (
    <section className="mx-auto my-10 w-[min(980px,calc(100%_-_32px))] text-center">
      {details && <>
        <h1 className="sr-only">{details.awayTeam.teamName} at {details.homeTeam.teamName}</h1>
        {date && <p className={`mb-5 text-sm font-semibold ${muted}`}>{date}</p>}
        <div className={`grid grid-cols-2 divide-x overflow-hidden rounded-lg border ${surface}`}>
          {[details.awayTeam, details.homeTeam].map((team) => (
            <div key={team.teamId || team.teamTricode} className="flex flex-col items-center gap-3 px-4 py-8">
              <TeamLogos teamId={team.teamId} teamName={team.teamName} tricode={team.teamTricode} size={70} />
              <h2 className="text-lg font-bold sm:text-2xl">{team.teamName || team.teamTricode}</h2>
              {isHidden && <span aria-hidden="true" className="h-12 w-20 rounded bg-current opacity-10" />}
            </div>
          ))}
        </div>
      </>}
      <div className="px-3 py-10" role={isError ? "alert" : undefined}>
        <h2 className="text-2xl font-extrabold">{title}</h2>
        <p className={`mt-3 text-sm ${muted}`}>
          {isHidden ? "Reveal scores and player stats for this game only." : isPregame
            ? exception ? "Schedule updates will appear here when available." : "Box score will be available after tip-off."
            : isError ? "Please try again to load this game." : isUnavailable ? "Box score coverage is not available for this game." : "Fetching the latest game data…"}
        </p>
        {isHidden && <button type="button" className={action} onClick={reveal}>Show scores for this game</button>}
        {isPregame && (details?.venue || details?.broadcast) && <dl className={`mt-6 grid gap-2 text-sm ${muted}`}>
          {details.venue && <div><dt className="inline font-bold">Venue: </dt><dd className="inline">{details.venue}</dd></div>}
          {details.broadcast && <div><dt className="inline font-bold">Broadcast: </dt><dd className="inline">{details.broadcast}</dd></div>}
        </dl>}
        {isError && <button type="button" className={action} onClick={retry}>Try again</button>}
        {isLoading && !isHidden && !isPregame && <p role="status" className="sr-only">Loading</p>}
      </div>
      {isHidden && <div aria-hidden="true" className="grid gap-5 text-left">
        <div className={`grid grid-cols-2 gap-4 rounded-lg border p-5 sm:grid-cols-4 ${surface}`}>
          {Array.from({length: 4}, (_, index) => <div key={index} className="h-16 rounded bg-current opacity-10" />)}
        </div>
        <div className="grid gap-5 sm:grid-cols-2">
          {[0, 1].map((team) => <div key={team} className={`grid gap-4 rounded-lg border p-5 ${surface}`}>
            {Array.from({length: 6}, (_, row) => <div key={row} className="h-4 rounded bg-current opacity-10" />)}
          </div>)}
        </div>
      </div>}
    </section>
  );
}

export default GameDetailsPanel;
