import type {AskPlayoffSeriesResult} from "@/services/ask/types";
import AskGameCard from "./AskGameCard";
import AskHiddenValue from "./AskHiddenValue";
import AskRevealButton from "./AskRevealButton";
import {playoffYear, roundLabel} from "./askFormat";
import {RESULT_GROUP, guarded, safeGame} from "./askSpoilers";
import {askCap, askCard, askTricode, type AskRevealControls} from "./askStyles";

interface AskSeriesResultProps {
  result: AskPlayoffSeriesResult;
  controls: AskRevealControls;
}

function AskSeriesResult({result, controls}: AskSeriesResultProps) {
  const revealed = controls.isRevealed(RESULT_GROUP);
  const summary = guarded(result.summary, revealed);
  const gamesPlayed = guarded(result.games_played, revealed);
  // The game list is guarded as a whole: its length reveals the series length.
  const games = guarded(result.games, revealed) ?? [];

  return (
    <div className="grid gap-3">
      <div className={askCard}>
        <div className="border-b border-hw-line px-3.5 pt-3.5 pb-3">
          <div className={askCap}>{roundLabel(result.round, result.conference)} · {playoffYear(result.season)}</div>
          {summary
            ? <div className="mt-2 text-[17px] leading-tight font-extrabold">{summary}</div>
            : (
              <>
                <div className="mt-2 text-[17px] leading-tight font-extrabold">This answer is a result</div>
                <p className="mt-1 text-xs leading-normal text-hw-muted">The winner, the series score, and how many games it went are hidden.</p>
              </>
            )}
        </div>
        <ul>
          {result.teams.map((row, index) => {
            const team = guarded(row.team, revealed);
            const wins = guarded(row.wins, revealed);
            const seed = guarded(row.seed, revealed);
            const won = guarded(row.won_series, revealed);
            return (
              <li key={index} className="flex items-center gap-3 border-t border-hw-line px-3.5 py-3.5 first:border-t-0">
                <span className={`${askTricode} h-[34px] min-w-12`}>{team ? team.tricode : <AskHiddenValue width={24} />}</span>
                <span className={`flex-1 text-sm font-extrabold ${won === false ? "text-hw-muted" : ""}`}>
                  {team ? team.name : <AskHiddenValue width={120} />}
                  {seed != null && <span className="ml-2 text-[10px] font-bold text-hw-muted">Seed {seed}</span>}
                  {won === true && <span className="sr-only"> (won the series)</span>}
                </span>
                <span className="text-xl font-extrabold tabular-nums">{wins ?? <AskHiddenValue width={22} />}</span>
              </li>
            );
          })}
          <li className="flex items-center border-t border-hw-line bg-hw-surface-muted px-3.5 py-3.5">
            <span className={`${askCap} flex-1`}>Games played</span>
            <span className="text-base font-extrabold tabular-nums">{gamesPlayed ?? <AskHiddenValue width={22} />}</span>
          </li>
        </ul>
      </div>
      <AskRevealButton group={RESULT_GROUP} controls={controls} label="answer" className="min-h-[46px] w-full" />
      {games.length > 0 && (
        <ul className="grid grid-cols-2 gap-3 max-[700px]:grid-cols-1" aria-label="Series games">
          {games.map((item, index) => (
            <li key={item.game.gameId}>
              <AskGameCard game={safeGame(item.game, item.spoilers, revealed)} showScores={revealed} date={item.date} index={index} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default AskSeriesResult;
