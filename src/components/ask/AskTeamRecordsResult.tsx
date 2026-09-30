import type {AskTeamRecordsResult as TeamRecordsData} from "@/services/ask/types";
import {formatAskDate} from "./askFormat";
import {askCap, askCard} from "./askStyles";

interface AskTeamRecordsResultProps {
  result: TeamRecordsData;
}

function AskTeamRecordsResult({result}: AskTeamRecordsResultProps) {
  const scope = result.standings_scope === "east" ? "Eastern conference" : result.standings_scope === "west" ? "Western conference" : "NBA";
  return (
    <section className={askCard} aria-label={result.team ? `${result.team.name} season record` : `${scope} standings`}>
      <div className="p-[18px]">
        <h3 className="text-xl font-extrabold">{result.team?.name ?? `${scope} standings`}</h3>
        <p className={`${askCap} mt-1 mb-4`}>{result.season} · Regular season</p>
        {result.team ? (
          <dl className="grid grid-cols-3 gap-3">
            <div><dt className={askCap}>Wins</dt><dd className="text-4xl font-extrabold tabular-nums">{result.rows[0].wins}</dd></div>
            <div><dt className={askCap}>Losses</dt><dd className="text-4xl font-extrabold tabular-nums">{result.rows[0].losses}</dd></div>
            <div><dt className={askCap}>Win %</dt><dd className="text-2xl leading-10 font-extrabold tabular-nums">{(result.rows[0].win_percentage * 100).toFixed(1)}%</dd></div>
          </dl>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <caption className="sr-only">{result.season} {scope} regular-season wins and losses</caption>
              <thead className={askCap}><tr>
                <th scope="col" className="pb-2 pr-3">Team</th>
                <th scope="col" className="pb-2 text-right">W</th>
                <th scope="col" className="pb-2 pl-3 text-right">L</th>
                <th scope="col" className="pb-2 pl-3 text-right">Win %</th>
              </tr></thead>
              <tbody>{result.rows.map(row => (
                <tr key={row.team.team_id} className="border-t border-hw-line">
                  <th scope="row" className="py-3 pr-3 font-bold">
                    {row.team.name}
                    {row.conference && <span className="mt-0.5 block text-[10px] text-hw-muted">{row.conference === "east" ? "East" : "West"}{row.conference_rank ? ` · Conference rank ${row.conference_rank}` : ""}</span>}
                  </th>
                  <td className="py-3 text-right font-extrabold tabular-nums">{row.wins}</td>
                  <td className="py-3 pl-3 text-right font-extrabold tabular-nums">{row.losses}</td>
                  <td className="py-3 pl-3 text-right font-extrabold tabular-nums">{(row.win_percentage * 100).toFixed(1)}%</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </div>
      <p className="border-t border-hw-line bg-hw-surface-muted px-[18px] py-3 text-xs font-bold text-hw-muted">
        Data as of {formatAskDate(result.as_of.slice(0, 10))}
      </p>
    </section>
  );
}

export default AskTeamRecordsResult;
