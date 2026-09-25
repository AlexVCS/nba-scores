import {useEffect} from "react";
import {Link} from "react-router";
import {getDefaultPlayoffSeason} from "@/helpers/helpers";
import {useResultsVisibility} from "@/hooks/useResultsVisibility";
import {useScoresPage} from "@/designs/hooks/useScoresPage";
import {designPath} from "@/designs/designRoutes";
import MarqueeDatePicker from "./MarqueeDatePicker";
import HardwoodGameCard from "./components/HardwoodGameCard";
import HardwoodHeader from "./components/HardwoodHeader";
import HardwoodPage from "./components/HardwoodPage";
import HardwoodPageState from "./components/HardwoodPageState";
import HardwoodRandomGameDayLink from "./components/HardwoodRandomGameDayLink";
import HardwoodSpoilerToggle from "./components/HardwoodSpoilerToggle";
import {hwActionLink, hwContainer} from "./components/hardwoodStyles";

function ScoresPage() {
  const state = useScoresPage({persistScoreReveal: false});
  const {showAllResults} = useResultsVisibility();
  const {setShowScores} = state;
  const resultsVisible = showAllResults || state.showScores;
  const selected = /^\d{4}-\d{2}-\d{2}$/.test(state.dateParam)
    ? new Date(`${state.dateParam}T12:00:00`)
    : new Date();

  useEffect(() => {
    if (showAllResults) setShowScores(false);
  }, [setShowScores, showAllResults]);

  return (
    <HardwoodPage>
      <HardwoodHeader section="scores" />
      <MarqueeDatePicker />

      {state.hasStartedGames && (
        <div className={`${hwContainer} mb-5 flex items-center justify-between border-t border-hw-line pt-[15px] text-[11px] font-extrabold tracking-[.14em] text-hw-court uppercase`}>
          <span>{state.games.length} {state.games.length === 1 ? "game" : "games"}</span>
          {!showAllResults && <HardwoodSpoilerToggle isRevealed={state.showScores} onChange={state.setShowScores} />}
        </div>
      )}

      {state.isLoading ? <HardwoodPageState kind="loading" /> : state.error || !state.hasData ? (
        <>
          <HardwoodPageState kind="error" title="Couldn't load games" detail="Try loading this date again." />
          <div className="-mt-[60px] mb-20 flex justify-center">
            <button type="button" className={hwActionLink} disabled={state.isFetching} onClick={() => void state.refetch()}>
              {state.isFetching ? "Retrying…" : "Try again"}
            </button>
          </div>
        </>
      ) : state.games.length === 0 ? (
        <>
          <HardwoodPageState kind="empty" title={`No games on ${selected.toLocaleDateString("en-US", {month: "short", day: "numeric"})}`} />
          <nav className="mx-auto mt-[-60px] mb-[90px] grid w-[min(620px,calc(100%_-_56px))] grid-cols-2 gap-2.5 max-[700px]:w-[min(calc(100%_-_28px),620px)] max-[700px]:grid-cols-1" aria-label="Other score destinations">
            <HardwoodRandomGameDayLink dateParam={state.dateParam} />
            <Link className={`${hwActionLink} text-hw-ink`} to={designPath("design-1", `/playoffs?season=${getDefaultPlayoffSeason(selected)}`)}>
              View this year’s playoffs
            </Link>
          </nav>
        </>
      ) : (
        <section className={`${hwContainer} grid ${state.games.length === 1 ? "grid-cols-[minmax(0,calc(50%_-_var(--spacing)*2))] justify-center" : "grid-cols-2"} gap-4 pb-20 max-[700px]:grid-cols-1 max-[700px]:pb-[50px]`}>
          {state.games.map((game, index) => (
            <HardwoodGameCard key={game.gameId} game={game} showScores={resultsVisible} index={index} dateParam={state.dateParam} />
          ))}
        </section>
      )}
    </HardwoodPage>
  );
}

export default ScoresPage;
