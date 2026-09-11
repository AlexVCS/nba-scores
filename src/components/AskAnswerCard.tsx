import { useEffect, useState } from "react";
import type { CSSProperties } from "react";
import { Eye, EyeOff } from "lucide-react";
import { Link } from "react-router";
import PlayerHeadshot from "@/components/PlayerHeadshot";
import TeamLogos from "@/components/TeamLogos";
import { TEAM_COLORS } from "@/constants/teamColors";
import { ASK_PANEL, ASK_INTERPRETATION, ASK_INTERPRETATION_CHIP, ASK_REVEAL, ASK_VEIL, ASK_VEIL_LINE, ASK_STAT_FOCUS, ASK_TABLE_CELL, ASK_TABLE_HEADER, ASK_TABLE_VALUE, ASK_LINK } from "./askStyles";
import type { AskField, AskItem, AskTeam } from "@/helpers/ask";
import type { Player } from "@/helpers/helpers";
import { useResultsVisibility } from "@/hooks/useResultsVisibility";
import AskGameResult from "./AskGameResult";

interface AskAnswerCardProps {
  item: AskItem;
  interpretation: string[];
  makePath: (path: string) => string;
}

const ALLOWED_PATH =
  /^\/(?:\?|games\/\d+\/boxscore(?:\?|$)|playoffs(?:[/?]|$))/;

function field(item: AskItem, ...labels: string[]) {
  const wanted = labels.map((label) => label.toLowerCase());
  return item.fields.find((entry) =>
    wanted.includes(entry.label.toLowerCase()),
  );
}

function shown(value: AskField | undefined) {
  return value?.value ?? "Not available";
}

function teamName(team: AskTeam | undefined) {
  return team?.name || team?.tricode || "Team";
}

function readableContext(context?: string | null) {
  if (!context) return "";
  const [game, competition] = context.split(" · ");
  return competition && /^Game \d+$/i.test(game)
    ? `${game} of the ${competition}`
    : context;
}

function sentence(item: AskItem, interpretation: string[]) {
  const context = readableContext(item.context);
  const contextPhrase = context
    ? `${/^\w{3} \d{1,2}, \d{4}$/.test(context) ? " on " : " in "}${context}`
    : "";
  if (item.kind === "statistic") {
    const stats = item.fields;
    if (stats.length === 1) {
      const stat = stats[0];
      if (interpretation.includes("Game leaders"))
        return `${item.title} led the game with ${shown(stat)} ${stat.label.toLowerCase()}.`;
      const verb =
        stat.label.toLowerCase() === "points" ? "scored" : "recorded";
      return `${item.title} ${verb} ${shown(stat)} ${stat.label.toLowerCase()}${contextPhrase}.`;
    }
    return `${item.title}${contextPhrase}.`;
  }
  if (item.kind === "series") {
    const winnerField = field(item, "Series winner");
    if (!winnerField) return `${item.title} series result unavailable.`;
    const winnerCode = String(winnerField.value);
    const winner = item.teams?.find((team) => team.tricode === winnerCode);
    const loser = item.teams?.find((team) => team !== winner);
    if (!winner || !loser)
      return `${winnerCode} won the ${item.context || item.title}.`;
    const winnerWins = shown(
      field(item, `Team ${(item.teams?.indexOf(winner) ?? 0) + 1} wins`),
    );
    const loserWins = shown(
      field(item, `Team ${(item.teams?.indexOf(loser) ?? 0) + 1} wins`),
    );
    return `${teamName(winner)} beat ${teamName(loser)} ${winnerWins}–${loserWins} in the ${item.context || item.title}.`;
  }
  const wins = shown(field(item, "Game wins"));
  const losses = shown(field(item, "Game losses"));
  return `${item.title} went ${wins}–${losses} in the ${item.context || "playoffs"}.`;
}

function StatTable({ item }: { item: AskItem }) {
  const fields =
    item.kind === "postseason"
      ? item.fields.filter(
          (entry) => entry.label === "Games without a recorded result",
        )
      : item.fields;
  return (
    <div className="mt-5 rounded-[7px] @[600px]:overflow-x-auto @[600px]:border @[600px]:border-[var(--ask-line)]">
      <table className="block w-full border-collapse tabular-nums @[600px]:table">
        <thead className="sr-only @[600px]:not-sr-only @[600px]:table-header-group">
          <tr>
            <th scope="col" className={ASK_TABLE_HEADER}>
              {item.kind === "postseason" ||
              item.teams?.some(
                (team) =>
                  team.name === item.title || team.tricode === item.title,
              )
                ? "Team"
                : "Player"}
            </th>
            {fields.map((entry) => (
              <th scope="col" className={`${ASK_TABLE_HEADER} ${ASK_STAT_FOCUS}`} key={entry.label}>
                {entry.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="block @[600px]:table-row-group">
          <tr className="grid grid-cols-[minmax(0,1fr)_auto] rounded-[7px] border border-[var(--ask-line)] [&>:last-child]:border-b-0 @[600px]:table-row @[600px]:border-0 @[600px]:[&>*]:border-b-0">
            <th scope="row" className={`${ASK_TABLE_CELL} col-span-full gap-[.55rem] text-xs @[600px]:flex @[600px]:text-left!`}>{item.title}</th>
            {fields.map((entry) => (
              <td
                data-label={entry.label}
                className={ASK_TABLE_VALUE}
                key={entry.label}
              >
                {shown(entry)}
              </td>
            ))}
          </tr>
        </tbody>
      </table>
    </div>
  );
}

function AskAnswerCard({ item, interpretation, makePath }: AskAnswerCardProps) {
  const { showAllResults } = useResultsVisibility();
  const [revealed, setRevealed] = useState(false);
  useEffect(() => {
    if (showAllResults) setRevealed(false);
  }, [showAllResults]);
  const hasSpoilers =
    item.kind === "game" ||
    item.title_spoiler ||
    item.fields.some((entry) => entry.spoiler) ||
    item.links.some((link) => link.spoiler);
  const visible = !hasSpoilers || showAllResults || revealed;
  const colors = (item.teams ?? [])
    .map((team) => TEAM_COLORS[team.id])
    .filter(Boolean);
  const rule =
    colors.length > 1
      ? `linear-gradient(to bottom, ${colors[0]} 0 50%, ${colors[1]} 50% 100%)`
      : colors[0];
  const safeLinks = item.links.filter((link) => ALLOWED_PATH.test(link.path));
  const player = item.player_id
    ? ({ personId: item.player_id, nameI: item.title } as Player)
    : null;
  const showTable =
    item.kind === "statistic"
      ? item.fields.length > 1
      : item.kind === "postseason" &&
        item.fields.some(
          (entry) => entry.label === "Games without a recorded result",
        );

  if (item.kind === "game") {
    return <AskGameResult item={item} interpretation={interpretation}
      visible={visible} revealed={revealed} showReveal={!showAllResults}
      onToggle={() => setRevealed(value => !value)} />;
  }

  return (
    <li
      className={`${ASK_PANEL} p-[clamp(1rem,3cqw,1.5rem)] pl-[calc(clamp(1rem,3cqw,1.5rem)+4px)] before:absolute before:inset-y-0 before:left-0 before:w-1 before:[background:var(--ask-team-rule,var(--ask-accent))] before:content-['']`}
      style={
        visible && rule
          ? ({ "--ask-team-rule": rule } as CSSProperties)
          : undefined
      }
    >
      <div className="grid grid-cols-[auto_1fr_auto] items-start gap-4 @[600px]:flex">
        {visible && player && (
          <PlayerHeadshot player={player} className="col-start-1 row-start-1 block h-[45px] w-[62px] object-contain @[600px]:h-[57px] @[600px]:w-[78px]" />
        )}
        {visible &&
          !player &&
          item.kind === "series" && (
            <div className="col-start-1 row-start-1 flex gap-[.35rem]" aria-hidden="true">
              {(item.teams ?? []).map((team) => (
                <TeamLogos
                  key={`${team.id}-${team.tricode}`}
                  teamId={team.id}
                  teamName={team.name}
                  tricode={team.tricode}
                  size={38}
                />
              ))}
            </div>
          )}
        <div className="col-span-full row-start-2 min-w-0 flex-1">
          {visible && (
            <h3 className="m-0 max-w-[22ch] text-[1.35rem] leading-[1.08] font-extrabold tracking-[-.02em] uppercase [overflow-wrap:anywhere] @[600px]:max-w-[30ch] @[600px]:text-[clamp(1.35rem,3.5cqw,1.9rem)]">{sentence(item, interpretation)}</h3>
          )}
          {interpretation.length > 0 && (
            <p className={ASK_INTERPRETATION}>
              <span>Interpreted as:</span>{" "}
              {interpretation.map((part) => (
                <span className={ASK_INTERPRETATION_CHIP} key={part}>
                  {part}
                </span>
              ))}
            </p>
          )}
        </div>
        {hasSpoilers && !showAllResults && (
          <button
            type="button"
            className={ASK_REVEAL}
            aria-pressed={revealed}
            onClick={() => setRevealed((value) => !value)}
          >
            {revealed ? (
              <EyeOff size={16} aria-hidden="true" />
            ) : (
              <Eye size={16} aria-hidden="true" />
            )}
            {revealed ? "Hide result" : "Reveal result"}
          </button>
        )}
      </div>
      {!visible && (
        <div className={ASK_VEIL} aria-hidden="true">
          <span className={ASK_VEIL_LINE} />
          <span className={ASK_VEIL_LINE} />
          <span className={ASK_VEIL_LINE} />
        </div>
      )}
      {visible && (
        <>
          {showTable && <StatTable item={item} />}
          {safeLinks.length > 0 && (
            <div className="mt-4 flex">
              {safeLinks.slice(0, 1).map((link) => (
                <Link
                  className={ASK_LINK}
                  key={`${link.path}-${link.label}`}
                  to={makePath(link.path)}
                >
                  {link.label} <span aria-hidden="true">→</span>
                </Link>
              ))}
            </div>
          )}
        </>
      )}
    </li>
  );
}

export default AskAnswerCard;
