import {useState} from "react";
import {Link, useLocation} from "react-router";
import TeamLogos from "@/components/TeamLogos";
import type {LastMatchup, MatchupTeam} from "@/services/nbaService";
import {designPath} from "../../designRoutes";
import HardwoodWinnerArrow from "./HardwoodWinnerArrow";
import {hwNarrowContainer} from "./hardwoodStyles";

interface HardwoodLastMatchupsProps {
  games: LastMatchup[];
  isLoading: boolean;
  showScores: boolean;
}

const formatDate = (value: string) =>
  new Intl.DateTimeFormat(undefined, {month: "short", day: "numeric", year: "numeric"}).format(new Date(`${value}T12:00:00`));

function MatchupSide({team, won, showScore, align}: {team: MatchupTeam; won: boolean; showScore: boolean; align: "start" | "end"}) {
  return (
    <div className={`flex items-center gap-3 ${align === "end" ? "flex-row-reverse" : ""}`}>
      <div className="flex w-12 flex-col items-center gap-1">
        <TeamLogos teamId={team.teamId} tricode={team.teamTricode} size={36} />
        <span className="text-[11px] font-extrabold tracking-[.08em]">{team.teamTricode}</span>
      </div>
      {showScore
        ? <strong className={`text-[32px] leading-none font-extrabold tabular-nums ${won ? "text-hw-ink dark:text-hw-accent" : "text-hw-muted"}`}>{team.score}</strong>
        : <span aria-hidden="true" className="h-7 w-12 rounded bg-current opacity-10" />}
    </div>
  );
}

// Revealing past meetings is local to this section: it must never reveal the
// upcoming game itself, which would leak live scores once it tips off.
function HardwoodLastMatchups({games, isLoading, showScores: showAllScores}: HardwoodLastMatchupsProps) {
  const location = useLocation();
  const [revealed, setRevealed] = useState(false);
  const showScores = showAllScores || revealed;
  if (!isLoading && games.length === 0) return null;

  return (
    <section className={`${hwNarrowContainer} mb-20`} aria-labelledby="hardwood-last-matchups-heading">
      <div className="mb-3 flex items-center justify-between gap-4 border-b border-hw-line pb-2">
        <h2 id="hardwood-last-matchups-heading" className="text-[13px] font-extrabold tracking-[.22em] uppercase">Last matchups</h2>
        {!showScores && games.length > 0 && (
          <button type="button" className="cursor-pointer rounded-hw border border-hw-line bg-hw-surface px-3 py-1.5 text-[10px] font-extrabold tracking-[.12em] uppercase hover:bg-hw-surface-muted focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-hw-accent" onClick={() => setRevealed(true)}>
            Show results
          </button>
        )}
      </div>
      {isLoading ? (
        <div aria-hidden="true" className="grid gap-3 sm:grid-cols-2">
          {[0, 1].map((key) => <div key={key} className="h-[132px] rounded-hw border border-hw-line bg-hw-surface opacity-60" />)}
        </div>
      ) : (
        <ul className="grid gap-3 sm:grid-cols-2">
          {games.map((game) => {
            const awayWon = game.awayTeam.score > game.homeTeam.score;
            return (
              <li key={game.gameId} className="relative rounded-hw border border-hw-line bg-hw-surface shadow-hw-card">
                <p className="border-b border-hw-line px-4 py-2 text-center text-[10px] font-extrabold tracking-[.14em] text-hw-muted uppercase">{formatDate(game.gameDate)}</p>
                <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-3 px-4 py-4">
                  <MatchupSide team={game.awayTeam} won={awayWon} showScore={showScores} align="start" />
                  <span className="flex items-center gap-1 text-[10px] font-extrabold tracking-[.14em] text-hw-muted uppercase">
                    {showScores && awayWon && <span className="inline-block rotate-180 text-hw-winner-arrow"><HardwoodWinnerArrow className="text-[32px]" /></span>}
                    Final
                    {showScores && !awayWon && <span className="text-hw-winner-arrow"><HardwoodWinnerArrow className="text-[32px]" /></span>}
                  </span>
                  <MatchupSide team={game.homeTeam} won={!awayWon} showScore={showScores} align="end" />
                </div>
                <Link
                  className="block border-t border-hw-line px-4 py-2 text-center text-[10px] font-extrabold tracking-[.12em] uppercase no-underline hover:text-hw-accent-ink focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-hw-accent"
                  to={designPath("design-1", `/games/${game.gameId}/boxscore?date=${game.gameDate}`)}
                  state={{from: location.pathname + location.search}}
                  aria-label={`${game.awayTeam.teamTricode} at ${game.homeTeam.teamTricode}, ${formatDate(game.gameDate)} box score`}
                >
                  Box score
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

export default HardwoodLastMatchups;
