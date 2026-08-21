import {useState} from "react";
import {useSearchParams} from "react-router";
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
import HardwoodScorersBook from "./components/HardwoodScorersBook";
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
      <div className="grid grid-cols-2 gap-3 switcher:grid-cols-4">
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
  // Desktop ledgers compare by default; `?view=stacked` opts into the stacked
  // layout so a link can carry the reader straight to either arrangement.
  const [searchParams, setSearchParams] = useSearchParams();
  const isComparing = searchParams.get("view") !== "stacked";
  const toggleComparing = () =>
    setSearchParams(
      (current) => {
        const next = new URLSearchParams(current);
        if (isComparing) next.set("view", "stacked");
        else next.delete("view");
        return next;
      },
      {replace: true},
    );
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
              <div className="sticky top-2.5 z-40 mx-auto mt-[26px] grid w-[min(560px,calc(100%_-_48px))] grid-cols-2 gap-1.5 rounded-[14px] border border-hw-line bg-hw-surface/88 p-1.5 shadow-hw-small backdrop-blur-[10px] min-[900px]:hidden max-[700px]:w-[min(calc(100%_-_28px),560px)]" role="group" aria-label="Choose team box score">
                {([["away", game.awayTeam], ["home", game.homeTeam]] as const).map(([key, team]) => (
                  <button className={teamButton} key={key} type="button" aria-pressed={side === key} onClick={() => setSide(key)}>
                    {team.teamTricode} <strong>{teamScore(team)}</strong>
                  </button>
                ))}
              </div>
              <div className="mx-auto mt-1 mb-20 w-[min(1180px,calc(100%_-_32px))] min-[900px]:hidden">
                <HardwoodScorersBook key={activeTeam.teamId} team={activeTeam} />
              </div>
              <div className="hidden min-[900px]:block">
                <div className="mx-auto mt-[26px] mb-[18px] flex w-[min(1180px,calc(100%_-_32px))] items-center justify-center border-y border-hw-line py-3">
                  <button
                    type="button"
                    className="min-h-[52px] min-w-[184px] cursor-pointer rounded-hw border border-hw-line bg-hw-surface px-6 text-xs font-bold tracking-[.12em] text-hw-ink uppercase whitespace-nowrap shadow-hw-small transition-[transform,background-color,color] duration-[160ms] [transition-timing-function:cubic-bezier(.16,1,.3,1)] hover:bg-hw-surface-muted active:translate-y-px focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-hw-ink motion-reduce:transition-none"
                    onClick={toggleComparing}
                  >
                    {isComparing ? "Stack teams" : "Compare teams"}
                  </button>
                </div>
                {isComparing ? (
                  <div className="mx-auto mb-20 grid w-[min(1760px,calc(100%_-_32px))] grid-cols-2 items-stretch gap-3">
                    <HardwoodScorersBook team={game.awayTeam} comparison />
                    <HardwoodScorersBook team={game.homeTeam} comparison />
                  </div>
                ) : (
                  <div className="mx-auto mb-20 grid w-[min(1180px,calc(100%_-_32px))] gap-12">
                    <HardwoodScorersBook team={game.awayTeam} />
                    <HardwoodScorersBook team={game.homeTeam} />
                  </div>
                )}
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
