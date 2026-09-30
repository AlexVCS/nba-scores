import type {AskPlayerSeasonStatsResult} from "@/services/ask/types";
import {STAT_LABELS, formatAskTimestamp} from "./askFormat";
import {askCap, askCard} from "./askStyles";

interface AskSeasonStatsResultProps {
  result: AskPlayerSeasonStatsResult;
}

function AskSeasonStatsResult({result}: AskSeasonStatsResultProps) {
  const single = result.values.length === 1;
  return (
    <section className={askCard} aria-label={`${result.player.name} season statistics`}>
      <div className="p-[18px]">
        <h3 className="text-xl font-extrabold">{result.player.name}</h3>
        <p className={`${askCap} mt-1 mb-4`}>
          {result.season} · {result.season_type === "playoffs" ? "Playoffs" : "Regular season"}
          {result.team ? ` · ${result.team.name}` : " · All teams"}
        </p>
        <dl className={single ? "" : "grid grid-cols-[repeat(auto-fill,minmax(112px,1fr))] gap-4"}>
          {result.values.map(value => (
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
        {result.values.every(value => value.stat.endsWith("percentage")) ? "Season shooting percentage" : result.aggregation === "per_game" ? "Per game" : "Season totals"} · {result.games_played} games played
        <span className="mt-1 block">Data as of {formatAskTimestamp(result.as_of)}</span>
      </div>
    </section>
  );
}

export default AskSeasonStatsResult;
