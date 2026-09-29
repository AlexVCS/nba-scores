import {CornerDownLeft, Eye, ShieldCheck} from "lucide-react";
import type {AskResponse} from "@/services/ask/types";
import {ASK_ANSWERS_SHOWN_COPY, ASK_NO_MODEL_COPY, ASK_SOURCE_COPY} from "./askCopy";
import AskResponseDetails from "./AskResponseDetails";

interface AskFooterProps {
  mode: "empty" | "typeahead" | "result";
  response: AskResponse | null;
  /** Id for the consent note, so the search field can reference it with aria-describedby. */
  consentId?: string;
}

const kbd = "inline-flex items-center rounded-md border border-hw-line bg-hw-surface px-[7px] py-[5px] text-[10px] leading-none font-bold tracking-[.06em] text-hw-muted uppercase";

function sourceLine(response: AskResponse | null): string {
  const copy = response?.interpreter.model_called === false ? ASK_NO_MODEL_COPY : ASK_SOURCE_COPY;
  const labels = [...new Set(response?.sources.map(source => source.label) ?? [])];
  const incomplete = response?.sources.some(source => !source.complete);
  return [copy, labels.length ? `Data: ${labels.join(", ")}.` : "", incomplete ? "Some games are still in progress." : ""]
    .filter(Boolean)
    .join(" ");
}

function AskFooter({mode, response, consentId}: AskFooterProps) {
  return (
    <div className="flex flex-none flex-wrap items-center gap-x-3.5 gap-y-2 border-t border-hw-line bg-hw-surface-muted px-5 py-[11px] text-[11px] leading-snug font-medium text-hw-muted max-[700px]:px-3.5 max-[700px]:py-3">
      {mode === "result" ? (
        <span className="flex items-start gap-1.5">
          <ShieldCheck className="mt-px size-[13px] flex-none" aria-hidden="true" /> {sourceLine(response)}
        </span>
      ) : (
        <span className="flex items-center gap-1.5">
          <Eye className="size-[13px] flex-none" aria-hidden="true" /> <span id={consentId}>{ASK_ANSWERS_SHOWN_COPY}</span>
        </span>
      )}
      {mode !== "result" && (
        <span className="ml-auto flex items-center gap-1.5 whitespace-nowrap max-[700px]:hidden" aria-hidden="true">
          <span className={kbd}>↑↓</span> navigate
          <span className={`${kbd} ml-2`}><CornerDownLeft className="size-2.5" /></span> {mode === "typeahead" ? "open" : "select"}
          <span className={`${kbd} ml-2`}>esc</span> close
        </span>
      )}
      {import.meta.env.DEV && mode === "result" && response && (
        <AskResponseDetails interpreter={response.interpreter} />
      )}
    </div>
  );
}

export default AskFooter;
