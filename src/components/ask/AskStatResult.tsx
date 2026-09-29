import type {AskBoxscoreStatResult, AskStatValue, Guarded} from "@/services/ask/types";
import AskHiddenValue from "./AskHiddenValue";
import AskRevealButton from "./AskRevealButton";
import {STAT_LABELS, formatAskDate, roundLabel} from "./askFormat";
import {RESULT_GROUP, SCORE_GROUP, guarded} from "./askSpoilers";
import {askCap, askCard, askTricode, type AskRevealControls} from "./askStyles";

interface AskStatResultProps {
  result: AskBoxscoreStatResult;
  controls: AskRevealControls;
}

function statText(value: AskStatValue): string {
  if (value.made !== null && value.attempted !== null) return `${value.made}-${value.attempted}`;
  return value.display;
}

function StatValues({values, revealed, hero}: {values: Guarded<AskStatValue>[]; revealed: boolean; hero: boolean}) {
  return (
    <dl className={hero && values.length === 1 ? "" : "grid grid-cols-[repeat(auto-fill,minmax(96px,1fr))] gap-3"}>
      {values.map(entry => {
        const shown = guarded(entry, revealed);
        return (
          <div key={entry.value.stat} className="flex flex-col-reverse">
            <dt className={hero && values.length === 1 ? "text-[17px] font-bold text-hw-muted" : `${askCap} mt-1`}>{STAT_LABELS[entry.value.stat]}</dt>
            <dd className={hero && values.length === 1 ? "text-[56px] leading-[.9] font-extrabold tracking-[-.02em] tabular-nums" : "text-xl font-extrabold tabular-nums"}>
              {shown ? statText(shown) : <AskHiddenValue width={hero && values.length === 1 ? 64 : 30} />}
            </dd>
          </div>
        );
      })}
    </dl>
  );
}

function AskStatResult({result, controls}: AskStatResultProps) {
  const revealed = controls.isRevealed(RESULT_GROUP);
  const scoreRevealed = controls.isRevealed(SCORE_GROUP);
  const {game} = result;
  const score = guarded(game.final_score, scoreRevealed);
  const matchup = `${game.away.tricode} @ ${game.home.tricode}`;
  const context = [matchup, formatAskDate(game.date), game.round ? roundLabel(game.round) : null, game.game_number ? `Game ${game.game_number}` : null]
    .filter(Boolean)
    .join(" · ");
  const statName = result.stat === "stat_line" ? "stat line" : STAT_LABELS[result.stat].toLowerCase();

  return (
    <div className={askCard}>
      <div className="flex flex-wrap items-end justify-between gap-4 px-[18px] pt-[18px] pb-4">
        <div className="min-w-0">
          {result.scope === "player" && result.player_line && (
            <>
              <div className={`${askCap} mb-2.5`}>{result.player_line.player.name} · {context}</div>
              {result.player_line.status === "played"
                ? <StatValues values={result.player_line.values} revealed={revealed} hero />
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
                    <StatValues values={line.values} revealed={revealed} hero={result.team_lines.length === 1} />
                  </div>
                ))}
              </div>
            </>
          )}
          {result.scope === "leaders" && (
            <>
              <div className={`${askCap} mb-2.5`}>{STAT_LABELS[result.stat]} leaders · {context}</div>
              <ol className="grid gap-2">
                {result.leaders.map(row => {
                  const player = guarded(row.player, revealed);
                  const team = guarded(row.team, revealed);
                  const value = guarded(row.value, revealed);
                  return (
                    <li key={row.rank} className="flex items-center gap-3 text-sm font-bold">
                      <span className="w-5 text-hw-muted tabular-nums">{row.rank}</span>
                      <span className="min-w-0 flex-1">{player ? player.name : <AskHiddenValue width={120} />}</span>
                      <span className={askTricode}>{team ? team.tricode : <AskHiddenValue width={24} />}</span>
                      <span className="w-12 text-right text-lg font-extrabold tabular-nums">{value ? statText(value) : <AskHiddenValue width={24} />}</span>
                    </li>
                  );
                })}
              </ol>
            </>
          )}
        </div>
        <AskRevealButton group={RESULT_GROUP} controls={controls} label={statName} />
      </div>
      <div className="flex flex-wrap items-center gap-3 border-t border-hw-line bg-hw-surface-muted px-3.5 py-3">
        <span className={`${askCap} w-[92px]`}>Final score</span>
        {game.final_score.value === null && !game.final_score.spoiler ? (
          <span className="text-sm font-bold text-hw-muted">Not final yet</span>
        ) : (
        <span className="flex items-center gap-2 text-lg font-extrabold tabular-nums">
          <span className={askTricode}>{game.away.tricode}</span>
          {score ? score.away : <AskHiddenValue />}
          <span className="font-medium text-hw-muted" aria-hidden="true">–</span>
          {score ? score.home : <AskHiddenValue />}
          <span className={askTricode}>{game.home.tricode}</span>
          {score && score.periods > 4 && (
            <span className="text-[11px] font-extrabold text-hw-muted">{score.periods === 5 ? "OT" : `${score.periods - 4}OT`}</span>
          )}
        </span>
        )}
        <span className="flex-1" />
        {game.final_score.spoiler && game.final_score.value !== null && (
          <AskRevealButton group={SCORE_GROUP} controls={controls} label="score" />
        )}
      </div>
    </div>
  );
}

export default AskStatResult;
