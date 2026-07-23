import {Link} from "react-router";
import {ChevronLeft} from "lucide-react";
import {useBoxscorePage} from "../hooks/useBoxscorePage";
import {designPath} from "../designRoutes";
import type {AlternateDesignId} from "../types";
import DesignGameSummary from "./DesignGameSummary";
import DesignHeader from "./DesignHeader";
import DesignPlayerTable from "./DesignPlayerTable";
import PageState from "./PageState";

interface DesignBoxscorePageProps { designId: AlternateDesignId; }

function DesignBoxscorePage({designId}: DesignBoxscorePageProps) {
  const state = useBoxscorePage();
  return (
    <main className="concept-page concept-boxscore-page">
      <DesignHeader designId={designId} section="boxscore" />
      <div className="concept-back-row"><Link to={designPath(designId, "/")}><ChevronLeft aria-hidden="true" /> Scoreboard</Link><span>OFFICIAL BOX SCORE</span></div>
      {state.isLoading ? <PageState kind="loading" /> : state.isError ? <PageState kind="error" title="Box score unavailable" /> : (
        <>
          {state.summary && <DesignGameSummary summary={state.summary} />}
          {state.game ? (
            <div className="concept-player-tables">
              <DesignPlayerTable team={state.game.awayTeam} />
              <DesignPlayerTable team={state.game.homeTeam} />
            </div>
          ) : <PageState kind="empty" title="Player ledger unavailable" detail="The game summary is still available above." />}
        </>
      )}
      <footer className="concept-footer"><span>NBA SCOREZ</span><span>Game ID {state.gameId}</span></footer>
    </main>
  );
}

export default DesignBoxscorePage;
