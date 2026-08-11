import {Link} from "react-router";
import {getDefaultPlayoffSeason} from "@/helpers/helpers";
import {useScoresPage} from "../../hooks/useScoresPage";
import {designPath} from "../../designRoutes";
import MarqueeDatePicker from "../MarqueeDatePicker";
import HardwoodFooter from "./HardwoodFooter";
import HardwoodGameCard from "./HardwoodGameCard";
import HardwoodHeader from "./HardwoodHeader";
import HardwoodPage from "./HardwoodPage";
import HardwoodPageState from "./HardwoodPageState";
import HardwoodRandomGameDayLink from "./HardwoodRandomGameDayLink";
import HardwoodSpoilerToggle from "./HardwoodSpoilerToggle";
import {hwActionLink, hwContainer} from "./hardwoodStyles";

function HardwoodScoresPage() {
  const state = useScoresPage();
  const selected = /^\d{4}-\d{2}-\d{2}$/.test(state.dateParam)
    ? new Date(`${state.dateParam}T12:00:00`)
    : new Date();

  return (
    <HardwoodPage>
      <HardwoodHeader section="scores" />
      <MarqueeDatePicker />

      {state.hasStartedGames && (
        <div className={`${hwContainer} mb-5 flex items-center justify-between border-t border-hw-line pt-[15px] text-[11px] font-extrabold tracking-[.14em] text-hw-court uppercase`}>
          <span>{state.games.length} {state.games.length === 1 ? "game" : "games"}</span>
          <HardwoodSpoilerToggle isRevealed={state.showScores} onChange={state.setShowScores} />
        </div>
      )}

      {state.isLoading ? <HardwoodPageState kind="loading" /> : state.error || !state.hasData ? <HardwoodPageState kind="error" /> : state.games.length === 0 ? (
        <>
          <HardwoodPageState kind="empty" title={`No games on ${selected.toLocaleDateString("en-US", {month: "short", day: "numeric"})}`} />
          <nav className="mx-auto mt-[-54px] mb-[90px] grid w-[min(620px,calc(100%_-_56px))] grid-cols-2 gap-2.5 max-[700px]:mt-[-58px] max-[700px]:w-[min(calc(100%_-_28px),620px)] max-[700px]:grid-cols-1" aria-label="Other score destinations">
            <HardwoodRandomGameDayLink dateParam={state.dateParam} />
            <Link className={`${hwActionLink} text-hw-ink`} to={designPath("design-4", `/playoffs?season=${getDefaultPlayoffSeason(selected)}`)}>
              View that year’s playoffs
            </Link>
          </nav>
        </>
      ) : (
        <section className={`${hwContainer} grid grid-cols-2 gap-4 pb-20 max-[700px]:grid-cols-1 max-[700px]:pb-[50px]`}>
          {state.games.map((game, index) => (
            <HardwoodGameCard key={game.gameId} game={game} showScores={state.showScores} index={index} />
          ))}
        </section>
      )}
      <HardwoodFooter />
    </HardwoodPage>
  );
}

export default HardwoodScoresPage;
