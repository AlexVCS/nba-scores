import {useEffect, useState} from "react";
import type {CSSProperties} from "react";
import {ChevronDown, ExternalLink} from "lucide-react";
import PlayerHeadshot from "@/components/PlayerHeadshot";
import type {Player, PlayerStatistics} from "@/helpers/helpers";
import {firstNameInitial, formatMinutesPlayed, formatPlayerNameLink} from "@/helpers/helpers";
import type {DesignBoxscoreTeam, DesignTeamStatistics} from "../../hooks/useBoxscorePage";

type Facet = "line" | "shooting" | "hustle";

// The slice of a stat line a ledger row reads. Player rows and the team totals
// row share it, so one column definition renders both.
type StatLine = Pick<
  PlayerStatistics,
  | "minutes" | "points" | "reboundsTotal" | "assists" | "steals" | "blocks" | "turnovers" | "plusMinusPoints"
  | "fieldGoalsMade" | "fieldGoalsAttempted" | "threePointersMade" | "threePointersAttempted"
  | "freeThrowsMade" | "freeThrowsAttempted"
>;

interface FacetColumn {
  label: string;
  value: (line: StatLine) => string | number;
}

const playerName = (player: Player) => `${player.firstName} ${player.familyName}`;
const shortPlayerName = (player: Player) => firstNameInitial(playerName(player));
const didPlay = (player: Player) => player.statistics.minutes !== "";
const signed = (value: number) => (value > 0 ? `+${value}` : String(value));
const shots = (made: number, attempted: number) => `${made}-${attempted}`;

// Team totals come from the box score endpoint's team statistics. Anything the
// payload leaves out is summed from the players who took the floor, so the row
// never goes blank on an older or partial response.
const teamTotals = (team: DesignBoxscoreTeam): StatLine => {
  const stats: DesignTeamStatistics = team.statistics ?? {points: team.score};
  const played = team.players.filter(didPlay).map((player) => player.statistics);
  const sum = (key: keyof Omit<StatLine, "minutes">) => played.reduce((total, line) => total + (line[key] ?? 0), 0);
  const pick = (key: Exclude<keyof DesignTeamStatistics, "points" | "minutes">, fallback: keyof Omit<StatLine, "minutes">) =>
    stats[key] ?? sum(fallback);
  return {
    minutes: stats.minutes ?? `PT${played.reduce((total, line) => total + Number(formatMinutesPlayed(line.minutes)), 0)}M`,
    points: stats.points ?? sum("points"),
    fieldGoalsMade: pick("fieldGoalsMade", "fieldGoalsMade"),
    fieldGoalsAttempted: pick("fieldGoalsAttempted", "fieldGoalsAttempted"),
    threePointersMade: pick("threePointersMade", "threePointersMade"),
    threePointersAttempted: pick("threePointersAttempted", "threePointersAttempted"),
    freeThrowsMade: pick("freeThrowsMade", "freeThrowsMade"),
    freeThrowsAttempted: pick("freeThrowsAttempted", "freeThrowsAttempted"),
    reboundsTotal: pick("reboundsTotal", "reboundsTotal"),
    assists: pick("assists", "assists"),
    steals: pick("steals", "steals"),
    blocks: pick("blocks", "blocks"),
    turnovers: pick("turnovers", "turnovers"),
    plusMinusPoints: stats.plusMinusPoints ?? Number.NaN,
  };
};

const profileHref = (player: Player) =>
  `https://www.nba.com/player/${formatPlayerNameLink({...player, nameI: playerName(player)})}`;

const FACETS: Array<{id: Facet; label: string; columns: FacetColumn[]}> = [
  {
    id: "line",
    label: "Line",
    columns: [
      {label: "MIN", value: (s) => formatMinutesPlayed(s.minutes)},
      {label: "PTS", value: (s) => s.points},
      {label: "REB", value: (s) => s.reboundsTotal},
      {label: "AST", value: (s) => s.assists},
    ],
  },
  {
    id: "shooting",
    label: "Shooting",
    columns: [
      {label: "FG", value: (s) => shots(s.fieldGoalsMade, s.fieldGoalsAttempted)},
      {label: "3PT", value: (s) => shots(s.threePointersMade, s.threePointersAttempted)},
      {label: "FT", value: (s) => shots(s.freeThrowsMade, s.freeThrowsAttempted)},
      {label: "PTS", value: (s) => s.points},
    ],
  },
  {
    id: "hustle",
    label: "Hustle",
    columns: [
      {label: "STL", value: (s) => s.steals},
      {label: "BLK", value: (s) => s.blocks},
      {label: "TO", value: (s) => s.turnovers},
      {label: "+/-", value: (s) => signed(s.plusMinusPoints)},
    ],
  },
];

const ALL_COLUMNS: FacetColumn[] = FACETS.flatMap((option) => option.columns).filter(
  (column, index, columns) => columns.findIndex((other) => other.label === column.label) === index,
);

// The wide ledger follows the reading path of a traditional basketball box score.
const WIDE_COLUMNS: FacetColumn[] = ["MIN", "FG", "3PT", "FT", "REB", "AST", "STL", "BLK", "TO", "+/-", "PTS"].map(
  (label) => ALL_COLUMNS.find((column) => column.label === label)!,
);

const WIDE_LEDGER_QUERY = "(min-width: 900px)";

function useWideLedger() {
  const [isWide, setIsWide] = useState(
    () => typeof window !== "undefined" && (window.matchMedia?.(WIDE_LEDGER_QUERY).matches ?? false),
  );
  useEffect(() => {
    const query = window.matchMedia?.(WIDE_LEDGER_QUERY);
    if (!query) return undefined;
    const onChange = (event: MediaQueryListEvent) => setIsWide(event.matches);
    query.addEventListener("change", onChange);
    return () => query.removeEventListener("change", onChange);
  }, []);
  return isWide;
}

// Counters the collapsed row may already show, keyed by that row's column label.
// The sheet only repeats a number when the current row layout hides it.
const COUNTERS: Array<{column: string; label: string; value: (player: Player) => string | number}> = [
  {column: "MIN", label: "Minutes", value: (p) => formatMinutesPlayed(p.statistics.minutes)},
  {column: "PTS", label: "Points", value: (p) => p.statistics.points},
  {column: "AST", label: "Assists", value: (p) => p.statistics.assists},
  {column: "STL", label: "Steals", value: (p) => p.statistics.steals},
  {column: "BLK", label: "Blocks", value: (p) => p.statistics.blocks},
  {column: "TO", label: "Turnovers", value: (p) => p.statistics.turnovers},
  {column: "+/-", label: "Plus/minus", value: (p) => signed(p.statistics.plusMinusPoints)},
];

const colLabel = "text-[8px] leading-none font-bold tracking-[.1em] text-hw-muted uppercase";

function HardwoodStatSheet({player, shownColumns}: {player: Player; shownColumns: Set<string>}) {
  const s = player.statistics;
  const shooting = [
    {label: "Field goals", made: s.fieldGoalsMade, attempted: s.fieldGoalsAttempted, percentage: s.fieldGoalsPercentage},
    {label: "Three pointers", made: s.threePointersMade, attempted: s.threePointersAttempted, percentage: s.threePointersPercentage},
    {label: "Free throws", made: s.freeThrowsMade, attempted: s.freeThrowsAttempted, percentage: s.freeThrowsPercentage},
  ];
  // Rebound splits and fouls never appear in the row, so they always lead the grid.
  const counters = [
    {label: "Off boards", value: () => s.reboundsOffensive},
    {label: "Def boards", value: () => s.reboundsDefensive},
    {label: "Fouls", value: () => s.foulsPersonal},
    ...COUNTERS.filter((counter) => !shownColumns.has(counter.column)),
  ];

  return (
    <div className="rounded-hw border border-dashed border-hw-line bg-hw-surface p-3.5">
      <dl className="mb-3.5 grid gap-2.5">
        {shooting.map((row) => (
          <div key={row.label} className="grid grid-cols-[74px_auto_minmax(0,1fr)_34px] items-center gap-2 min-[700px]:grid-cols-[92px_auto_minmax(0,1fr)_38px] min-[700px]:gap-2.5">
            <dt className="text-[10px] font-semibold tracking-[.04em] text-hw-muted uppercase">{row.label}</dt>
            <dd className="contents">
              <strong className="min-w-11 text-right text-xs font-bold tabular-nums">{shots(row.made, row.attempted)}</strong>
              <span
                className="relative h-1 overflow-hidden rounded-full bg-hw-ink/12 after:absolute after:inset-0 after:w-(--fill) after:origin-left after:rounded-full after:bg-hw-accent after:animate-hw-fill motion-reduce:after:animate-none"
                style={{"--fill": `${Math.min(row.percentage, 1) * 100}%`} as CSSProperties}
                aria-hidden="true"
              />
              <em className="text-right text-[10px] font-medium text-hw-muted tabular-nums not-italic">{row.attempted > 0 ? `${Math.round(row.percentage * 100)}%` : "—"}</em>
            </dd>
          </div>
        ))}
      </dl>
      <dl className="mb-3 flex flex-wrap gap-px overflow-hidden rounded-hw border border-hw-line bg-hw-line min-[560px]:grid min-[560px]:grid-cols-[repeat(auto-fit,minmax(96px,1fr))]">
        {counters.map((counter) => (
          <div key={counter.label} className="grid flex-[1_1_96px] justify-items-center gap-1 bg-hw-surface-muted px-2 py-[9px] text-center">
            <dt className={colLabel}>{counter.label}</dt>
            <dd className="m-0 text-sm leading-none font-bold tabular-nums">{counter.value(player)}</dd>
          </div>
        ))}
      </dl>
      <a
        className="inline-flex items-center gap-1.5 text-[10px] font-extrabold tracking-[.1em] text-hw-accent-ink uppercase no-underline hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-hw-accent-ink [&_svg]:w-[11px]"
        href={profileHref(player)}
        target="_blank"
        rel="noopener noreferrer"
      >
        Full profile <ExternalLink aria-hidden="true" />
      </a>
    </div>
  );
}

interface HardwoodScorersBookProps {
  team: DesignBoxscoreTeam;
  comparison?: boolean;
}

// Row tracks: [headshot] [name] [stat columns] [chevron]. The mobile facet always
// carries four columns; the wide ledger carries the full eleven. Stat tracks floor
// at max-content so a wide value (a totals line like "20-28") never wraps; the
// ellipsized name column absorbs the slack instead.
const rowTracks = {
  stacked:
    "grid-cols-[44px_minmax(0,1fr)_repeat(4,minmax(38px,auto))_15px] max-[420px]:grid-cols-[minmax(0,1fr)_repeat(4,minmax(38px,auto))_15px] min-[900px]:grid-cols-[44px_minmax(0,2fr)_repeat(11,minmax(max-content,1fr))_30px]",
  comparison: "grid-cols-[28px_minmax(82px,1.9fr)_repeat(11,minmax(max-content,1fr))_12px]",
};

function HardwoodScorersBook({team, comparison = false}: HardwoodScorersBookProps) {
  const [facetId, setFacetId] = useState<Facet>("line");
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const isWide = useWideLedger();
  const facet = FACETS.find((option) => option.id === facetId) ?? FACETS[0];
  const wide = comparison || isWide;
  const columns = wide ? WIDE_COLUMNS : facet.columns;
  const shownColumns = new Set(columns.map((column) => column.label));
  const active = team.players.filter(didPlay);
  const benched = team.players.filter((player) => !didPlay(player));
  const tracks = comparison ? rowTracks.comparison : rowTracks.stacked;
  const totals = teamTotals(team);
  const headshot = comparison
    ? "[&_figure]:contents [&_img]:block [&_img]:h-9 [&_img]:w-7 [&_img]:max-w-none [&_img]:object-contain"
    : "[&_figure]:contents [&_img]:block [&_img]:h-8 [&_img]:w-11 [&_img]:max-w-none [&_img]:object-contain max-[420px]:[&_img]:hidden";
  const longName = comparison ? "hidden min-[1600px]:inline" : "hidden min-[700px]:inline";
  const shortName = comparison ? "min-[1600px]:hidden" : "min-[700px]:hidden";

  const toggle = (personId: number) =>
    setExpanded((current) => {
      const next = new Set(current);
      if (next.has(personId)) next.delete(personId);
      else next.add(personId);
      return next;
    });

  return (
    <section
      className={`flex min-w-0 flex-col ${comparison ? "" : "mt-5"}`}
      aria-label={`${team.teamCity} ${team.teamName} player statistics`}
    >
      <header className="flex items-end justify-between gap-3.5 border-b-4 border-hw-accent pb-3 max-[700px]:flex-col max-[700px]:items-stretch">
        <div className="grid grid-cols-[auto_1fr] items-baseline gap-4 max-[700px]:h-[60px]">
          <span className={`${comparison ? "text-3xl" : "text-4xl"} leading-none text-hw-accent-ink`}>{team.teamTricode}</span>
          <h2 className={`${comparison ? "text-xl" : "text-[25px]"} leading-none font-extrabold uppercase`}>{team.teamCity} {team.teamName}</h2>
        </div>
        {!wide && (
          <div className="inline-flex gap-[3px] rounded-[13px] border border-hw-line bg-hw-surface p-[3px] max-[700px]:grid max-[700px]:grid-cols-3" role="group" aria-label="Choose the stats shown on each row">
            {FACETS.map((option) => (
              <button
                key={option.id}
                type="button"
                className="min-h-[34px] cursor-pointer rounded-hw border-0 bg-transparent px-3 text-[10px] font-extrabold tracking-[.1em] text-hw-muted uppercase transition-colors duration-[160ms] aria-pressed:bg-hw-accent aria-pressed:text-hw-accent-contrast focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-hw-accent-ink motion-reduce:transition-none"
                aria-pressed={option.id === facetId}
                onClick={() => setFacetId(option.id)}
              >
                {option.label}
              </button>
            ))}
          </div>
        )}
      </header>
      <div className="flex min-h-0 min-w-0 flex-1 flex-col rounded-b-hw border border-t-0 border-hw-line bg-hw-surface shadow-hw-card">
        {wide && (
          <div className={`grid items-end justify-items-end border-b border-hw-line px-3 pt-[9px] pb-1.5 text-[9px] font-bold tracking-[.1em] text-hw-muted ${tracks} ${comparison ? "gap-[3px] px-[7px] text-[8px]" : "gap-[9px]"}`}>
            <span />
            <span className="justify-self-start">PLAYER</span>
            {columns.map((column) => (
              <span key={column.label}>{column.label}</span>
            ))}
            {comparison ? <span /> : <span className="justify-self-end whitespace-nowrap">MORE</span>}
          </div>
        )}
        <ul className="m-0 flex flex-1 list-none flex-col p-0">
          {active.map((player) => {
            const isOpen = expanded.has(player.personId);
            return (
              <li key={player.personId} className={`border-b border-hw-line last:border-b-0 ${isOpen ? "bg-hw-surface-muted shadow-[inset_3px_0_0_var(--hw-accent)]" : ""}`}>
                <button
                  type="button"
                  className={`group grid w-full cursor-pointer items-center border-0 bg-transparent text-left text-hw-ink transition-colors duration-[120ms] focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-hw-accent-ink active:bg-hw-surface-muted motion-reduce:transition-none [@media(hover:hover)]:hover:bg-hw-surface-muted ${tracks} ${headshot} ${comparison ? "min-h-11 gap-1 px-[7px] py-1" : "min-h-[54px] gap-[9px] px-3 py-1.5 max-[700px]:gap-[7px] max-[700px]:px-2.5"}`}
                  aria-expanded={isOpen}
                  aria-controls={`hw-sheet-${player.personId}`}
                  onClick={() => toggle(player.personId)}
                >
                  <PlayerHeadshot player={player} className="block" />
                  <span className={`flex min-w-0 items-baseline ${comparison ? "gap-1" : "gap-1.5"}`}>
                    <span className="sr-only">{playerName(player)}</span>
                    <span className={`overflow-hidden font-extrabold text-ellipsis whitespace-nowrap underline decoration-hw-line underline-offset-3 transition-colors duration-[120ms] group-hover:text-hw-accent-ink group-hover:decoration-hw-accent group-aria-expanded:text-hw-accent-ink group-aria-expanded:decoration-hw-accent motion-reduce:transition-none ${comparison ? "text-[11px]" : "text-[13px]"} ${longName}`} aria-hidden="true">{playerName(player)}</span>
                    <span className={`overflow-hidden font-extrabold text-ellipsis whitespace-nowrap underline decoration-hw-line underline-offset-3 transition-colors duration-[120ms] group-hover:text-hw-accent-ink group-hover:decoration-hw-accent group-aria-expanded:text-hw-accent-ink group-aria-expanded:decoration-hw-accent motion-reduce:transition-none ${comparison ? "text-[11px]" : "text-[13px]"} ${shortName}`} aria-hidden="true">{shortPlayerName(player)}</span>
                    <small className="text-[8px] leading-none font-medium text-hw-muted">{player.position || player.jerseyNum}</small>
                  </span>
                  {columns.map((column) => (
                    <span key={column.label} className="grid justify-items-end gap-[3px]">
                      {!wide && <small className={colLabel}>{column.label}</small>}
                      <strong className={`leading-none font-bold tabular-nums whitespace-nowrap ${comparison ? "text-[10px]" : "text-[13px]"}`}>{column.value(player.statistics)}</strong>
                    </span>
                  ))}
                  <ChevronDown aria-hidden="true" className={`shrink-0 justify-self-end text-hw-muted transition-transform duration-[180ms] group-aria-expanded:rotate-180 group-aria-expanded:text-hw-accent-ink motion-reduce:transition-none ${comparison ? "w-3" : "w-[15px]"}`} />
                </button>
                {isOpen && (
                  <div id={`hw-sheet-${player.personId}`} className="animate-hw-unfold px-3 pt-1.5 pb-3 max-[700px]:px-2.5 motion-reduce:animate-none">
                    <HardwoodStatSheet player={player} shownColumns={shownColumns} />
                  </div>
                )}
              </li>
            );
          })}
          {benched.map((player) => (
            <li
              key={player.personId}
              className={`grid items-center border-b border-hw-line font-semibold last:border-b-0 ${headshot} ${comparison ? `min-h-[45px] gap-1 px-[7px] py-1 text-[10px] ${rowTracks.comparison}` : "min-h-[54px] grid-cols-[44px_minmax(118px,.7fr)_minmax(0,1fr)] gap-[9px] px-3 py-1.5 text-xs max-[700px]:grid-cols-[44px_minmax(96px,.7fr)_minmax(0,1fr)] max-[700px]:gap-[7px] max-[700px]:px-2.5 max-[420px]:grid-cols-[minmax(96px,.7fr)_minmax(0,1fr)]"}`}
            >
              <PlayerHeadshot player={player} className="block" />
              <span className="flex min-w-0 items-baseline font-extrabold" title={playerName(player)}>
                <span className="sr-only">{playerName(player)}</span>
                <span className={`overflow-hidden text-ellipsis whitespace-nowrap ${longName}`} aria-hidden="true">{playerName(player)}</span>
                <span className={`overflow-hidden text-ellipsis whitespace-nowrap ${shortName}`} aria-hidden="true">{shortPlayerName(player)}</span>
              </span>
              <small className={`min-w-0 overflow-hidden text-ellipsis whitespace-nowrap text-hw-muted ${comparison ? "col-[3/-1] text-[11px] font-semibold text-hw-ink" : "text-[10px] font-medium"}`}>{player.comment || "DNP — Coach’s Decision"}</small>
            </li>
          ))}
        </ul>
        <footer
          className={`grid items-center rounded-b-[inherit] border-t border-hw-line bg-hw-surface-muted ${tracks} ${comparison ? "min-h-11 gap-1 px-[7px] py-1.5" : "min-h-[54px] gap-[9px] px-3 py-2 max-[700px]:gap-[7px] max-[700px]:px-2.5"}`}
          aria-label={`${team.teamCity} ${team.teamName} totals`}
        >
          <span className={comparison ? "" : "max-[420px]:hidden"} />
          <span className={`self-center font-extrabold tracking-[.14em] uppercase ${comparison ? "text-[9px]" : "text-[10px]"}`}>Totals</span>
          {columns.map((column) => {
            const isMinutes = column.label === "MIN";
            const isPoints = column.label === "PTS";
            const isUnavailable = column.label === "+/-" && !Number.isFinite(totals.plusMinusPoints);
            return (
              <span key={column.label} className="grid justify-items-end gap-[3px]">
                {isMinutes ? null : isUnavailable ? (
                  <strong className={`leading-none font-bold text-hw-muted ${comparison ? "text-[10px]" : "text-[13px]"}`} aria-label="Not totaled">—</strong>
                ) : (
                  <strong className={`leading-none font-extrabold tabular-nums whitespace-nowrap ${comparison ? "text-[11px]" : "text-sm"} ${isPoints ? "dark:text-hw-accent" : ""}`}>{column.value(totals)}</strong>
                )}
              </span>
            );
          })}
          <span />
        </footer>
      </div>
    </section>
  );
}

export default HardwoodScorersBook;
