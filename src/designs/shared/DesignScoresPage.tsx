import {Link} from "react-router";
import {format} from "date-fns";
import {getDefaultPlayoffSeason} from "@/helpers/helpers";
import {useScoresPage} from "../hooks/useScoresPage";
import {designPath} from "../designRoutes";
import type {AlternateDesignId} from "../types";
import DesignDatePicker from "./DesignDatePicker";
import DesignGameCard from "./DesignGameCard";
import DesignHeader from "./DesignHeader";
import PageState from "./PageState";
import SpoilerToggle from "./SpoilerToggle";

interface DesignScoresPageProps { designId: AlternateDesignId; }

function DesignScoresPage({designId}: DesignScoresPageProps) {
  const state = useScoresPage();
  const selected = /^\d{4}-\d{2}-\d{2}$/.test(state.dateParam) ? new Date(`${state.dateParam}T12:00:00`) : new Date();
  const yesterday = new Date(selected);
  yesterday.setDate(yesterday.getDate() - 1);
  const selectedLabel = state.dateParam
    ? selected.toLocaleDateString("en-US", {weekday: "long", month: "long", day: "numeric", year: "numeric"})
    : "Tonight’s games";

  return (
    <main className="concept-page concept-scores-page">
      <DesignHeader designId={designId} section="scores" />
      <section className="concept-scoreboard-intro">
        <div><span>DAILY SCOREBOARD</span><h1>{selectedLabel}</h1></div>
        <DesignDatePicker />
      </section>

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
            <Link to={designPath(designId, `/?date=${format(yesterday, "yyyy-MM-dd")}`)}>Previous day</Link>
            <Link to={designPath(designId, `/playoffs?season=${getDefaultPlayoffSeason(selected)}`)}>View that season’s playoffs</Link>
          </nav>
        </>
      ) : (
        <section className="concept-games-grid">
          {state.games.map((game, index) => <DesignGameCard key={game.gameId} designId={designId} game={game} showScores={state.showScores} index={index} />)}
        </section>
      )}
      <footer className="concept-footer"><span>NBA SCOREZ</span><span>Spoiler-safe by design</span></footer>
    </main>
  );
}

export default DesignScoresPage;
