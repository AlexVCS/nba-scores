import type {AskPostseasonSummaryResult} from "@/services/ask/types";
import AskLinks from "./AskLinks";
import {FINISH_LABELS, playoffYear, roundLabel} from "./askFormat";
import {askCap, askCard} from "./askStyles";

interface AskPostseasonResultProps {
  result: AskPostseasonSummaryResult;
  resultsHidden: boolean;
}

const statValue = "text-[22px] font-extrabold tabular-nums";

function AskPostseasonResult({result, resultsHidden}: AskPostseasonResultProps) {
  const year = playoffYear(result.season);

  if (result.team) {
    const finish = result.finish.value;
    const record = result.record.value;
    const seriesWon = result.series_won.value;
    const rounds = result.rounds.value;
    return (
      <div className="grid gap-3">
        <div className={askCard}>
          <div className="border-b-4 border-hw-accent px-3.5 py-4">
            <div className={askCap}>{result.team.name} · {year} Postseason</div>
            <div className="mt-2.5 text-2xl leading-tight font-extrabold uppercase">
              {finish ? FINISH_LABELS[finish] : "No result yet"}
            </div>
            <dl className="mt-3 flex gap-[22px]">
              <div className="flex flex-col-reverse">
                <dt className={`${askCap} mt-1`}>Record</dt>
                <dd className={statValue}>{record ? `${record.wins}-${record.losses}` : "–"}</dd>
              </div>
              <div className="flex flex-col-reverse">
                <dt className={`${askCap} mt-1`}>Series won</dt>
                <dd className={statValue}>{seriesWon ?? "–"}</dd>
              </div>
            </dl>
          </div>
          {rounds.length > 0 && (
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
                  {round.series_link && <AskLinks links={[round.series_link]} resultsHidden={resultsHidden} compact />}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    );
  }

  const champion = result.champion.value;
  const runnerUp = result.runner_up.value;
  const series = result.series.value;
  return (
    <div className="grid gap-3">
      <div className={askCard}>
        <div className="border-b-4 border-hw-accent px-3.5 py-4">
          <div className={askCap}>{year} Postseason</div>
          <dl className="mt-3 grid grid-cols-2 gap-4">
            <div className="flex flex-col-reverse">
              <dt className={`${askCap} mt-1`}>Champion</dt>
              <dd className="text-lg font-extrabold">{champion ? champion.name : "Not decided"}</dd>
            </div>
            <div className="flex flex-col-reverse">
              <dt className={`${askCap} mt-1`}>Runner-up</dt>
              <dd className="text-lg font-extrabold">{runnerUp ? runnerUp.name : "Not decided"}</dd>
            </div>
          </dl>
        </div>
        {series.length > 0 && (
          <ul aria-label="Series">
            {series.map((row, index) => (
              <li key={`${row.round}-${row.conference}-${index}`} className="flex flex-wrap items-center gap-2 border-t border-hw-line px-3.5 py-2.5 text-sm first:border-t-0">
                <span className={`${askCap} w-[132px]`}>{roundLabel(row.round, row.conference)}</span>
                <span className="flex-1 font-extrabold">{row.teams[0].team.tricode} <span className="tabular-nums">{row.teams[0].wins}–{row.teams[1].wins}</span> {row.teams[1].team.tricode}</span>
                <span className="text-xs text-hw-muted">{row.status === "complete" ? "Final" : row.status === "in_progress" ? "In progress" : "Not started"}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

export default AskPostseasonResult;
