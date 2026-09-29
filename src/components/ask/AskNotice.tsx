import {Hourglass, HelpCircle, RotateCcw, SearchX, TriangleAlert} from "lucide-react";
import type {AskNotice as AskNoticeData, AskOutcome} from "@/services/ask/types";
import {ASK_DIAGNOSTICS_NOTE} from "./askCopy";
import {askButton} from "./askStyles";

interface AskNoticeProps {
  outcome: AskOutcome;
  notice: AskNoticeData;
  onRetry: () => void;
}

function NoticeIcon({outcome}: {outcome: AskOutcome}) {
  const className = "size-5";
  if (outcome === "budget_exhausted") return <Hourglass className={className} aria-hidden="true" />;
  if (outcome === "unavailable") return <TriangleAlert className={className} aria-hidden="true" />;
  if (outcome === "not_found") return <SearchX className={className} aria-hidden="true" />;
  return <HelpCircle className={className} aria-hidden="true" />;
}

/** Unsupported, not found (incl. missing historical records), unavailable, and budget-exhausted outcomes. */
function AskNotice({outcome, notice, onRetry}: AskNoticeProps) {
  return (
    <div className="rounded-[12px] border border-hw-line bg-hw-surface px-4 py-[18px]" data-notice={notice.code}>
      <span className="grid size-10 place-items-center rounded-[10px] bg-hw-surface-muted text-hw-accent-ink">
        <NoticeIcon outcome={outcome} />
      </span>
      <h3 className="mt-3.5 text-[19px] leading-tight font-extrabold">{notice.title}</h3>
      <p className="mt-1.5 text-[13px] leading-normal text-hw-muted">{notice.message}</p>
      {notice.retryable && (
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button type="button" className={askButton} onClick={onRetry}>
            <RotateCcw className="size-[13px]" aria-hidden="true" /> Try again
          </button>
          {notice.retry_after_seconds && (
            <span className="text-xs text-hw-muted">
              Best after about {notice.retry_after_seconds < 90 ? `${notice.retry_after_seconds} seconds` : `${Math.round(notice.retry_after_seconds / 60)} minutes`}.
            </span>
          )}
        </div>
      )}
      {notice.diagnostics_recorded && <p className="mt-3.5 text-[11px] leading-[1.45] text-hw-muted">{ASK_DIAGNOSTICS_NOTE}</p>}
    </div>
  );
}

export default AskNotice;
