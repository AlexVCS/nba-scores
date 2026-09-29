import {Fragment, useState} from "react";
import type {CSSProperties} from "react";
import {ChevronDown, ExternalLink} from "lucide-react";
import PlayerHeadshot from "@/components/PlayerHeadshot";
import useMediaQuery from "@/hooks/useMediaQuery";
import type {Player, PlayerStatistics} from "@/helpers/helpers";
import {firstNameInitial, formatMinutesPlayed, formatPlayerNameLink} from "@/helpers/helpers";
import type {StatEventMeasure, StatEvents} from "@/helpers/statEventUrl";
import {statEventLabel, statEventUrl} from "@/helpers/statEventUrl";
import type {DesignBoxscoreTeam, DesignTeamStatistics} from "../../hooks/useBoxscorePage";
import {getActiveBoxscorePlayers} from "../../shared/inactivePlayerUtils";

type Facet = "line" | "shooting" | "hustle";

// The slice of a stat line a ledger row reads. Player rows and the team totals
// row share it, so one column definition renders both.
type StatLine = Pick<
  PlayerStatistics,
  | "minutes" | "points" | "reboundsTotal" | "assists" | "steals" | "blocks" | "turnovers" | "plusMinusPoints"
  | "fieldGoalsMade" | "fieldGoalsAttempted" | "threePointersMade" | "threePointersAttempted"
  | "freeThrowsMade" | "freeThrowsAttempted"
>;

// A value NBA.com can open as an event page. Shooting columns carry two parts
// (made and attempted) that link separately around a plain dash.
interface StatPart {
  measure: StatEventMeasure;
  value: (line: StatLine) => number;
}

interface FacetColumn {
  label: string;
  value: (line: StatLine) => string | number;
  parts?: StatPart[];
}

const part = (measure: StatEventMeasure, value: (line: StatLine) => number): StatPart => ({measure, value});

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
  const played = getActiveBoxscorePlayers(team.players).filter(didPlay).map((player) => player.statistics);
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
      {label: "REB", value: (s) => s.reboundsTotal, parts: [part("REB", (s) => s.reboundsTotal)]},
      {label: "AST", value: (s) => s.assists, parts: [part("AST", (s) => s.assists)]},
    ],
  },
  {
    id: "shooting",
    label: "Shooting",
    columns: [
      {
        label: "FG",
        value: (s) => shots(s.fieldGoalsMade, s.fieldGoalsAttempted),
        parts: [part("FGM", (s) => s.fieldGoalsMade), part("FGA", (s) => s.fieldGoalsAttempted)],
      },
      {
        label: "3PT",
        value: (s) => shots(s.threePointersMade, s.threePointersAttempted),
        parts: [part("FG3M", (s) => s.threePointersMade), part("FG3A", (s) => s.threePointersAttempted)],
      },
      {label: "FT", value: (s) => shots(s.freeThrowsMade, s.freeThrowsAttempted)},
      {label: "PTS", value: (s) => s.points},
    ],
  },
  {
    id: "hustle",
    label: "Hustle",
    columns: [
      {label: "STL", value: (s) => s.steals, parts: [part("STL", (s) => s.steals)]},
      {label: "BLK", value: (s) => s.blocks, parts: [part("BLK", (s) => s.blocks)]},
      {label: "TO", value: (s) => s.turnovers, parts: [part("TOV", (s) => s.turnovers)]},
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

const WIDE_LEDGER_QUERY = "(min-width: 768px)";

// Counters the collapsed row may already show, keyed by that row's column label.
// The sheet only repeats a number when the current row layout hides it.
interface Counter {
  column?: string;
  label: string;
  value: (player: Player) => string | number;
  measure?: StatEventMeasure;
}

const COUNTERS: Counter[] = [
  {column: "MIN", label: "Minutes", value: (p) => formatMinutesPlayed(p.statistics.minutes)},
  {column: "PTS", label: "Points", value: (p) => p.statistics.points},
  {column: "AST", label: "Assists", value: (p) => p.statistics.assists, measure: "AST"},
  {column: "STL", label: "Steals", value: (p) => p.statistics.steals, measure: "STL"},
  {column: "BLK", label: "Blocks", value: (p) => p.statistics.blocks, measure: "BLK"},
  {column: "TO", label: "Turnovers", value: (p) => p.statistics.turnovers, measure: "TOV"},
  {column: "+/-", label: "Plus/minus", value: (p) => signed(p.statistics.plusMinusPoints)},
];

const colLabel = "text-[8px] leading-none font-bold tracking-[.1em] text-hw-muted uppercase";

// Who a stat link points at: a player (with PlayerID) or a team total (without).
interface StatLinkTarget {
  gameId?: string;
  statEvents?: StatEvents | null;
  teamId: number;
  subject: string;
  personId?: number;
}

// Dotted accent underline from the ledger mockup. The links sit above the row's
// full-width expansion button, so they opt back into pointer events.
const statLinkClass =
  "pointer-events-auto relative z-10 rounded-[3px] underline decoration-hw-accent decoration-dotted decoration-2 underline-offset-4 transition-colors duration-[120ms] hover:text-hw-accent-ink hover:decoration-solid focus-visible:bg-hw-accent focus-visible:text-hw-accent-contrast focus-visible:decoration-hw-accent-contrast focus-visible:outline-none motion-reduce:transition-none";

// Ledger stat cells clip horizontally so a link's enlarged tap target (below)
// never crosses into the neighbouring column: grid cells don't overlap, so
// neither can targets in different columns. overflow-y stays visible, so the
// vertical growth is kept. Chromium and WebKit ignore
// overflow-clip-margin with single-axis clip, so an outside focus outline
// would be cut off at the cell edge; the links show focus as a filled
// highlight inside their own box instead.
const statCellClass = "grid justify-items-end gap-[3px] overflow-x-clip";

// Where a link sits: "made" is left of a shooting dash, "attempted" right of
// it; "trailing" is a lone value flush against a ledger cell's right edge;
// "single" is a lone value with room on both sides (the expanded sheet).
type StatLinkEdge = "single" | "trailing" | "made" | "attempted";

// Tap targets (WCAG 2.5.8): a single digit renders roughly 7x14px, so an
// invisible ::after grows the hit area to at least 24x24 CSS px without moving
// the text. min(0px, ...) only extends a side when the value is narrower or
// shorter than 24px. In "4-8" the two links sit a dash apart, so their inner
// sides reach only 0.12em into the dash (a hyphen is ~0.3em or wider), leaving
// the dash's midpoint as a neutral strip; the full extra width goes outward.
// Ledger values are right-aligned in clipped cells, so a trailing value grows
// leftward only. A right-hand "attempted" value is boxed in by the dash and the
// cell edge, so in the ledger it stays roughly its own width (plus 0.12em);
// the column, not the target, is the limit there.
const statTapTarget: Record<StatLinkEdge, string> = {
  single: "after:inset-x-[min(0px,calc(50%_-_12px))]",
  trailing: "after:right-0 after:left-[min(0px,calc(100%_-_24px))]",
  made: "after:-right-[0.12em] after:left-[min(0px,calc(100%_+_0.12em_-_24px))]",
  attempted: "after:-left-[0.12em] after:right-[min(0px,calc(100%_+_0.12em_-_24px))]",
};
const statTapTargetBase = "after:absolute after:inset-y-[min(0px,calc(50%_-_12px))] after:content-['']";

function StatValue({value, measure, target, edge = "single"}: {value: number; measure: StatEventMeasure; target: StatLinkTarget; edge?: StatLinkEdge}) {
  const {gameId, statEvents, teamId, personId, subject} = target;
  const href = gameId ? statEventUrl({statEvents, gameId, teamId, personId, measure, value}) : null;
  if (!href) return <>{value}</>;
  return (
    <a className={`${statLinkClass} ${statTapTargetBase} ${statTapTarget[edge]}`} href={href} target="_blank" rel="noopener noreferrer" aria-label={statEventLabel(subject, measure)}>
      {value}
    </a>
  );
}

const partEdge = (index: number, count: number): StatLinkEdge => (count < 2 ? "trailing" : index === 0 ? "made" : "attempted");

function ColumnValue({column, line, target}: {column: FacetColumn; line: StatLine; target: StatLinkTarget}) {
  if (!column.parts) return <>{column.value(line)}</>;
  const count = column.parts.length;
  return (
    <>
      {column.parts.map((stat, index) => (
        <Fragment key={stat.measure}>
          {index > 0 && "-"}
          <StatValue value={stat.value(line)} measure={stat.measure} target={target} edge={partEdge(index, count)} />
        </Fragment>
      ))}
    </>
  );
}

function HardwoodStatSheet({player, shownColumns, target}: {player: Player; shownColumns: Set<string>; target: StatLinkTarget}) {
  const s = player.statistics;
  const shooting: Array<{label: string; made: number; attempted: number; percentage: number; measures?: [StatEventMeasure, StatEventMeasure]}> = [
    {label: "Field goals", made: s.fieldGoalsMade, attempted: s.fieldGoalsAttempted, percentage: s.fieldGoalsPercentage, measures: ["FGM", "FGA"]},
    {label: "Three pointers", made: s.threePointersMade, attempted: s.threePointersAttempted, percentage: s.threePointersPercentage, measures: ["FG3M", "FG3A"]},
    {label: "Free throws", made: s.freeThrowsMade, attempted: s.freeThrowsAttempted, percentage: s.freeThrowsPercentage},
  ];
  // Rebound splits and fouls never appear in the row, so they always lead the grid.
  const counters: Counter[] = [
    {label: "Off boards", value: () => s.reboundsOffensive, measure: "OREB"},
    {label: "Def boards", value: () => s.reboundsDefensive, measure: "DREB"},
    {label: "Fouls", value: () => s.foulsPersonal},
    ...COUNTERS.filter((counter) => !counter.column || !shownColumns.has(counter.column)),
  ];

  return (
    <div className="rounded-hw border border-dashed border-hw-line bg-hw-surface p-3.5">
      <dl className="mb-3.5 grid gap-2.5">
        {shooting.map((row) => (
          <div key={row.label} className="grid grid-cols-[74px_auto_minmax(0,1fr)_34px] items-center gap-2 min-[700px]:grid-cols-[92px_auto_minmax(0,1fr)_38px] min-[700px]:gap-2.5">
            <dt className="text-[10px] font-semibold tracking-[.04em] text-hw-muted uppercase">{row.label}</dt>
            <dd className="contents">
              <strong className="min-w-11 text-right text-xs font-bold tabular-nums">
                {row.measures ? (
                  <>
                    <StatValue value={row.made} measure={row.measures[0]} target={target} edge="made" />-<StatValue value={row.attempted} measure={row.measures[1]} target={target} edge="attempted" />
                  </>
                ) : shots(row.made, row.attempted)}
              </strong>
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
            <dd className="m-0 text-sm leading-none font-bold tabular-nums">
              {counter.measure ? <StatValue value={Number(counter.value(player))} measure={counter.measure} target={target} /> : counter.value(player)}
            </dd>
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
  gameId?: string;
  // From the boxscore response; null or absent keeps every stat plain text.
  statEvents?: StatEvents | null;
}

// Row tracks: [headshot] [name] [stat columns] [chevron]. The mobile facet always
// carries four columns; the wide ledger carries the full eleven. Stat tracks floor
// at max-content so a wide value (a totals line like "20-28") never wraps; the
// ellipsized name column absorbs the slack instead.
const rowTracks = {
  stacked:
    "grid-cols-[44px_minmax(0,1fr)_repeat(4,minmax(38px,auto))_15px] max-[420px]:grid-cols-[minmax(0,1fr)_repeat(4,minmax(38px,auto))_15px] min-[768px]:grid-cols-[36px_minmax(112px,1.6fr)_repeat(11,minmax(max-content,1fr))_15px] min-[1280px]:grid-cols-[44px_minmax(0,2fr)_repeat(11,minmax(max-content,1fr))_30px]",
  comparison: "grid-cols-[28px_minmax(82px,1.9fr)_repeat(11,minmax(max-content,1fr))_12px]",
};

function HardwoodScorersBook({team, comparison = false, gameId, statEvents = null}: HardwoodScorersBookProps) {
  const [facetId, setFacetId] = useState<Facet>("line");
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const isWide = useMediaQuery(WIDE_LEDGER_QUERY);
  const facet = FACETS.find((option) => option.id === facetId) ?? FACETS[0];
  const wide = comparison || isWide;
  const columns = wide ? WIDE_COLUMNS : facet.columns;
  const shownColumns = new Set(columns.map((column) => column.label));
  const availablePlayers = getActiveBoxscorePlayers(team.players);
  const active = availablePlayers.filter(didPlay);
  const benched = availablePlayers.filter((player) => !didPlay(player));
  const tracks = comparison ? rowTracks.comparison : rowTracks.stacked;
  const totals = teamTotals(team);
  const teamTarget: StatLinkTarget = {gameId, statEvents, teamId: team.teamId, subject: `${team.teamCity} ${team.teamName}`};
  const playerTarget = (player: Player): StatLinkTarget => ({...teamTarget, subject: playerName(player), personId: player.personId});
  const headshot = comparison
    ? "[&_figure]:contents [&_img]:block [&_img]:h-9 [&_img]:w-7 [&_img]:max-w-none [&_img]:object-contain"
    : "[&_figure]:contents [&_img]:block [&_img]:h-8 [&_img]:w-11 [&_img]:max-w-none [&_img]:object-contain max-[420px]:[&_img]:hidden min-[768px]:max-[1279px]:[&_img]:w-9";
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
          <span className={`${comparison ? "text-3xl" : "text-4xl"} leading-none text-hw-court dark:text-hw-accent-ink`}>{team.teamTricode}</span>
          <h2 className="text-hw-heading leading-none font-bold uppercase">{team.teamCity} {team.teamName}</h2>
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
          <div className={`grid items-end justify-items-end border-b border-hw-line px-3 pt-[9px] pb-1.5 text-[9px] font-bold tracking-[.1em] text-hw-muted ${tracks} ${comparison ? "gap-[3px] px-[7px] text-[8px]" : "gap-[9px] min-[768px]:max-[1279px]:gap-[3px] min-[768px]:max-[1279px]:px-2 min-[768px]:max-[1279px]:text-[8px]"}`}>
            <span />
            <span className="justify-self-start">PLAYER</span>
            {columns.map((column) => (
              <span key={column.label}>{column.label}</span>
            ))}
            {comparison ? <span /> : <span className="justify-self-end whitespace-nowrap"><span className="min-[768px]:max-[1279px]:sr-only">MORE</span></span>}
          </div>
        )}
        <ul className="m-0 flex flex-1 list-none flex-col p-0">
          {active.map((player) => {
            const isOpen = expanded.has(player.personId);
            const target = playerTarget(player);
            return (
              <li key={player.personId} className={`border-b border-hw-line last:border-b-0 ${isOpen ? "bg-hw-surface-muted shadow-[inset_3px_0_0_var(--hw-accent)]" : ""}`}>
                {/* The expansion button stretches under the whole row so the row still
                    toggles on any plain cell; stat links are siblings layered above it. */}
                <div className={`group relative grid cursor-pointer items-center text-left text-hw-ink transition-colors duration-[120ms] has-[>button:active]:bg-hw-surface-muted motion-reduce:transition-none [@media(hover:hover)]:has-[>button:hover]:bg-hw-surface-muted ${tracks} ${headshot} ${comparison ? "min-h-11 gap-1 px-[7px] py-1" : "min-h-[54px] gap-[9px] px-3 py-1.5 max-[700px]:gap-[7px] max-[700px]:px-2.5 min-[768px]:max-[1279px]:min-h-11 min-[768px]:max-[1279px]:gap-[3px] min-[768px]:max-[1279px]:px-2 min-[768px]:max-[1279px]:py-1"}`}>
                  <button
                    type="button"
                    className="absolute inset-0 cursor-pointer border-0 bg-transparent p-0 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-hw-accent-ink"
                    aria-expanded={isOpen}
                    aria-controls={`hw-sheet-${player.personId}`}
                    onClick={() => toggle(player.personId)}
                  >
                    <span className="sr-only">{playerName(player)}</span>
                  </button>
                  <span className="pointer-events-none contents" aria-hidden="true">
                    <PlayerHeadshot player={player} className="block" />
                  </span>
                  <span className={`pointer-events-none flex min-w-0 items-baseline ${comparison ? "gap-1" : "gap-1.5"}`} aria-hidden="true">
                    <span className={`overflow-hidden font-extrabold text-ellipsis whitespace-nowrap underline underline-offset-3 transition-colors duration-[120ms] group-has-[>button:hover]:text-hw-accent-ink group-has-[>button:hover]:decoration-hw-accent group-has-[>button:focus-visible]:text-hw-accent-ink group-has-[>button:focus-visible]:decoration-hw-accent motion-reduce:transition-none ${isOpen ? "text-hw-accent-ink decoration-hw-accent" : "decoration-hw-line"} ${comparison ? "text-[11px]" : "text-[13px]"} ${longName}`}>{playerName(player)}</span>
                    <span className={`overflow-hidden font-extrabold text-ellipsis whitespace-nowrap underline underline-offset-3 transition-colors duration-[120ms] group-has-[>button:hover]:text-hw-accent-ink group-has-[>button:hover]:decoration-hw-accent group-has-[>button:focus-visible]:text-hw-accent-ink group-has-[>button:focus-visible]:decoration-hw-accent motion-reduce:transition-none ${isOpen ? "text-hw-accent-ink decoration-hw-accent" : "decoration-hw-line"} ${comparison ? "text-[11px]" : "text-[13px]"} ${shortName}`}>{shortPlayerName(player)}</span>
                    {player.position && <small className="text-[8px] leading-none font-medium text-hw-muted">{player.position}</small>}
                  </span>
                  {columns.map((column) => (
                    <span key={column.label} className={`${statCellClass} pointer-events-none`}>
                      {!wide && <small className={colLabel}>{column.label}</small>}
                      <strong className={`leading-none font-bold tabular-nums whitespace-nowrap ${comparison ? "text-[10px]" : "text-[13px] min-[768px]:max-[1279px]:text-[11px]"}`}>
                        <ColumnValue column={column} line={player.statistics} target={target} />
                      </strong>
                    </span>
                  ))}
                  <ChevronDown aria-hidden="true" className={`pointer-events-none shrink-0 justify-self-end transition-transform duration-[180ms] motion-reduce:transition-none group-has-[>button:hover]:text-hw-accent-ink group-has-[>button:focus-visible]:text-hw-accent-ink ${isOpen ? "rotate-180 text-hw-accent-ink" : "text-hw-muted"} ${comparison ? "w-3" : "w-[15px]"}`} />
                </div>
                {isOpen && (
                  <div id={`hw-sheet-${player.personId}`} className="animate-hw-unfold px-3 pt-1.5 pb-3 max-[700px]:px-2.5 motion-reduce:animate-none">
                    <HardwoodStatSheet player={player} shownColumns={shownColumns} target={target} />
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
          className={`grid items-center rounded-b-[inherit] border-t border-hw-line bg-hw-surface-muted ${tracks} ${comparison ? "min-h-11 gap-1 px-[7px] py-1.5" : "min-h-[54px] gap-[9px] px-3 py-2 max-[700px]:gap-[7px] max-[700px]:px-2.5 min-[768px]:max-[1279px]:min-h-11 min-[768px]:max-[1279px]:gap-[3px] min-[768px]:max-[1279px]:px-2 min-[768px]:max-[1279px]:py-1.5"}`}
          aria-label={`${team.teamCity} ${team.teamName} totals`}
        >
          <span className={comparison ? "" : "max-[420px]:hidden"} />
          <span className={`self-center font-extrabold tracking-[.14em] uppercase ${comparison ? "text-[9px]" : "text-[10px]"}`}>Totals</span>
          {columns.map((column) => {
            const isMinutes = column.label === "MIN";
            const isPoints = column.label === "PTS";
            const isUnavailable = column.label === "+/-" && !Number.isFinite(totals.plusMinusPoints);
            return (
              <span key={column.label} className={statCellClass}>
                {isMinutes ? null : isUnavailable ? (
                  <strong className={`leading-none font-bold text-hw-muted ${comparison ? "text-[10px]" : "text-[13px] min-[768px]:max-[1279px]:text-[11px]"}`} aria-label="Not totaled">—</strong>
                ) : (
                  <strong className={`leading-none font-extrabold tabular-nums whitespace-nowrap ${comparison ? "text-[11px]" : "text-sm min-[768px]:max-[1279px]:text-[11px]"} ${isPoints ? "dark:text-hw-accent" : ""}`}>
                    <ColumnValue column={column} line={totals} target={teamTarget} />
                  </strong>
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
