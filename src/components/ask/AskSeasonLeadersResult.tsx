import type {AskSeasonLeadersResult as SeasonLeadersData} from "@/services/ask/types";
import {STAT_LABELS, formatAskTimestamp} from "./askFormat";
import {askCap, askCard, askTricode} from "./askStyles";

interface AskSeasonLeadersResultProps {
  result: SeasonLeadersData;
}

function leaderTitle(result: SeasonLeadersData): string {
  const label = STAT_LABELS[result.stat];
  if (result.stat.endsWith("percentage")) return `${label} leaders`;
  return result.aggregation === "per_game" ? `${label} per game leaders` : `Total ${label.toLowerCase()} leaders`;
}

function AskSeasonLeadersResult({result}: AskSeasonLeadersResultProps) {
  const title = leaderTitle(result);
  const phase = result.season_type === "playoffs" ? "Playoffs" : "Regular season";
  const valueHeader = result.stat.endsWith("percentage") ? STAT_LABELS[result.stat] : result.aggregation === "per_game" ? "Per game" : "Total";
  const tiedRanks = new Set(result.rows.filter((row, i) => result.rows.findIndex(other => other.rank === row.rank) !== i).map(row => row.rank));
  // Ranks come from unrounded values, so two ranks can display the same rounded number.
  const roundedApart = result.rows.some((row, i) => i > 0 && row.rank !== result.rows[i - 1].rank && row.value.display === result.rows[i - 1].value.display);

  return (
    <section className={askCard} aria-label={`${result.season} ${title}`}>
      <div className="p-[18px]">
        <h3 className="text-xl font-extrabold">{title}</h3>
        <p className={`${askCap} mt-1 mb-4`}>{result.season} · {phase} · Top {result.limit}</p>
        <div className="overflow-x-auto" tabIndex={0} role="region" aria-label={`${title} table, scroll horizontally if needed`}>
          <table className="w-full text-left text-xs">
            <caption className="sr-only">{result.season} {phase.toLowerCase()} {title.toLowerCase()}, top {result.limit}</caption>
            <thead className={askCap}><tr>
              <th scope="col" className="pb-2 pr-3">Rank</th>
              <th scope="col" className="pb-2 pr-3">Player</th>
              <th scope="col" className="pb-2 pr-3">Team</th>
              <th scope="col" className="pb-2 pl-3 text-right">GP</th>
              <th scope="col" className="pb-2 pl-3 text-right">{valueHeader}</th>
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
                  <th scope="row" className={`py-3 pr-3 ${leader ? "text-sm font-extrabold" : "font-bold"}`}>{row.player.name}</th>
                  <td className="py-3 pr-3">
                    {row.team ? <span className={askTricode} title={row.team.name}>{row.team.tricode}</span>
                      : <span className="text-hw-muted">{row.multiple_teams ? "Multiple teams" : "—"}</span>}
                  </td>
                  <td className="py-3 pl-3 text-right tabular-nums">{row.games_played}</td>
                  <td className={`py-3 pl-3 text-right font-extrabold tabular-nums ${leader ? "text-lg" : ""}`}>{row.value.display}</td>
                </tr>
              );
            })}</tbody>
          </table>
        </div>
        {result.omitted_tie && (
          <p className="mt-3 text-sm text-hw-muted">
            {result.omitted_tie.count} more players tied at rank {result.omitted_tie.rank} are not shown.
          </p>
        )}
        {result.coverage_note && <p className="mt-3 text-sm text-hw-muted">{result.coverage_note}</p>}
      </div>
      <div className="border-t border-hw-line bg-hw-surface-muted px-[18px] py-3 text-xs font-bold text-hw-muted">
        {result.qualification_note}
        {tiedRanks.size > 0 && <span className="mt-1 block">T marks players tied at the same rank.</span>}
        {roundedApart && <span className="mt-1 block">Ranks use unrounded values, so equal-looking numbers can rank apart.</span>}
        <span className="mt-1 block">Data as of {formatAskTimestamp(result.as_of)}</span>
      </div>
    </section>
  );
}

export default AskSeasonLeadersResult;
