import {Link, useLocation} from "react-router";
import type {AskPostseasonSummaryResult} from "@/services/ask/types";
import AskHiddenValue from "./AskHiddenValue";
import AskRevealButton from "./AskRevealButton";
import {FINISH_LABELS, playoffYear, roundLabel} from "./askFormat";
import {withDesignPrefix} from "./askRouting";
import {RESULT_GROUP, guarded} from "./askSpoilers";
import {askCap, askCard, type AskRevealControls} from "./askStyles";

interface AskPostseasonResultProps {
  result: AskPostseasonSummaryResult;
  controls: AskRevealControls;
}

const statValue = "text-[22px] font-extrabold tabular-nums";

function AskPostseasonResult({result, controls}: AskPostseasonResultProps) {
  const {pathname} = useLocation();
  const revealed = controls.isRevealed(RESULT_GROUP);
  const year = playoffYear(result.season);

  if (result.team) {
    const finish = guarded(result.finish, revealed);
    const record = guarded(result.record, revealed);
    const seriesWon = guarded(result.series_won, revealed);
    // Guarded as a whole: the number of rounds reveals how far the team went.
    const rounds = guarded(result.rounds, revealed);
    return (
      <div className="grid gap-3">
        <div className={askCard}>
          <div className="border-b-4 border-hw-accent px-3.5 py-4">
            <div className={askCap}>{result.team.name} · {year} Postseason</div>
            <div className="mt-2.5 text-2xl leading-tight font-extrabold uppercase">
              {finish ? FINISH_LABELS[finish] : finish === null ? "No result yet" : <AskHiddenValue width={180} />}
            </div>
            <dl className="mt-3 flex gap-[22px]">
              <div className="flex flex-col-reverse">
                <dt className={`${askCap} mt-1`}>Record</dt>
                <dd className={statValue}>{record ? `${record.wins}-${record.losses}` : <AskHiddenValue width={44} />}</dd>
              </div>
              <div className="flex flex-col-reverse">
                <dt className={`${askCap} mt-1`}>Series won</dt>
                <dd className={statValue}>{seriesWon ?? <AskHiddenValue width={30} />}</dd>
              </div>
            </dl>
          </div>
          {rounds ? (
            <ul aria-label="Rounds">
              {rounds.map(round => (
                <li key={round.round} className="flex items-center gap-2 border-t border-hw-line px-3.5 py-3 first:border-t-0">
                  <span className={`${askCap} w-[120px] text-hw-ink!`}>{roundLabel(round.round, round.conference)}</span>
                  <span className="flex-1" />
                  <span className="flex items-center gap-2 text-[17px] font-extrabold tabular-nums">
                    <span className="text-xs">{result.team?.tricode}</span>
                    <span className={round.won === false ? "text-hw-muted" : ""}>{round.team_wins}</span>
                    <span className="font-medium text-hw-muted" aria-hidden="true">–</span>
                    <span className={round.won === true ? "text-hw-muted" : ""}>{round.opponent_wins}</span>
                    <span className="text-xs text-hw-muted">{round.opponent.tricode}</span>
                  </span>
                  {round.series_href && (
                    <Link className="ml-2 text-[10px] font-extrabold tracking-[.1em] uppercase underline underline-offset-3" to={withDesignPrefix(round.series_href, pathname)}>
                      Series
                    </Link>
                  )}
                </li>
              ))}
            </ul>
          ) : (
            <div className="flex items-center px-3.5 py-3">
              <span className={`${askCap} flex-1`}>Series by round</span>
              <AskHiddenValue width={60} />
            </div>
          )}
        </div>
        <AskRevealButton group={RESULT_GROUP} controls={controls} label="answer" className="min-h-[46px] w-full" />
      </div>
    );
  }

  const champion = guarded(result.champion, revealed);
  const runnerUp = guarded(result.runner_up, revealed);
  const series = guarded(result.series, revealed);
  return (
    <div className="grid gap-3">
      <div className={askCard}>
        <div className="border-b-4 border-hw-accent px-3.5 py-4">
          <div className={askCap}>{year} Postseason</div>
          <dl className="mt-3 grid grid-cols-2 gap-4">
            <div className="flex flex-col-reverse">
              <dt className={`${askCap} mt-1`}>Champion</dt>
              <dd className="text-lg font-extrabold">{champion ? champion.name : champion === null ? "Not decided" : <AskHiddenValue width={120} />}</dd>
            </div>
            <div className="flex flex-col-reverse">
              <dt className={`${askCap} mt-1`}>Runner-up</dt>
              <dd className="text-lg font-extrabold">{runnerUp ? runnerUp.name : runnerUp === null ? "Not decided" : <AskHiddenValue width={120} />}</dd>
            </div>
          </dl>
        </div>
        {series ? (
          <ul aria-label="Series">
            {series.map((row, index) => (
              <li key={index} className="flex items-center gap-2 border-t border-hw-line px-3.5 py-2.5 text-sm first:border-t-0">
                <span className={`${askCap} w-[132px]`}>{roundLabel(row.round, row.conference)}</span>
                <span className="flex-1 font-extrabold">{row.winner?.tricode ?? "TBD"}</span>
                <span className="font-extrabold tabular-nums">{row.winner_wins}–{row.loser_wins}</span>
                <span className="w-10 text-right text-hw-muted">{row.loser?.tricode ?? "TBD"}</span>
              </li>
            ))}
          </ul>
        ) : (
          <div className="flex items-center px-3.5 py-3">
            <span className={`${askCap} flex-1`}>Every series</span>
            <AskHiddenValue width={60} />
          </div>
        )}
      </div>
      <AskRevealButton group={RESULT_GROUP} controls={controls} label="answer" className="min-h-[46px] w-full" />
    </div>
  );
}

export default AskPostseasonResult;
