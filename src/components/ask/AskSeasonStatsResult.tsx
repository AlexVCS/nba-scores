import type {AskPlayerSeasonStatsResult} from "@/services/ask/types";
import {STAT_LABELS, formatAskTimestamp} from "./askFormat";
import {useAskMeasure} from "./askMeasure";
import AskMeasureToggle from "./AskMeasureToggle";
import {askCap, askCard} from "./askStyles";

interface AskSeasonStatsResultProps {
  result: AskPlayerSeasonStatsResult;
}

function AskSeasonStatsResult({result}: AskSeasonStatsResultProps) {
  const {measure, values, toggle, setMeasure} = useAskMeasure(result);
  const single = values.length === 1;
  return (
    <section className={askCard} aria-label={`${result.player.name} season statistics`}>
      <div className="p-[18px]">
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            <h3 className="text-xl font-extrabold">{result.player.name}</h3>
            <p className={`${askCap} mt-1`}>
              {result.season} · {result.season_type === "playoffs" ? "Playoffs" : "Regular season"}
              {result.team ? ` · ${result.team.name}` : " · All teams"}
            </p>
          </div>
          {toggle && <AskMeasureToggle measure={measure} onChange={setMeasure} subject={`${result.player.name} ${result.season} statistics`} />}
        </div>
        <dl className={single ? "" : "grid grid-cols-[repeat(auto-fill,minmax(112px,1fr))] gap-4"}>
          {values.map(value => (
            <div key={value.stat} className="flex flex-col-reverse">
              <dt className={`${askCap} mt-1`}>{STAT_LABELS[value.stat]}</dt>
              <dd className={single ? "text-[56px] leading-tight font-extrabold tabular-nums" : "text-xl font-extrabold tabular-nums"}>
                {value.display}
              </dd>
            </div>
          ))}
        </dl>
        {result.coverage_note && <p className="mt-4 text-sm text-hw-muted">{result.coverage_note}</p>}
      </div>
      <div className="border-t border-hw-line bg-hw-surface-muted px-[18px] py-3 text-xs font-bold text-hw-muted">
        {values.every(value => value.stat.endsWith("percentage")) ? "Season shooting percentage" : measure === "per_game" ? "Per game" : "Season totals"} · {result.games_played} games played
        <span className="mt-1 block">Data as of {formatAskTimestamp(result.as_of)}</span>
      </div>
    </section>
  );
}

export default AskSeasonStatsResult;
