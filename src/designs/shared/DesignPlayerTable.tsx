import {useState} from "react";
import PlayerHeadshot from "@/components/PlayerHeadshot";
import type {Player} from "@/helpers/helpers";
import {formatMinutesPlayed, formatPlayerNameLink} from "@/helpers/helpers";
import type {DesignBoxscoreTeam} from "../hooks/useBoxscorePage";

interface DesignPlayerTableProps {
  team: DesignBoxscoreTeam;
}

interface StatColumn {
  label: string;
  value: (player: Player) => string | number;
}

const percent = (value: number) => `${(value * 100).toFixed(1)}%`;
const columns: StatColumn[] = [
  {label: "PTS", value: (p) => p.statistics.points},
  {label: "REB", value: (p) => p.statistics.reboundsTotal},
  {label: "OREB", value: (p) => p.statistics.reboundsOffensive},
  {label: "DREB", value: (p) => p.statistics.reboundsDefensive},
  {label: "AST", value: (p) => p.statistics.assists},
  {label: "TO", value: (p) => p.statistics.turnovers},
  {label: "STL", value: (p) => p.statistics.steals},
  {label: "BLK", value: (p) => p.statistics.blocks},
  {label: "PF", value: (p) => p.statistics.foulsPersonal},
  {label: "+/-", value: (p) => p.statistics.plusMinusPoints},
  {label: "MIN", value: (p) => formatMinutesPlayed(p.statistics.minutes)},
  {label: "FGM", value: (p) => p.statistics.fieldGoalsMade},
  {label: "FGA", value: (p) => p.statistics.fieldGoalsAttempted},
  {label: "FG%", value: (p) => percent(p.statistics.fieldGoalsPercentage)},
  {label: "3PM", value: (p) => p.statistics.threePointersMade},
  {label: "3PA", value: (p) => p.statistics.threePointersAttempted},
  {label: "3P%", value: (p) => percent(p.statistics.threePointersPercentage)},
  {label: "FTM", value: (p) => p.statistics.freeThrowsMade},
  {label: "FTA", value: (p) => p.statistics.freeThrowsAttempted},
  {label: "FT%", value: (p) => percent(p.statistics.freeThrowsPercentage)},
];

const COMPACT_LABELS = new Set(["PTS", "REB", "AST", "TO", "STL", "BLK", "+/-", "MIN"]);

function DesignPlayerTable({team}: DesignPlayerTableProps) {
  const [showAllStats, setShowAllStats] = useState(true);
  const visibleColumns = showAllStats ? columns : columns.filter((column) => COMPACT_LABELS.has(column.label));

  return (
    <section className={`concept-player-ledger ${showAllStats ? "concept-player-ledger--full" : "concept-player-ledger--compact"}`}>
      <header>
        <span>{team.teamTricode}</span>
        <h2>{team.teamCity} {team.teamName}</h2>
        <div className="concept-stat-toggle" role="group" aria-label={`${team.teamName} stat columns`}>
          <button type="button" aria-pressed={!showAllStats} onClick={() => setShowAllStats(false)}>Compact</button>
          <button type="button" aria-pressed={showAllStats} onClick={() => setShowAllStats(true)}>All stats</button>
        </div>
      </header>
      <div className="concept-player-ledger__scroll" tabIndex={0} aria-label={`${team.teamName} player statistics`}>
        <table>
          <thead><tr><th>PLAYER</th>{visibleColumns.map((column) => <th key={column.label}>{column.label}</th>)}</tr></thead>
          <tbody>
            {team.players.map((player) => {
              const didPlay = player.statistics.minutes !== "";
              const fullName = `${player.firstName} ${player.familyName}`;
              const href = `https://www.nba.com/player/${formatPlayerNameLink({...player, nameI: fullName})}`;
              return (
                <tr key={player.personId}>
                  <th scope="row">
                    <a className="concept-player-ledger__player" href={href} target="_blank" rel="noopener noreferrer">
                      <PlayerHeadshot player={player} />
                      <span className="concept-player-ledger__player-copy">
                        <span>{fullName}</span>
                        <small>{player.position || player.jerseyNum}</small>
                      </span>
                    </a>
                  </th>
                  {didPlay
                    ? visibleColumns.map((column) => <td key={column.label}>{column.value(player)}</td>)
                    : <td className="concept-player-ledger__dnp" colSpan={visibleColumns.length}>{player.comment || "DNP — Coach’s Decision"}</td>}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default DesignPlayerTable;
