import type {ReactNode} from "react";
import {Link} from "react-router";
import {getDefaultPlayoffSeason} from "@/helpers/helpers";
import {useScoresPage} from "../hooks/useScoresPage";
import {designPath} from "../designRoutes";
import type {AlternateDesignId} from "../types";
import DesignDatePicker from "./DesignDatePicker";
import DesignGameCard from "./DesignGameCard";
import DesignHeader from "./DesignHeader";
import PageState from "./PageState";
import RandomGameDayLink from "./RandomGameDayLink";
import SpoilerToggle from "./SpoilerToggle";

interface DesignScoresPageProps {
  designId: AlternateDesignId;
  /** Optional replacement for the default marquee + date-picker intro band. */
  intro?: ReactNode;
}

function DesignScoresPage({designId, intro}: DesignScoresPageProps) {
  const state = useScoresPage();
  const selected = /^\d{4}-\d{2}-\d{2}$/.test(state.dateParam) ? new Date(`${state.dateParam}T12:00:00`) : new Date();
  const selectedLabel = state.dateParam
    ? selected.toLocaleDateString("en-US", {weekday: "long", month: "long", day: "numeric", year: "numeric"})
    : "Tonight’s games";

  return (
    <main className="concept-page concept-scores-page">
      <DesignHeader designId={designId} section="scores" />
      {intro ?? (
        <section className="concept-scoreboard-intro">
          <div><h1>{selectedLabel}</h1></div>
          <DesignDatePicker />
        </section>
      )}

      {state.hasStartedGames && (
        <div className="concept-scoreboard-toolbar">
          <span>{state.games.length} {state.games.length === 1 ? "game" : "games"}</span>
          <SpoilerToggle isRevealed={state.showScores} onChange={state.setShowScores} />
        </div>
      )}

      {state.isLoading ? <PageState kind="loading" /> : state.error || !state.hasData ? <PageState kind="error" /> : state.games.length === 0 ? (
        <>
          <PageState kind="empty" title={`No games on ${selected.toLocaleDateString("en-US", {month: "short", day: "numeric"})}`} />
          <nav className="concept-empty-links" aria-label="Other score destinations">
            {designId === "design-4" && <RandomGameDayLink dateParam={state.dateParam} designId={designId} />}
            <Link className="concept-empty-links__secondary" to={designPath(designId, `/playoffs?season=${getDefaultPlayoffSeason(selected)}`)}>View that year’s playoffs</Link>
          </nav>
        </>
      ) : (
        <section className="concept-games-grid">
          {state.games.map((game, index) => <DesignGameCard key={game.gameId} designId={designId} game={game} showScores={state.showScores} index={index} />)}
        </section>
      )}
      <footer className="concept-footer"><span>NBA SCOREZ</span></footer>
    </main>
  );
}

export default DesignScoresPage;
