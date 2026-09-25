import TeamLogos from "@/components/TeamLogos";
import type {GameDetails} from "@/services/nbaService";
import {hwNarrowContainer} from "./hardwoodStyles";

interface HardwoodPregameSummaryProps {
  details: GameDetails;
}

// NBA schedules are published in Eastern time; show tip-off the nba.com way ("8:00 PM ET").
const NBA_TIME_ZONE = "America/New_York";
const DATE_FORMAT: Intl.DateTimeFormatOptions = {weekday: "short", month: "short", day: "numeric", year: "numeric"};
const LABEL_CLASS = "text-[10px] font-extrabold tracking-[.18em] whitespace-nowrap text-hw-muted uppercase";

const formatDate = (details: GameDetails, scheduled: Date | null) => {
  if (scheduled) return new Intl.DateTimeFormat("en-US", {...DATE_FORMAT, timeZone: NBA_TIME_ZONE}).format(scheduled);
  if (!details.gameDate) return null;
  return new Intl.DateTimeFormat("en-US", DATE_FORMAT).format(new Date(`${details.gameDate.slice(0, 10)}T12:00:00`));
};

const formatTipoff = (scheduled: Date) =>
  `${new Intl.DateTimeFormat("en-US", {hour: "numeric", minute: "2-digit", timeZone: NBA_TIME_ZONE}).format(scheduled)} ET`;

function HardwoodPregameSummary({details}: HardwoodPregameSummaryProps) {
  const parsed = details.gameTimeUTC ? new Date(details.gameTimeUTC) : null;
  const scheduled = parsed && !Number.isNaN(parsed.getTime()) ? parsed : null;
  const date = formatDate(details, scheduled);
  const exception = /postponed|cancelled|canceled/i.test(details.gameStatusText);
  const status = exception ? details.gameStatusText : date;
  const venue = [details.venue, details.venueCity, details.venueState].filter(Boolean).join(", ");
  const teams = [
    {side: "Away", team: details.awayTeam, className: "col-start-1"},
    {side: "Home", team: details.homeTeam, className: "col-start-3 max-[700px]:col-start-2"},
  ];

  return (
    <section className={`${hwNarrowContainer} mt-[46px] mb-8 overflow-hidden rounded-hw bg-hw-surface shadow-hw-card`}>
      <h1 className="sr-only">{details.awayTeam.teamName} at {details.homeTeam.teamName}</h1>
      {status && (
        <div className="border-b border-hw-line p-3.5 text-center">
          <span className={LABEL_CLASS}>{status}</span>
        </div>
      )}
      <div className="grid grid-cols-[1fr_auto_1fr] items-center px-12 py-[34px] max-[700px]:grid-cols-2 max-[700px]:gap-y-[22px] max-[700px]:px-4 max-[700px]:py-6">
        {teams.map(({side, team, className}) => (
          <div key={side} className={`row-start-1 flex min-w-0 flex-col items-center gap-2.5 text-center max-[700px]:[&_figure]:size-14! ${className}`}>
            <TeamLogos teamName={team.teamName} teamId={team.teamId} size={84} tricode={team.teamTricode} />
            <div className="mt-1 text-[44px] leading-[.9] font-extrabold tracking-[-.02em] max-[700px]:mt-0 max-[700px]:text-[32px]">{team.teamTricode}</div>
            <span className="mt-1.5 text-[11px] font-extrabold tracking-[.24em] whitespace-nowrap text-hw-muted uppercase max-[700px]:-mt-0.5 max-[700px]:text-[10px] max-[700px]:tracking-[.18em]">
              {side}
            </span>
          </div>
        ))}
        {!exception && (
          <div className="col-start-2 row-start-1 min-w-[220px] px-6 text-center max-[700px]:col-span-full max-[700px]:col-start-1 max-[700px]:row-start-2 max-[700px]:min-w-0 max-[700px]:border-t max-[700px]:border-hw-line max-[700px]:px-0 max-[700px]:pt-5">
            {scheduled ? (
              <time dateTime={scheduled.toISOString()} className="text-[40px] leading-none font-extrabold tracking-[-.02em] whitespace-nowrap max-[700px]:text-[34px]">
                {formatTipoff(scheduled)}
              </time>
            ) : (
              <span className="text-[40px] leading-none font-extrabold tracking-[-.02em] max-[700px]:text-[34px]">TBD</span>
            )}
          </div>
        )}
      </div>
      {(venue || details.broadcast) && (
        <p className="border-t border-hw-line bg-hw-surface-muted p-3.5 text-center text-[13px] font-bold">
          {venue}
          {details.broadcast && (
            <span className="font-semibold text-hw-muted">{venue && " · "}{details.broadcast}</span>
          )}
        </p>
      )}
    </section>
  );
}

export default HardwoodPregameSummary;
