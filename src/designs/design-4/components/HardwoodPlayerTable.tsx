import PlayerHeadshot from "@/components/PlayerHeadshot";
import type {Player} from "@/helpers/helpers";
import {firstNameInitial, formatMinutesPlayed, formatPlayerNameLink} from "@/helpers/helpers";
import type {DesignBoxscoreTeam} from "../../hooks/useBoxscorePage";

interface HardwoodPlayerTableProps {
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

function HardwoodPlayerTable({team}: HardwoodPlayerTableProps) {
  return (
    <section className="mt-5">
      <header className="grid grid-cols-[auto_1fr] items-baseline gap-4 border-b-4 border-hw-accent pb-[13px]">
        <span className="text-4xl leading-none text-hw-accent-ink">{team.teamTricode}</span>
        <h2 className="text-[25px] leading-none font-extrabold uppercase">{team.teamCity} {team.teamName}</h2>
      </header>
      <div className="overflow-x-auto outline-offset-4" tabIndex={0} aria-label={`${team.teamName} player statistics`}>
        <table className="w-full min-w-[1300px] border-collapse bg-hw-surface tabular-nums">
          <thead>
            <tr>
              <th className="sticky left-0 z-[1] min-w-[190px] border-b border-hw-line bg-hw-surface px-2.5 py-3 text-left text-[9px] font-bold tracking-[.14em] text-hw-muted whitespace-nowrap min-[768px]:min-w-[260px]">PLAYER</th>
              {columns.map((column) => <th className="border-b border-hw-line px-2.5 py-3 text-right text-[9px] font-bold tracking-[.14em] text-hw-muted whitespace-nowrap" key={column.label}>{column.label}</th>)}
            </tr>
          </thead>
          <tbody>
            {team.players.map((player) => {
              const didPlay = player.statistics.minutes !== "";
              const fullName = `${player.firstName} ${player.familyName}`;
              const href = `https://www.nba.com/player/${formatPlayerNameLink({...player, nameI: fullName})}`;
              return (
                <tr key={player.personId}>
                  <th className="sticky left-0 z-[1] min-w-[190px] border-b border-hw-line bg-hw-surface px-2.5 py-3 text-left text-[11px] whitespace-nowrap min-[768px]:min-w-[260px]" scope="row">
                    <a className="inline-flex items-center gap-2.5 text-[13px] font-extrabold no-underline [&_figure]:contents [&_img]:h-[38px] [&_img]:w-[52px] [&_img]:max-w-none [&_img]:object-contain" href={href} target="_blank" rel="noopener noreferrer">
                      <PlayerHeadshot player={player} />
                      <span className="inline-flex items-baseline gap-1.5 whitespace-nowrap">
                        <span className="min-[768px]:hidden">{firstNameInitial(fullName)}</span>
                        <span className="hidden min-[768px]:inline">{fullName}</span>
                        <small className="m-0 text-[8px] leading-none text-hw-muted">{player.position || player.jerseyNum}</small>
                      </span>
                    </a>
                  </th>
                  {didPlay
                    ? columns.map((column) => <td className="border-b border-hw-line px-2.5 py-3 text-right text-[11px] whitespace-nowrap" key={column.label}>{column.value(player)}</td>)
                    : <td className="border-b border-hw-line px-2.5 py-3 text-left text-[11px] whitespace-nowrap" colSpan={columns.length}>{player.comment || "DNP — Coach’s Decision"}</td>}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default HardwoodPlayerTable;
