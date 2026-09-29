import type {AskClarificationOption, AskResponse} from "@/services/ask/types";
import AskClarification from "./AskClarification";
import AskGamesResult from "./AskGamesResult";
import AskInterpretation from "./AskInterpretation";
import AskLinks from "./AskLinks";
import AskNotice from "./AskNotice";
import AskPostseasonResult from "./AskPostseasonResult";
import AskSeriesResult from "./AskSeriesResult";
import AskStatResult from "./AskStatResult";
import AskSuggestions from "./AskSuggestions";
import AskRevealButton from "./AskRevealButton";
import {RESULT_GROUP} from "./askSpoilers";
import type {AskRevealControls} from "./askStyles";

interface AskResultProps {
  response: AskResponse;
  controls: AskRevealControls;
  onAsk: (question: string, options: {remember: boolean}) => void;
  onChooseOption: (option: AskClarificationOption) => void;
  onRetry: () => void;
  onEditQuestion: () => void;
}

/** Renders one AskResponse. Every protected value goes through the spoiler helpers in askSpoilers.ts. */
function AskResult({response, controls, onAsk, onChooseOption, onRetry, onEditQuestion}: AskResultProps) {
  const revealed = controls.isRevealed(RESULT_GROUP);
  const {result} = response;

  if (response.spoiler_gate && !revealed) {
    return (
      <div className="grid gap-4">
        {response.interpretation && <AskInterpretation interpretation={response.interpretation} revealed={false} omitProtected onEditQuestion={onEditQuestion} />}
        <section className="grid gap-3 rounded-[12px] border border-hw-line bg-hw-surface p-4" aria-label="Hidden answer">
          <h3 className="text-lg font-extrabold">{response.spoiler_gate.title}</h3>
          <p className="text-sm text-hw-muted">{response.spoiler_gate.message}</p>
          <AskRevealButton group={RESULT_GROUP} controls={controls} label="answer" />
        </section>
      </div>
    );
  }

  return (
    <div className="grid gap-4">
      {response.interpretation && (
        <AskInterpretation interpretation={response.interpretation} revealed={revealed} onEditQuestion={onEditQuestion} />
      )}

      {response.outcome === "answer" && result?.kind === "games" && <AskGamesResult result={result} controls={controls} />}
      {response.outcome === "answer" && result?.kind === "boxscore_stat" && <AskStatResult result={result} controls={controls} />}
      {response.outcome === "answer" && result?.kind === "playoff_series" && <AskSeriesResult result={result} controls={controls} />}
      {response.outcome === "answer" && result?.kind === "postseason_summary" && <AskPostseasonResult result={result} controls={controls} />}

      {response.outcome === "needs_clarification" && response.clarification && (
        <AskClarification
          clarification={response.clarification}
          revealed={revealed}
          onChoose={onChooseOption}
          onEditQuestion={onEditQuestion}
        />
      )}

      {response.notice && response.outcome !== "answer" && response.outcome !== "needs_clarification" && (
        <AskNotice outcome={response.outcome} notice={response.notice} onRetry={onRetry} />
      )}

      <AskLinks links={response.links} revealed={revealed} />

      <AskSuggestions
        suggestions={response.suggestions}
        revealed={revealed}
        title={response.outcome === "answer" ? "Ask next" : "Try one of these"}
        variant={response.outcome === "answer" ? "chips" : "list"}
        onAsk={onAsk}
      />
    </div>
  );
}

export default AskResult;
