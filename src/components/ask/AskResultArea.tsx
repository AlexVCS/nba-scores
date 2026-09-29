import {RotateCcw, TriangleAlert} from "lucide-react";
import type {AskClarificationOption} from "@/services/ask/types";
import AskResult from "./AskResult";
import type {AskSessionState} from "./askSessionStore";
import {askButton, type AskRevealControls} from "./askStyles";

interface AskResultAreaProps {
  session: AskSessionState;
  controls: AskRevealControls;
  onAsk: (question: string, options: {remember: boolean}) => void;
  onChooseOption: (option: AskClarificationOption) => void;
  onRetry: () => void;
  onEditQuestion: () => void;
}

/** Loading and transport-failure shells around the response renderer. */
function AskResultArea({session, controls, onAsk, onChooseOption, onRetry, onEditQuestion}: AskResultAreaProps) {
  if (session.status === "loading") {
    return (
      <div className="grid gap-3" data-testid="ask-loading">
        <span className="text-[13px] font-semibold text-hw-muted">Reading your question…</span>
        <div className="h-[30px] w-2/3 animate-pulse rounded-lg bg-hw-surface-muted motion-reduce:animate-none" aria-hidden="true" />
        <div className="h-[120px] animate-pulse rounded-[12px] bg-hw-surface-muted motion-reduce:animate-none" aria-hidden="true" />
      </div>
    );
  }

  if (session.status === "error") {
    return (
      <div className="rounded-[12px] border border-hw-line bg-hw-surface px-4 py-[18px]">
        <span className="grid size-10 place-items-center rounded-[10px] bg-hw-surface-muted text-hw-accent-ink">
          <TriangleAlert className="size-5" aria-hidden="true" />
        </span>
        <h3 className="mt-3.5 text-[19px] leading-tight font-extrabold">Couldn’t reach Ask</h3>
        <p className="mt-1.5 text-[13px] leading-normal text-hw-muted">
          Check your connection and try again. Scores, boxscores, and playoffs still work.
        </p>
        <button type="button" className={`${askButton} mt-4`} onClick={onRetry}>
          <RotateCcw className="size-[13px]" aria-hidden="true" /> Try again
        </button>
      </div>
    );
  }

  if (session.status === "success" && session.response) {
    return (
      <AskResult
        response={session.response}
        controls={controls}
        onAsk={onAsk}
        onChooseOption={onChooseOption}
        onRetry={onRetry}
        onEditQuestion={onEditQuestion}
      />
    );
  }

  return null;
}

export default AskResultArea;
