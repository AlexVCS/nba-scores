import {useState} from "react";
import PlayerHeadshot from "@/components/PlayerHeadshot";
import type {Player} from "@/helpers/helpers";
import {useBoxscorePage} from "../hooks/useBoxscorePage";
import type {DesignBoxscoreTeam} from "../hooks/useBoxscorePage";
import {designPath} from "../designRoutes";
import HardwoodBackRow from "./components/HardwoodBackRow";
import HardwoodFooter from "./components/HardwoodFooter";
import HardwoodGameSummary from "./components/HardwoodGameSummary";
import HardwoodHeader from "./components/HardwoodHeader";
import HardwoodPage from "./components/HardwoodPage";
import HardwoodPageState from "./components/HardwoodPageState";
import HardwoodPlayerTable from "./components/HardwoodPlayerTable";
import {hwContainer} from "./components/hardwoodStyles";

const playerName = (player: Player) => `${player.firstName} ${player.familyName}`;
const playerNameShort = (player: Player) => `${player.firstName} ${player.familyName.charAt(0)}.`;
const didPlay = (player: Player) => player.statistics.minutes !== "";
const teamScore = (team: DesignBoxscoreTeam) => team.statistics?.points ?? team.score;

const topPerformers = (team: DesignBoxscoreTeam, count: number) =>
  [...team.players]
    .filter(didPlay)
    .sort((a, b) => b.statistics.points - a.statistics.points)
    .slice(0, count);

function HardwoodLeaders({game}: {game: {awayTeam: DesignBoxscoreTeam; homeTeam: DesignBoxscoreTeam}}) {
  const leaders = [game.awayTeam, game.homeTeam].flatMap((team) =>
    topPerformers(team, 2).map((player) => ({team, player})),
  );
  if (leaders.length === 0) return null;

  return (
    <section className={hwContainer} aria-label="Top performers">
      <h2 className="mb-3 text-[13px] font-extrabold tracking-[.22em] uppercase">Top performers</h2>
      <div className="grid grid-cols-2 gap-3 min-[900px]:grid-cols-4">
        {leaders.map(({team, player}) => (
          <article key={player.personId} className="grid grid-cols-[auto_1fr] items-center gap-x-3 gap-y-0.5 rounded-hw border border-hw-line bg-hw-surface px-4 py-3.5 shadow-hw-card max-[700px]:gap-x-2.5 max-[700px]:px-3 max-[700px]:py-[11px] [&_figure]:contents [&_img]:row-span-3 [&_img]:h-[38px] [&_img]:w-[52px] [&_img]:max-w-none [&_img]:object-contain max-[700px]:[&_img]:h-[32px] max-[700px]:[&_img]:w-[44px]">
            <PlayerHeadshot player={player} className="block place-self-center" />
            <div className="flex min-w-0 flex-col items-start gap-0.5">
              <span className="overflow-hidden text-[13px] font-extrabold text-ellipsis whitespace-nowrap min-[700px]:hidden">{playerNameShort(player)}</span>
              <span className="hidden overflow-hidden text-[13px] font-extrabold text-ellipsis whitespace-nowrap min-[700px]:inline">{playerName(player)}</span>
              <small className="text-[9px] leading-none font-extrabold tracking-[.16em] text-hw-muted">{team.teamTricode}</small>
            </div>
            <strong className="flex items-baseline gap-1.5 text-3xl leading-none font-extrabold tracking-[-.02em] tabular-nums dark:text-hw-accent max-[700px]:text-[26px]">
              {player.statistics.points}<b className="text-[9px] font-extrabold tracking-[.16em] text-hw-accent-ink">PTS</b>
            </strong>
            <em className="text-[11px] font-semibold text-hw-muted not-italic">{player.statistics.reboundsTotal} REB · {player.statistics.assists} AST</em>
          </article>
        ))}
      </div>
    </section>
  );
}

function BoxscorePage() {
  const state = useBoxscorePage();
  const [side, setSide] = useState<"away" | "home">("away");
  const game = state.game;
  const activeTeam = game ? (side === "away" ? game.awayTeam : game.homeTeam) : null;
  const teamButton =
    "flex min-h-[46px] cursor-pointer items-center justify-center gap-2.5 rounded-hw border-0 bg-transparent text-xs font-extrabold tracking-[.14em] text-hw-muted uppercase transition-colors duration-[160ms] [transition-timing-function:ease] aria-pressed:bg-hw-accent aria-pressed:text-hw-accent-contrast motion-reduce:transition-none [&_strong]:text-lg [&_strong]:font-extrabold [&_strong]:tracking-normal [&_strong]:tabular-nums";

  return (
    <HardwoodPage>
      <HardwoodHeader section="boxscore" />
      <HardwoodBackRow href={designPath("design-4", "/")} label="Scoreboard" detail="BOX SCORE" />
      {state.isLoading ? <HardwoodPageState kind="loading" /> : state.isError ? <HardwoodPageState kind="error" title="Box score unavailable" /> : (
        <>
          {state.summary && <HardwoodGameSummary summary={state.summary} />}
          {game && activeTeam ? (
            <>
              <HardwoodLeaders game={game} />
              <div className="sticky top-2.5 z-40 mx-auto mt-[26px] grid w-[min(560px,calc(100%_-_48px))] grid-cols-2 gap-1.5 rounded-[14px] border border-hw-line bg-hw-surface/88 p-1.5 shadow-hw-small backdrop-blur-[10px] max-[700px]:w-[min(calc(100%_-_28px),560px)]" role="group" aria-label="Choose team box score">
                {([["away", game.awayTeam], ["home", game.homeTeam]] as const).map(([key, team]) => (
                  <button className={teamButton} key={key} type="button" aria-pressed={side === key} onClick={() => setSide(key)}>
                    {team.teamTricode} <strong>{teamScore(team)}</strong>
                  </button>
                ))}
              </div>
              <div className="mx-auto mt-1 mb-20 w-[min(1180px,calc(100%_-_32px))]">
                <HardwoodPlayerTable key={activeTeam.teamId} team={activeTeam} />
              </div>
            </>
          ) : <HardwoodPageState kind="empty" title="Player ledger unavailable" detail="The game summary is still available above." />}
        </>
      )}
      <HardwoodFooter detail={<>Game ID {state.gameId}</>} />
    </HardwoodPage>
  );
}

export default BoxscorePage;
