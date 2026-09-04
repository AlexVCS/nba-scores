import TeamLogos from "@/components/TeamLogos";
import type {GameSummaryData} from "@/helpers/helpers";
import HardwoodWinnerArrow from "./HardwoodWinnerArrow";
import {hwNarrowContainer} from "./hardwoodStyles";

interface HardwoodGameSummaryProps {
  summary: GameSummaryData;
}

function HardwoodGameSummary({summary}: HardwoodGameSummaryProps) {
  const periods = summary.homeTeam.periods.length === summary.awayTeam.periods.length
    ? summary.homeTeam.periods.map((period) => period.period)
    : [];
  const periodLabel = (period: number) => period <= 4 ? String(period) : period === 5 ? "OT" : `OT${period - 4}`;
  const awayScore = Number(summary.awayTeam.score);
  const homeScore = Number(summary.homeTeam.score);
  const hasScores = summary.awayTeam.score !== "" && summary.homeTeam.score !== "";
  const winnerId = hasScores && awayScore !== homeScore
    ? (awayScore > homeScore ? summary.awayTeam : summary.homeTeam).teamId
    : null;

  return (
    <section className={`${hwNarrowContainer} mt-[46px] mb-[60px] text-center`}>
      <span className="text-sm font-extrabold tracking-[.26em] text-hw-court uppercase dark:text-hw-accent">{summary.gameStatusText}</span>
      <div className="mt-6 grid grid-cols-2 gap-px border border-hw-line bg-hw-line max-[700px]:[&_img]:size-[52px]!">
        {[summary.awayTeam, summary.homeTeam].map((team) => (
          <div key={team.teamId || team.teamTricode} className="grid grid-cols-[auto_auto_1fr] items-center gap-[18px] bg-hw-surface px-5 py-[34px] text-left max-[700px]:grid-cols-1 max-[700px]:justify-items-center max-[700px]:px-2.5 max-[700px]:py-[25px] max-[700px]:text-center">
            <TeamLogos teamName={team.teamName} teamId={team.teamId} size={70} tricode={team.teamTricode} />
            <span className="text-[28px]">{team.teamTricode}</span>
            <strong className="justify-self-end text-[clamp(3rem,8vw,6rem)] leading-[.8] font-extrabold text-hw-ink tabular-nums dark:text-hw-accent max-[700px]:justify-self-center">
              {team.teamId === winnerId && (
                <span className="text-hw-winner-arrow" aria-label="Winner">
                  <HardwoodWinnerArrow className="mr-[.14em] align-middle" />
                </span>
              )}
              {team.score}
            </strong>
          </div>
        ))}
      </div>
      {periods.length > 0 && (
        <div className="mt-3.5 overflow-x-auto rounded-hw border border-hw-line bg-hw-surface max-[700px]:hidden [&_table]:w-full [&_table]:min-w-[460px] [&_table]:border-collapse [&_th]:border-r [&_th]:border-hw-line [&_th]:px-3.5 [&_th]:py-2.5 [&_th]:text-center [&_th]:text-xs [&_td]:border-r [&_td]:border-hw-line [&_td]:px-3.5 [&_td]:py-2.5 [&_td]:text-center [&_td]:text-xs">
          <table>
            <thead><tr><th>TEAM</th>{periods.map((period) => <th key={period}>{periodLabel(period)}</th>)}</tr></thead>
            <tbody>
              {[summary.awayTeam, summary.homeTeam].map((team) => (
                <tr key={team.teamId || team.teamTricode}>
                  <th>{team.teamTricode}</th>
                  {periods.map((period) => <td key={period}>{team.periods.find((item) => item.period === period)?.score ?? "–"}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export default HardwoodGameSummary;
