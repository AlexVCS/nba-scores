import {Link} from "react-router";
import {ChevronLeft, ExternalLink} from "lucide-react";
import TeamLogos from "@/components/TeamLogos";
import {formatGameDate, generateWatchLink} from "@/helpers/helpers";
import {useSeriesPage} from "../hooks/useSeriesPage";
import {designPath} from "../designRoutes";
import type {AlternateDesignId} from "../types";
import DesignHeader from "./DesignHeader";
import PageState from "./PageState";
import SpoilerToggle from "./SpoilerToggle";

interface DesignSeriesPageProps { designId: AlternateDesignId; }

function DesignSeriesPage({designId}: DesignSeriesPageProps) {
  const state = useSeriesPage();
  const bracketHref = designPath(designId, `/playoffs${state.season ? `?season=${state.season}` : ""}`);

  if (!state.isValidYear) return <main className="concept-page"><DesignHeader designId={designId} section="series" /><PageState kind="error" title="Invalid season year" /></main>;
  if (state.isLoading) return <main className="concept-page"><DesignHeader designId={designId} section="series" /><PageState kind="loading" /></main>;
  if (state.error || !state.data) return <main className="concept-page"><DesignHeader designId={designId} section="series" /><PageState kind="error" /></main>;
  if (!state.series || !state.model) return <main className="concept-page"><DesignHeader designId={designId} section="series" /><PageState kind="empty" title="Series not found" /><Link className="concept-standalone-link" to={bracketHref}>Return to bracket</Link></main>;

  const [team1, team2] = state.series.teams;
  if (!team1 || !team2) return <main className="concept-page"><DesignHeader designId={designId} section="series" /><PageState kind="empty" title="Matchup unavailable" /></main>;
  const wins1 = state.series.wins[team1.id] || 0;
  const wins2 = state.series.wins[team2.id] || 0;
  const playoffYear = Number.parseInt(state.model.season.split("-")[0], 10);

  return (
    <main className="concept-page concept-series-page">
      <DesignHeader designId={designId} section="series" />
      <div className="concept-back-row"><Link to={bracketHref}><ChevronLeft aria-hidden="true" /> Bracket</Link><span>{state.series.roundName}</span></div>
      <section className="concept-series-hero">
        <span>{state.data.season} PLAYOFFS</span>
        <div className="concept-series-hero__matchup">
          {[team1, team2].map((team) => <div key={team.id}><TeamLogos teamName={team.name} teamId={team.id} size={88} tricode={team.tricode} /><strong>{team.tricode}</strong><small>{team.name}</small></div>)}
          <div className="concept-series-hero__result">
            {state.isRevealed ? <strong>{wins1}—{wins2}</strong> : <strong>VS</strong>}
            {state.isRevealed && state.series.winnerTeamTricode && <span>{state.series.winnerTeamTricode} wins</span>}
          </div>
        </div>
        <SpoilerToggle isRevealed={state.isRevealed} onChange={state.setIsRevealed} label="results" />
      </section>

      <section className="concept-series-games" id="games">
        <header><span>GAME LOG</span><h2>The series, game by game</h2></header>
        {state.series.games.map((game, index) => {
          const watch = generateWatchLink(game.awayTeam.tricode, game.homeTeam.tricode, game.gameId);
          return (
            <article key={game.gameId}>
              <span className="concept-series-games__number">{String(index + 1).padStart(2, "0")}</span>
              <time>{formatGameDate(game.date)}</time>
              <div>{state.isRevealed ? <><strong>{game.awayTeam.tricode} {game.awayTeam.score}</strong><span>—</span><strong>{game.homeTeam.score} {game.homeTeam.tricode}</strong></> : <span>Result hidden</span>}</div>
              <nav>
                {playoffYear >= 2012 && <a href={watch} target="_blank" rel="noopener noreferrer">Watch <ExternalLink aria-hidden="true" /></a>}
                {state.isRevealed && game.boxscoreAvailable && <Link to={designPath(designId, `/games/${game.gameId}/boxscore`)}>Box score</Link>}
              </nav>
            </article>
          );
        })}
      </section>
      <footer className="concept-footer"><span>NBA SCOREZ</span><span>{state.series.gameCount} games</span></footer>
    </main>
  );
}

export default DesignSeriesPage;
