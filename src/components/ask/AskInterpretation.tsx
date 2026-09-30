import type {AskInterpretation as AskInterpretationData} from "@/services/ask/types";
import AskHiddenValue from "./AskHiddenValue";
import {DETECTED_TYPE_LABELS, FIELD_LABELS, formatAskRange} from "./askFormat";
import {askCap} from "./askStyles";

interface AskInterpretationProps {
  interpretation: AskInterpretationData;
  revealed: boolean;
  omitProtected?: boolean;
  onEditQuestion: () => void;
}

const chip = "inline-flex min-h-[30px] items-center gap-[7px] rounded-lg border px-2.5 text-xs font-bold";
const chipLabel = "text-[9px] font-extrabold tracking-[.12em] not-italic uppercase";

function AskInterpretation({interpretation, revealed, omitProtected = false, onEditQuestion}: AskInterpretationProps) {
  const {items, detected_type: detectedType, dates, season} = interpretation;
  const visibleItems = omitProtected && !revealed ? items.filter(item => !item.spoiler) : items;
  const hasDateItem = visibleItems.some(item => item.field === "date" || item.field === "dates" || item.field === "game");
  const hasSeasonItem = visibleItems.some(item => item.field === "season" || item.field === "round" || item.field === "series");

  return (
    <section aria-label="How Ask read your question">
      <div className="mb-2 flex items-center gap-2.5">
        <span className={askCap}>Reading this as</span>
        {detectedType && (
          // The detected type is a description, not a filter: plain text with no control semantics.
          <span className="inline-flex min-h-[22px] items-center rounded-full bg-hw-accent px-[9px] text-[9px] font-extrabold tracking-[.12em] text-hw-accent-contrast uppercase">
            {DETECTED_TYPE_LABELS[detectedType]}
          </span>
        )}
      </div>
      <ul className="flex flex-wrap items-center gap-1.5">
        {visibleItems.map((item, index) => {
          const ambiguous = item.status === "ambiguous";
          // Inferred participants are spoilers: keep the field name, drop the value entirely.
          const hidden = item.spoiler && !revealed;
          return (
            <li key={`${item.field}-${index}`} className={`${chip} ${ambiguous ? "border-dashed border-hw-accent bg-transparent" : "border-hw-line bg-hw-surface-muted"}`}>
              <i className={`${chipLabel} ${ambiguous ? "text-hw-accent-ink" : "text-hw-muted"}`}>{FIELD_LABELS[item.field]}</i>
              {hidden ? <AskHiddenValue width={48} /> : (
                <>
                  {item.value}
                  {(item.detail || (ambiguous && item.match_count)) && (
                    <small className="text-[11px] font-medium text-hw-muted">
                      {item.detail ?? `${item.match_count} matches`}
                    </small>
                  )}
                </>
              )}
            </li>
          );
        })}
        {dates && !hasDateItem && (
          <li className={`${chip} border-hw-line bg-hw-surface-muted`}>
            <i className={`${chipLabel} text-hw-muted`}>Dates</i>
            {formatAskRange(dates.start, dates.end)}
            <small className="text-[11px] font-medium text-hw-muted">ET</small>
          </li>
        )}
        {season && !hasSeasonItem && !dates && (
          <li className={`${chip} border-hw-line bg-hw-surface-muted`}>
            <i className={`${chipLabel} text-hw-muted`}>Season</i>{season}
          </li>
        )}
      </ul>
      <button
        type="button"
        className="mt-2 min-h-8 cursor-pointer text-[11px] font-bold text-hw-accent-ink underline underline-offset-3 focus-visible:outline-2 focus-visible:outline-hw-accent"
        onClick={onEditQuestion}
      >
        Not right? Edit your question
      </button>
    </section>
  );
}

export default AskInterpretation;
