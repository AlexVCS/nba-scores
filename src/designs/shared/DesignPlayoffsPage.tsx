import {usePlayoffsPage} from "../hooks/usePlayoffsPage";
import type {AlternateDesignId} from "../types";
import DesignBracket from "./DesignBracket";
import DesignHeader from "./DesignHeader";
import DesignSeasonPicker from "./DesignSeasonPicker";
import PageState from "./PageState";

interface DesignPlayoffsPageProps { designId: AlternateDesignId; }

function DesignPlayoffsPage({designId}: DesignPlayoffsPageProps) {
  const state = usePlayoffsPage();
  return (
    <main className="concept-page concept-playoffs-page">
      <DesignHeader designId={designId} section="playoffs" />
      <section className="concept-playoff-intro">
        <div><span>THE ROAD TO THE FINALS</span><h1>{state.model?.season ?? state.season ?? "NBA"} Playoffs</h1></div>
        <DesignSeasonPicker />
      </section>
      {state.isLoading ? <PageState kind="loading" /> : state.error ? <PageState kind="error" /> : state.model ? (
        <DesignBracket designId={designId} model={state.model} revealedRounds={state.revealedRounds} revealRound={state.revealRound} hideRound={state.hideRound} canRevealRound={state.canRevealRound} />
      ) : <PageState kind="empty" title="No bracket available" />}
      <footer className="concept-footer"><span>NBA SCOREZ</span><span>{state.model?.format.notes[0] ?? "Historical brackets"}</span></footer>
    </main>
  );
}

export default DesignPlayoffsPage;
