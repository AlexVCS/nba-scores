import type {AskBoxscoreStatResult, AskStatValue} from "@/services/ask/types";
import {STAT_LABELS, formatAskDate, roundLabel} from "./askFormat";
import {askCap, askCard, askTricode} from "./askStyles";

interface AskStatResultProps {
  result: AskBoxscoreStatResult;
}

function StatValues({values, hero}: {values: AskStatValue[]; hero: boolean}) {
  return (
    <dl className={hero && values.length === 1 ? "" : "grid grid-cols-[repeat(auto-fill,minmax(96px,1fr))] gap-3"}>
      {values.map(value => (
        <div key={value.stat} className="flex flex-col-reverse">
          <dt className={hero && values.length === 1 ? "text-[17px] font-bold text-hw-muted" : `${askCap} mt-1`}>{STAT_LABELS[value.stat]}</dt>
          <dd className={hero && values.length === 1 ? "text-[56px] leading-[.9] font-extrabold tracking-[-.02em] tabular-nums" : "text-xl font-extrabold tabular-nums"}>
            {value.display}
          </dd>
        </div>
      ))}
    </dl>
  );
}

function AskStatResult({result}: AskStatResultProps) {
  const {game} = result;
  const {final_score: score, away, home} = game;
  const context = [
    `${away.tricode} @ ${home.tricode}`,
    formatAskDate(game.date),
    game.round ? roundLabel(game.round) : null,
    game.game_number ? `Game ${game.game_number}` : null,
  ].filter(Boolean).join(" · ");

  return (
    <div className={askCard}>
      <div className="px-[18px] pt-[18px] pb-4">
        {result.scope === "player" && result.player_line && (
          <>
            <div className={`${askCap} mb-2.5`}>{result.player_line.player.name} · {context}</div>
            {result.player_line.status === "played"
              ? <StatValues values={result.player_line.values} hero />
              : <p className="text-lg font-extrabold">{result.player_line.status === "inactive" ? "Inactive" : "Did not play"}</p>}
          </>
        )}
        {result.scope === "team" && (
          <>
            <div className={`${askCap} mb-2.5`}>{context}</div>
            <div className="grid gap-3">
              {result.team_lines.map(line => (
                <div key={line.team.team_id} className="flex items-center gap-3">
                  <span className={askTricode}>{line.team.tricode}</span>
                  <StatValues values={line.values} hero={result.team_lines.length === 1} />
                </div>
              ))}
            </div>
          </>
        )}
        {result.scope === "leaders" && result.leaders && (
          <>
            <div className={`${askCap} mb-2.5`}>{STAT_LABELS[result.stat]} leaders · {context}</div>
            <ol className="grid gap-2">
              {result.leaders.map((row, index) => (
                <li key={`${row.rank}-${row.player.player_id}-${index}`} className="flex items-center gap-3 text-sm font-bold">
                  <span className="w-5 text-hw-muted tabular-nums">{row.rank}</span>
                  <span className="min-w-0 flex-1">{row.player.name}</span>
                  <span className={askTricode}>{row.team.tricode}</span>
                  <span className="w-12 text-right text-lg font-extrabold tabular-nums">{row.value.display}</span>
                </li>
              ))}
            </ol>
          </>
        )}
      </div>
      <div className="flex flex-wrap items-center gap-3 border-t border-hw-line bg-hw-surface-muted px-3.5 py-3">
        <span className={`${askCap} w-[92px]`}>Final score</span>
        {score === null ? (
          <span className="text-sm font-bold text-hw-muted">Not final yet</span>
        ) : (
          <span className="flex items-center gap-2 text-lg font-extrabold tabular-nums">
            <span className={askTricode}>{away.tricode}</span>
            {score.away}
            <span className="font-medium text-hw-muted" aria-hidden="true">–</span>
            {score.home}
            <span className={askTricode}>{home.tricode}</span>
            {score.periods > 4 && (
              <span className="text-[11px] font-extrabold text-hw-muted">{score.periods === 5 ? "OT" : `${score.periods - 4}OT`}</span>
            )}
          </span>
        )}
      </div>
    </div>
  );
}

export default AskStatResult;
