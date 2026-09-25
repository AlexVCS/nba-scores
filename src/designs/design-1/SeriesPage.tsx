import {useEffect, useRef, type CSSProperties} from "react";
import {ExternalLink} from "lucide-react";
import {Link, useLocation} from "react-router";
import TeamLogos from "@/components/TeamLogos";
import {TEAM_COLORS} from "@/constants/teamColors";
import {formatGameDate, generateWatchLink} from "@/helpers/helpers";
import {useResultsVisibility} from "@/hooks/useResultsVisibility";
import {useSeriesPage} from "../hooks/useSeriesPage";
import {designPath} from "../designRoutes";
import HardwoodBackRow from "./components/HardwoodBackRow";
import HardwoodFloatingBracketLink from "./components/HardwoodFloatingBracketLink";
import HardwoodHeader from "./components/HardwoodHeader";
import HardwoodPage from "./components/HardwoodPage";
import HardwoodPageState from "./components/HardwoodPageState";
import HardwoodSpoilerToggle from "./components/HardwoodSpoilerToggle";
import HardwoodWinnerArrow from "./components/HardwoodWinnerArrow";
import {hwActionLink, hwNarrowContainer} from "./components/hardwoodStyles";

function SeriesPage() {
  const state = useSeriesPage();
  const location = useLocation();
  const {showAllResults} = useResultsVisibility();
  const {isRevealed, setIsRevealed} = state;
  const resultsVisible = showAllResults || state.isRevealed;
  const backRowLinkRef = useRef<HTMLAnchorElement>(null);
  const bracketHref = designPath("design-1", `/playoffs${state.season ? `?season=${state.season}` : ""}`);

  useEffect(() => {
    if (showAllResults && isRevealed) setIsRevealed(false);
  }, [isRevealed, setIsRevealed, showAllResults]);

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
      <section className={`${hwNarrowContainer} mt-12 mb-12 text-center max-[700px]:mb-10`}>
        <span className="block text-hw-heading leading-none font-bold tracking-[.01em] text-black uppercase dark:text-hw-accent-ink max-[700px]:leading-[1.1]">{state.data.season} PLAYOFFS</span>
        <div className="relative my-[22px] grid grid-cols-2 gap-px border border-hw-line bg-hw-line max-[700px]:[&_figure]:size-16! max-[700px]:[&_img]:size-16!">
          {[team1, team2].map((team) => {
            const isWinner = resultsVisible && team.tricode === state.series?.winnerTeamTricode;
            const ruleColor = hasTeamRules ? TEAM_COLORS[team.id] : undefined;
            return (
              <div className="grid min-h-[270px] content-center place-items-center bg-hw-surface px-5 py-10 max-[700px]:min-h-[220px] max-[700px]:px-2" key={team.id}>
                <TeamLogos teamName={team.name} teamId={team.id} size={64} tricode={team.tricode} />
                <strong className="mt-2.5 block text-hw-title leading-[.9] font-bold uppercase max-[700px]:text-[clamp(1.5rem,7vw,2rem)]">
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
            {resultsVisible ? <strong className="m-0 block text-[24px] leading-[.9] font-extrabold max-[700px]:text-[clamp(1.25rem,6vw,1.5rem)]">{wins1}—{wins2}</strong> : <strong className="m-0 block text-[24px] leading-[.9] font-extrabold max-[700px]:text-[clamp(1.25rem,6vw,1.5rem)]">VS</strong>}
            {resultsVisible && state.series.winnerTeamTricode && <span className="mt-1 block text-[8px] font-extrabold tracking-[.08em] uppercase">{state.series.winnerTeamTricode} wins</span>}
          </div>
        </div>
        {!showAllResults && <HardwoodSpoilerToggle isRevealed={state.isRevealed} onChange={state.setIsRevealed} label="results" />}
      </section>

      <section className={`${hwNarrowContainer} mb-20 overflow-hidden rounded-hw border border-hw-line bg-hw-surface text-hw-ink shadow-hw-card`} id="games">
        <header className="border-b-4 border-hw-accent px-6 pt-6 pb-[17px] max-[700px]:px-4 max-[700px]:pt-5">
          <h2 className="mt-[5px] text-hw-heading font-bold uppercase max-[700px]:leading-[1.1] max-[700px]:text-balance">The series, game by game</h2>
        </header>
        {state.series.games.map((game, index) => {
          const watch = generateWatchLink(game.awayTeam.tricode, game.homeTeam.tricode, game.gameId);
          return (
            <article className="relative grid min-h-[84px] grid-cols-[54px_140px_1fr_auto] items-center gap-3.5 border-b border-hw-line px-6 py-[13px] last:border-b-0 max-[700px]:grid-cols-[36px_1fr_auto] max-[700px]:gap-[9px] max-[700px]:px-4" key={game.gameId}>
              <span className="text-xl font-extrabold text-hw-ink tabular-nums dark:text-hw-accent-ink">{index + 1}</span>
              <time className="text-[11px] font-extrabold tracking-[.02em] text-hw-muted uppercase max-[700px]:hidden">{formatGameDate(game.date)}</time>
              <div className="flex justify-center gap-[9px] font-semibold text-hw-ink tabular-nums max-[700px]:justify-start max-[700px]:text-xs">
                {resultsVisible ? <><strong>{game.awayTeam.tricode} {game.awayTeam.score}</strong><span className="text-hw-muted">—</span><strong>{game.homeTeam.score} {game.homeTeam.tricode}</strong></> : <span>Result hidden</span>}
              </div>
              <nav className="flex gap-3.5 max-[700px]:flex-col max-[700px]:gap-[5px]">
                {playoffYear >= 2012 && <a className="relative z-10 inline-flex items-center gap-1.5 text-[11px] font-extrabold tracking-[.1em] text-hw-ink uppercase no-underline transition-colors hover:text-hw-accent-ink focus-visible:rounded-sm focus-visible:outline-2 focus-visible:outline-offset-3 focus-visible:outline-hw-accent dark:hover:text-hw-accent [&_svg]:w-3" href={watch} target="_blank" rel="noopener noreferrer">Watch <ExternalLink aria-hidden="true" /></a>}
                {game.gameId && <Link state={{from: location.pathname + location.search}} aria-label={`View game ${index + 1}: ${game.awayTeam.tricode} at ${game.homeTeam.tricode}`} className="after:absolute after:inset-0 inline-flex items-center gap-1.5 text-[11px] font-extrabold tracking-[.1em] text-hw-ink uppercase no-underline transition-colors hover:text-hw-accent-ink focus-visible:rounded-sm focus-visible:outline-2 focus-visible:outline-offset-3 focus-visible:outline-hw-accent dark:hover:text-hw-accent" to={designPath("design-1", `/games/${game.gameId}/boxscore?date=${game.date.slice(0, 10)}`)}>Game details</Link>}
              </nav>
            </article>
          );
        })}
      </section>
      <div className="h-[70px]" aria-hidden="true" />
      <HardwoodFloatingBracketLink href={bracketHref} watchRef={backRowLinkRef} />
    </HardwoodPage>
  );
}

export default SeriesPage;
