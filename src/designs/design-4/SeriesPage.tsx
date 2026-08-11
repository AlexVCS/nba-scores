import {useRef, type CSSProperties} from "react";
import {ExternalLink} from "lucide-react";
import {Link} from "react-router";
import TeamLogos from "@/components/TeamLogos";
import {TEAM_COLORS} from "@/constants/teamColors";
import {formatGameDate, generateWatchLink} from "@/helpers/helpers";
import {useSeriesPage} from "../hooks/useSeriesPage";
import {designPath} from "../designRoutes";
import HardwoodBackRow from "./components/HardwoodBackRow";
import HardwoodFloatingBracketLink from "./components/HardwoodFloatingBracketLink";
import HardwoodFooter from "./components/HardwoodFooter";
import HardwoodHeader from "./components/HardwoodHeader";
import HardwoodPage from "./components/HardwoodPage";
import HardwoodPageState from "./components/HardwoodPageState";
import HardwoodSpoilerToggle from "./components/HardwoodSpoilerToggle";
import HardwoodWinnerArrow from "./components/HardwoodWinnerArrow";
import {hwActionLink, hwNarrowContainer} from "./components/hardwoodStyles";

function SeriesPage() {
  const state = useSeriesPage();
  const backRowLinkRef = useRef<HTMLAnchorElement>(null);
  const bracketHref = designPath("design-4", `/playoffs${state.season ? `?season=${state.season}` : ""}`);

  if (!state.isValidYear) return <HardwoodPage><HardwoodHeader section="series" /><HardwoodPageState kind="error" title="Invalid season year" /></HardwoodPage>;
  if (state.isLoading) return <HardwoodPage><HardwoodHeader section="series" /><HardwoodPageState kind="loading" /></HardwoodPage>;
  if (state.error || !state.data) return <HardwoodPage><HardwoodHeader section="series" /><HardwoodPageState kind="error" /></HardwoodPage>;
  if (!state.series || !state.model) return (
    <HardwoodPage>
      <HardwoodHeader section="series" />
      <HardwoodPageState kind="empty" title="Series not found" />
      <Link className={`${hwActionLink} mx-auto mt-[-60px] mb-[90px] w-[min(620px,calc(100%_-_48px))]`} to={bracketHref}>Return to bracket</Link>
    </HardwoodPage>
  );

  const [team1, team2] = state.series.teams;
  if (!team1 || !team2) return <HardwoodPage><HardwoodHeader section="series" /><HardwoodPageState kind="empty" title="Matchup unavailable" /></HardwoodPage>;
  const wins1 = state.series.wins[team1.id] || 0;
  const wins2 = state.series.wins[team2.id] || 0;
  const hasTeamRules = Boolean(TEAM_COLORS[team1.id] && TEAM_COLORS[team2.id]);
  const playoffYear = Number.parseInt(state.model.season.split("-")[0], 10);

  return (
    <HardwoodPage>
      <HardwoodHeader section="series" />
      <HardwoodBackRow href={bracketHref} label="Bracket" detail={state.series.roundName} linkRef={backRowLinkRef} />
      <section className={`${hwNarrowContainer} mt-12 mb-[70px] text-center`}>
        <span className="block text-[30px] leading-none font-extrabold tracking-[.01em] text-black uppercase dark:text-hw-accent-ink max-[700px]:text-[clamp(1.25rem,6vw,1.5rem)] max-[700px]:leading-[1.1]">{state.data.season} PLAYOFFS</span>
        <div className="relative my-[22px] grid grid-cols-2 gap-px border border-hw-line bg-hw-line max-[700px]:[&_figure]:size-16! max-[700px]:[&_img]:size-16!">
          {[team1, team2].map((team) => {
            const isWinner = state.isRevealed && team.tricode === state.series?.winnerTeamTricode;
            const ruleColor = hasTeamRules ? TEAM_COLORS[team.id] : undefined;
            return (
              <div className="grid min-h-[270px] content-center place-items-center bg-hw-surface px-5 py-10 max-[700px]:min-h-[220px] max-[700px]:px-2" key={team.id}>
                <TeamLogos teamName={team.name} teamId={team.id} size={88} tricode={team.tricode} />
                <strong className="mt-2.5 block text-[clamp(2.5rem,7vw,5rem)] leading-[.9] font-extrabold uppercase max-[700px]:text-[clamp(1.9rem,9vw,3rem)]">
                  {isWinner && <span className="text-hw-winner-arrow" aria-label="Series winner"><HardwoodWinnerArrow className="mr-[.14em] align-middle" /></span>}
                  {team.tricode}
                </strong>
                {ruleColor && (
                  <span
                    aria-hidden="true"
                    className="mt-3 h-1 w-14 rounded-full bg-(--team-rule) dark:bg-[color-mix(in_srgb,var(--team-rule)_65%,white)]"
                    style={{"--team-rule": ruleColor} as CSSProperties}
                  />
                )}
                <small className="mt-[7px] text-[10px] text-hw-muted uppercase max-[700px]:hidden">{team.name}</small>
              </div>
            );
          })}
          <div className="absolute top-1/2 left-1/2 z-[2] min-w-[110px] -translate-1/2 rounded-xl bg-hw-accent p-3 text-hw-accent-contrast max-[700px]:min-w-[clamp(48px,16vw,72px)] max-[700px]:p-2">
            {state.isRevealed ? <strong className="m-0 block text-[28px] leading-[.9] font-extrabold max-[700px]:text-[clamp(1.25rem,6vw,1.5rem)]">{wins1}—{wins2}</strong> : <strong className="m-0 block text-[28px] leading-[.9] font-extrabold max-[700px]:text-[clamp(1.25rem,6vw,1.5rem)]">VS</strong>}
            {state.isRevealed && state.series.winnerTeamTricode && <span className="mt-1 block text-[8px] font-extrabold tracking-[.08em] uppercase">{state.series.winnerTeamTricode} wins</span>}
          </div>
        </div>
        <HardwoodSpoilerToggle isRevealed={state.isRevealed} onChange={state.setIsRevealed} label="results" />
      </section>

      <section className={`${hwNarrowContainer} mb-20`} id="games">
        <header className="border-b-4 border-hw-accent pb-[17px]">
          <h2 className="mt-[5px] text-[30px] font-extrabold uppercase max-[700px]:text-[clamp(1.25rem,6vw,1.5rem)] max-[700px]:leading-[1.1] max-[700px]:text-balance">The series, game by game</h2>
        </header>
        {state.series.games.map((game, index) => {
          const watch = generateWatchLink(game.awayTeam.tricode, game.homeTeam.tricode, game.gameId);
          return (
            <article className="grid min-h-[76px] grid-cols-[54px_140px_1fr_auto] items-center gap-3.5 border-b border-hw-line px-1 py-[13px] max-[700px]:grid-cols-[36px_1fr_auto] max-[700px]:gap-[9px]" key={game.gameId}>
              <span className="text-xl font-extrabold text-hw-ink tabular-nums dark:text-hw-accent-ink">{index + 1}</span>
              <time className="text-[10px] font-extrabold text-hw-muted uppercase max-[700px]:hidden">{formatGameDate(game.date)}</time>
              <div className="flex justify-center gap-[9px] tabular-nums max-[700px]:justify-start max-[700px]:text-xs">
                {state.isRevealed ? <><strong>{game.awayTeam.tricode} {game.awayTeam.score}</strong><span className="text-hw-muted">—</span><strong>{game.homeTeam.score} {game.homeTeam.tricode}</strong></> : <span className="text-hw-muted">Result hidden</span>}
              </div>
              <nav className="flex gap-3.5 max-[700px]:flex-col max-[700px]:gap-[5px]">
                {playoffYear >= 2012 && <a className="inline-flex items-center gap-1.5 text-[10px] font-extrabold tracking-[.1em] uppercase no-underline [&_svg]:w-3" href={watch} target="_blank" rel="noopener noreferrer">Watch <ExternalLink aria-hidden="true" /></a>}
                {state.isRevealed && game.boxscoreAvailable && <Link className="inline-flex items-center gap-1.5 text-[10px] font-extrabold tracking-[.1em] uppercase no-underline" to={designPath("design-4", `/games/${game.gameId}/boxscore`)}>Box score</Link>}
              </nav>
            </article>
          );
        })}
      </section>
      <HardwoodFooter detail={<>{state.series.gameCount} games</>} />
      <div className="h-[70px]" aria-hidden="true" />
      <HardwoodFloatingBracketLink href={bracketHref} watchRef={backRowLinkRef} />
    </HardwoodPage>
  );
}

export default SeriesPage;
