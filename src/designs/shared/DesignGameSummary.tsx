import TeamLogos from "@/components/TeamLogos";
import type {GameSummaryData} from "@/helpers/helpers";

interface DesignGameSummaryProps { summary: GameSummaryData; }

function DesignGameSummary({summary}: DesignGameSummaryProps) {
  const periods = summary.homeTeam.periods.length === summary.awayTeam.periods.length
    ? summary.homeTeam.periods.map((period) => period.period)
    : [];
  const periodLabel = (period: number) => period <= 4 ? String(period) : period === 5 ? "OT" : `OT${period - 4}`;

  return (
    <section className="concept-game-summary">
      <span className="concept-game-summary__status">{summary.gameStatusText}</span>
      <div className="concept-game-summary__score">
        {[summary.awayTeam, summary.homeTeam].map((team) => (
          <div key={team.teamId || team.teamTricode}>
            <TeamLogos teamName={team.teamName} teamId={team.teamId} size={70} tricode={team.teamTricode} />
            <span>{team.teamTricode}</span>
            <strong>{team.score}</strong>
          </div>
        ))}
      </div>
      {periods.length > 0 && (
        <div className="concept-game-summary__periods">
          <table>
            <thead><tr><th>TEAM</th>{periods.map((period) => <th key={period}>{periodLabel(period)}</th>)}</tr></thead>
            <tbody>{[summary.awayTeam, summary.homeTeam].map((team) => <tr key={team.teamId || team.teamTricode}><th>{team.teamTricode}</th>{periods.map((period) => <td key={period}>{team.periods.find((item) => item.period === period)?.score ?? "–"}</td>)}</tr>)}</tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export default DesignGameSummary;
