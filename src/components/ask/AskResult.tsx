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
import AskSeasonStatsResult from "./AskSeasonStatsResult";
import AskTeamRecordsResult from "./AskTeamRecordsResult";
import AskSeasonLeadersResult from "./AskSeasonLeadersResult";

interface AskResultProps {
  response: AskResponse;
  /** The global results preference. It governs only what the user did not ask for (ADR 0006). */
  resultsHidden: boolean;
  onAsk: (question: string, options: {remember: boolean}) => void;
  onChooseOption: (option: AskClarificationOption) => void;
  onRetry: () => void;
  onEditQuestion: () => void;
}

/**
 * Renders one AskResponse. Asking is consent: the answer (or the record that there is none) shows in full.
 * Clarification options, follow-up links, and suggestions were not asked for, so spoiler ones stay out
 * while results are hidden.
 */
function AskResult({response, resultsHidden, onAsk, onChooseOption, onRetry, onEditQuestion}: AskResultProps) {
  const {result} = response;
  const answered = response.outcome === "answer" || response.outcome === "not_found";

  return (
    <div className="grid gap-4">
      {response.interpretation && (
        <AskInterpretation
          interpretation={response.interpretation}
          showProtected={answered || !resultsHidden}
          onEditQuestion={onEditQuestion}
        />
      )}

      {response.outcome === "answer" && result?.kind === "games" && <AskGamesResult result={result} resultsHidden={resultsHidden} />}
      {response.outcome === "answer" && result?.kind === "boxscore_stat" && <AskStatResult result={result} />}
      {response.outcome === "answer" && result?.kind === "playoff_series" && <AskSeriesResult result={result} />}
      {response.outcome === "answer" && result?.kind === "postseason_summary" && <AskPostseasonResult result={result} resultsHidden={resultsHidden} />}

      {response.outcome === "answer" && result?.kind === "player_season_stats" && <AskSeasonStatsResult result={result} />}
      {response.outcome === "answer" && result?.kind === "team_records" && <AskTeamRecordsResult result={result} />}
      {response.outcome === "answer" && result?.kind === "season_leaders" && <AskSeasonLeadersResult result={result} />}

      {response.outcome === "needs_clarification" && response.clarification && (
        <AskClarification
          clarification={response.clarification}
          resultsHidden={resultsHidden}
          onChoose={onChooseOption}
          onEditQuestion={onEditQuestion}
        />
      )}

      {response.notice && response.outcome !== "answer" && response.outcome !== "needs_clarification" && (
        <AskNotice outcome={response.outcome} notice={response.notice} onRetry={onRetry} />
      )}

      <AskLinks links={response.links} resultsHidden={resultsHidden} />

      <AskSuggestions
        suggestions={response.suggestions}
        resultsHidden={resultsHidden}
        title={response.outcome === "answer" ? "Ask next" : "Try one of these"}
        variant={response.outcome === "answer" ? "chips" : "list"}
        onAsk={onAsk}
      />
    </div>
  );
}

export default AskResult;
