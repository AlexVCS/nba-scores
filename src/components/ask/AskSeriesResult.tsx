import TeamLogos from "@/components/TeamLogos";
import type {AskPlayoffSeriesResult} from "@/services/ask/types";
import AskGameCard from "./AskGameCard";
import {playoffYear, roundLabel} from "./askFormat";
import {askCap, askCard} from "./askStyles";

interface AskSeriesResultProps {
  result: AskPlayoffSeriesResult;
}

function AskSeriesResult({result}: AskSeriesResultProps) {
  const games = result.games.value;

  return (
    <div className="grid gap-3">
      <div className={askCard}>
        <div className="border-b border-hw-line px-3.5 pt-3.5 pb-3">
          <div className={askCap}>{roundLabel(result.round, result.conference)} · {playoffYear(result.season)}</div>
          <div className="mt-2 text-[17px] leading-tight font-extrabold">{result.summary.value}</div>
        </div>
        <ul>
          {result.teams.map((row, index) => {
            const team = row.team.value;
            const seed = row.seed.value;
            const won = row.won_series.value;
            return (
              <li key={index} className="flex items-center gap-3 border-t border-hw-line px-3.5 py-3.5 first:border-t-0">
                <span className="grid h-10 w-12 place-items-center">
                  <TeamLogos teamName={team.name} teamId={team.team_id} tricode={team.tricode} size={40} />
                </span>
                <span className={`flex-1 text-sm font-extrabold ${won === false ? "text-hw-muted" : ""}`}>
                  {team.name}
                  {seed != null && <span className="ml-2 text-[10px] font-bold text-hw-muted">Seed {seed}</span>}
                  {won === true && <span className="sr-only"> (won the series)</span>}
                </span>
                <span className="text-xl font-extrabold tabular-nums">{row.wins.value}</span>
              </li>
            );
          })}
          <li className="flex items-center border-t border-hw-line bg-hw-surface-muted px-3.5 py-3.5">
            <span className={`${askCap} flex-1`}>Games played</span>
            <span className="text-base font-extrabold tabular-nums">{result.games_played.value}</span>
          </li>
        </ul>
      </div>
      {games.length > 0 && (
        <ul className="grid grid-cols-2 gap-3 max-[700px]:grid-cols-1" aria-label="Series games">
          {games.map((item, index) => (
            <li key={item.game.gameId}>
              <AskGameCard game={item.game} showScores date={item.date} index={index} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default AskSeriesResult;
