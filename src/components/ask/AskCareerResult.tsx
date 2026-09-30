import type {AskCareerStatsResult} from "@/services/ask/types";
import {STAT_LABELS, formatAskTimestamp} from "./askFormat";
import {useAskMeasure} from "./askMeasure";
import AskMeasureToggle from "./AskMeasureToggle";
import {askCap, askCard} from "./askStyles";

interface AskCareerResultProps {
  result: AskCareerStatsResult;
}

function ordinal(n: number): string {
  const tens = n % 100;
  const suffix = tens >= 11 && tens <= 13 ? "th" : ({1: "st", 2: "nd", 3: "rd"} as Record<number, string>)[n % 10] ?? "th";
  return `${n}${suffix}`;
}

function AskCareerResult({result}: AskCareerResultProps) {
  const phase = result.season_type === "playoffs" ? "Playoffs" : "Regular season";
  const statLabel = STAT_LABELS[result.stat];
  const tiedRanks = new Set(result.rows.filter((row, i) => result.rows.findIndex(other => other.rank === row.rank) !== i).map(row => row.rank));
  const title = result.view === "leaders" ? `All-time ${statLabel.toLowerCase()} leaders`
    : result.view === "player_rank" ? `${result.player?.name} · all-time ${statLabel.toLowerCase()}`
      : `${result.player?.name} career statistics`;
  const {measure, values, toggle, setMeasure} = useAskMeasure(result);
  const single = values.length === 1;

  return (
    <section className={askCard} aria-label={title}>
      <div className="p-[18px]">
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            <h3 className="text-xl font-extrabold">{result.view === "leaders" ? title : result.player?.name}</h3>
            <p className={`${askCap} mt-1`}>
              Career · {phase}{result.view === "leaders" ? ` · Top ${result.limit}` : ""}
            </p>
          </div>
          {result.view === "player_totals" && toggle && (
            <AskMeasureToggle measure={measure} onChange={setMeasure} subject={`${result.player?.name} career statistics`} />
          )}
        </div>
        {result.limit_note && <p className="-mt-2 mb-3 text-sm font-bold text-hw-muted">{result.limit_note}</p>}

        {result.view === "player_totals" && (
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
        )}

        {result.view === "player_rank" && (result.rank === null ? (
          <p className="text-lg font-extrabold">Not in NBA.com's top {result.list_size} for career {statLabel.toLowerCase()}.</p>
        ) : (
          <dl className="grid grid-cols-2 gap-4">
            <div className="flex flex-col-reverse">
              <dt className={`${askCap} mt-1`}>All-time rank</dt>
              <dd className="text-[56px] leading-tight font-extrabold tabular-nums">
                {result.tied_count ? `T-${ordinal(result.rank)}` : ordinal(result.rank)}
              </dd>
            </div>
            <div className="flex flex-col-reverse">
              <dt className={`${askCap} mt-1`}>Career {statLabel.toLowerCase()}</dt>
              <dd className="text-[56px] leading-tight font-extrabold tabular-nums">{result.values[0].display}</dd>
            </div>
            {result.tied_count && <p className="col-span-2 text-sm text-hw-muted">{result.tied_count} players share this rank.</p>}
          </dl>
        ))}

        {result.view === "leaders" && (
          <div className="overflow-x-auto" tabIndex={0} role="region" aria-label={`${title} table, scroll horizontally if needed`}>
            <table className="w-full text-left text-xs">
              <caption className="sr-only">{phase} {title.toLowerCase()}, top {result.limit}</caption>
              <thead className={askCap}><tr>
                <th scope="col" className="pb-2 pr-3">Rank</th>
                <th scope="col" className="pb-2 pr-3">Player</th>
                <th scope="col" className="pb-2 pl-3 text-right">Total</th>
              </tr></thead>
              <tbody>{result.rows.map(row => {
                const leader = row.rank === 1;
                const tied = tiedRanks.has(row.rank);
                return (
                  <tr key={row.player.player_id} className="border-t border-hw-line" data-leader={leader || undefined}>
                    <td className={`py-3 pr-3 font-extrabold tabular-nums ${leader ? "text-hw-accent-ink" : "text-hw-muted"}`}>
                      <span aria-hidden="true">{tied ? `T${row.rank}` : row.rank}</span>
                      <span className="sr-only">{tied ? `Tied for rank ${row.rank}` : `Rank ${row.rank}`}</span>
                    </td>
                    <th scope="row" className={`py-3 pr-3 ${leader ? "text-sm font-extrabold" : "font-bold"}`}>
                      {row.player.name}
                      {row.active && <span className="ml-2 text-[10px] font-extrabold tracking-[.1em] text-hw-muted uppercase">Active</span>}
                    </th>
                    <td className={`py-3 pl-3 text-right font-extrabold tabular-nums ${leader ? "text-lg" : ""}`}>{row.value.display}</td>
                  </tr>
                );
              })}</tbody>
            </table>
          </div>
        )}

        {result.omitted_tie && (
          <p className="mt-3 text-sm text-hw-muted">
            {result.omitted_tie.count} more players tied at rank {result.omitted_tie.rank} are not shown.
          </p>
        )}
        {result.coverage_note && <p className="mt-3 text-sm text-hw-muted">{result.coverage_note}</p>}
      </div>
      <div className="border-t border-hw-line bg-hw-surface-muted px-[18px] py-3 text-xs font-bold text-hw-muted">
        {result.view === "player_totals"
          ? `${values.every(value => value.stat.endsWith("percentage")) ? "Career shooting percentage" : measure === "per_game" ? "Career per game" : "Career totals"} · ${result.games_played} games played`
          : "All-time totals from NBA.com"}
        {tiedRanks.size > 0 && <span className="mt-1 block">T marks players tied at the same rank.</span>}
        <span className="mt-1 block">Data as of {formatAskTimestamp(result.as_of)}</span>
      </div>
    </section>
  );
}

export default AskCareerResult;
