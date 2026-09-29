import {useCallback, useEffect, useId, useMemo, useRef, useState, type KeyboardEvent, type MouseEvent} from "react";
import {useLocation, useNavigate} from "react-router";
import {format, isSameWeek} from "date-fns";
import {HelpCircle} from "lucide-react";
import {useAskSession} from "@/hooks/useAskSession";
import {useAskTypeahead} from "@/hooks/useAskTypeahead";
import {useResultsVisibility} from "@/hooks/useResultsVisibility";
import {addRecentSearch, clearRecentSearches, readRecentSearches, type AskRecentSearch} from "@/services/ask/recentSearches";
import type {AskClarificationOption, AskClientContext} from "@/services/ask/types";
import AskActionList from "./AskActionList";
import AskFooter from "./AskFooter";
import AskResultArea from "./AskResultArea";
import AskSearchField from "./AskSearchField";
import {ASK_DIAGNOSTICS_COPY, ASK_EXAMPLES, ASK_PROVIDER_COPY, ASK_RECENT_COPY, ASK_SCOPE_COPY} from "./askCopy";
import {askClientContext, withDesignPrefix} from "./askRouting";
import {askSession} from "./askSessionStore";
import {askOptionId, type AskAction, type AskActionGroup} from "./askTypeahead";

interface AskPanelProps {
  onClose: () => void;
}

function askedLabel(askedAt: string, now: Date): string {
  const date = new Date(askedAt);
  if (Number.isNaN(date.getTime())) return "";
  return `Asked ${isSameWeek(date, now) ? format(date, "EEE") : format(date, "MMM d")}`;
}

function emptyStateGroups(recents: AskRecentSearch[]): AskActionGroup[] {
  const now = new Date();
  const groups: AskActionGroup[] = [];
  if (recents.length > 0) {
    groups.push({
      id: "recent",
      label: "Recent",
      actions: recents.map((recent, index) => ({
        id: `recent-${index}`,
        kind: "recent",
        label: recent.question,
        meta: askedLabel(recent.askedAt, now),
        question: recent.question,
      })),
    });
  }
  groups.push({
    id: "examples",
    label: "Try asking",
    actions: ASK_EXAMPLES.map((example, index) => ({
      id: `example-${index}`,
      kind: "example",
      label: example.question,
      detail: example.label,
      question: example.question,
    })),
  });
  return groups;
}

function AskPanel({onClose}: AskPanelProps) {
  const session = useAskSession();
  const {showAllResults} = useResultsVisibility();
  const navigate = useNavigate();
  const location = useLocation();
  const inputRef = useRef<HTMLInputElement>(null);
  const listboxId = useId();
  const consentId = useId();
  const [recents, setRecents] = useState(readRecentSearches);
  const [activeId, setActiveId] = useState<string | null>(null);

  const query = session.query;
  const trimmed = query.trim();
  const mode = !trimmed
    ? "empty"
    : session.submission && session.status !== "idle" && trimmed === session.submission.question
      ? "result"
      : "typeahead";

  const typeahead = useAskTypeahead({query, resultsHidden: !showAllResults, enabled: mode === "typeahead"});
  const groups = useMemo(
    () => mode === "empty" ? emptyStateGroups(recents) : mode === "typeahead" ? typeahead.groups : [],
    [mode, recents, typeahead.groups],
  );
  const actions = useMemo(() => groups.flatMap(group => group.actions), [groups]);
  // Typing highlights the first row so Enter always runs what is visibly selected; the empty state waits for arrows.
  const active = actions.find(action => action.id === activeId) ?? (mode === "typeahead" ? actions[0] : undefined);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    if (!active) return;
    document.getElementById(askOptionId(listboxId, active.id))?.scrollIntoView?.({block: "nearest"});
  }, [active, listboxId]);

  const {pathname, search} = location;
  const ask = useCallback((question: string, {remember = true, resolution = null, context = askClientContext(pathname, search)}: {remember?: boolean; resolution?: string | null; context?: AskClientContext | null} = {}) => {
    const next = question.trim();
    if (!next) return;
    // Recent history keeps the question only, and never one taken from a spoiler-flagged suggestion.
    if (remember) setRecents(addRecentSearch(next));
    setActiveId(null);
    askSession.submit(next, {resolution, context});
  }, [pathname, search]);

  const chooseOption = useCallback((option: AskClarificationOption) => {
    ask(option.question, {remember: !option.spoiler, resolution: option.resolution, context: session.submission?.context ?? null});
  }, [ask, session.submission?.context]);

  const run = (action: AskAction) => {
    if (action.href) {
      navigate(withDesignPrefix(action.href, pathname));
      onClose();
    } else if (action.question) {
      ask(action.question, {remember: !action.spoiler});
    }
  };

  const editQuestion = useCallback(() => {
    inputRef.current?.focus();
    inputRef.current?.select();
  }, []);

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.nativeEvent.isComposing) return;
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      if (actions.length === 0) return;
      event.preventDefault();
      const index = active ? actions.indexOf(active) : -1;
      const step = event.key === "ArrowDown" ? 1 : -1;
      const nextIndex = index === -1
        ? (step === 1 ? 0 : actions.length - 1)
        : (index + step + actions.length) % actions.length;
      setActiveId(actions[nextIndex].id);
    } else if (event.key === "Enter") {
      event.preventDefault();
      if (active) run(active);
      else if (trimmed) ask(trimmed);
    }
  };

  // In-app links inside answers (boxscores, series, game cards) leave the dialog.
  const handleBodyClick = (event: MouseEvent<HTMLDivElement>) => {
    const anchor = (event.target as Element).closest("a");
    if (anchor && anchor.target !== "_blank") onClose();
  };

  const statusText = mode === "result"
    ? session.status === "loading" ? "Asking…"
      : session.status === "error" ? "Couldn’t reach Ask."
        : session.response?.outcome === "needs_clarification" ? "Ask needs you to choose an option."
          : session.response?.notice?.title ?? "Answer ready."
    : mode === "typeahead" ? `${actions.length} ${actions.length === 1 ? "suggestion" : "suggestions"} available.` : "";

  return (
    <>
      <AskSearchField
        inputRef={inputRef}
        value={query}
        onChange={value => {
          setActiveId(null);
          askSession.setQuery(value);
        }}
        onKeyDown={handleKeyDown}
        onClear={() => {
          setActiveId(null);
          askSession.setQuery("");
          inputRef.current?.focus();
        }}
        onClose={onClose}
        listboxId={listboxId}
        isExpanded={groups.length > 0}
        activeDescendant={active ? askOptionId(listboxId, active.id) : undefined}
        describedBy={mode === "result" ? undefined : consentId}
      />
      <span className="sr-only" role="status" aria-live="polite">{statusText}</span>
      <div
        className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-5 pt-[18px] pb-5 max-[700px]:px-3.5 max-[700px]:pt-3.5"
        onClick={handleBodyClick}
      >
        {mode === "result" ? (
          <AskResultArea
            session={session}
            resultsHidden={!showAllResults}
            onAsk={(question, {remember}) => ask(question, {remember})}
            onChooseOption={chooseOption}
            onRetry={askSession.retry}
            onEditQuestion={editQuestion}
          />
        ) : (
          <AskActionList
            listboxId={listboxId}
            label={mode === "empty" ? "Recent searches and examples" : "Suggestions"}
            groups={groups}
            activeId={active?.id ?? null}
            onActiveChange={setActiveId}
            onRun={run}
          />
        )}
        {mode === "empty" && (
          <div className="mx-3 mt-3.5 grid gap-2.5 border-t border-hw-line pt-3.5 text-[11px] leading-[1.45] font-medium text-hw-muted max-[700px]:mx-0">
            <p className="flex items-start gap-2">
              <HelpCircle className="mt-px size-3.5 flex-none" aria-hidden="true" />
              <span>{ASK_SCOPE_COPY}</span>
            </p>
            <p>{ASK_RECENT_COPY} {ASK_PROVIDER_COPY} {ASK_DIAGNOSTICS_COPY}</p>
            {recents.length > 0 && (
              <button
                type="button"
                className="min-h-8 w-fit cursor-pointer font-bold text-hw-accent-ink underline underline-offset-3 focus-visible:outline-2 focus-visible:outline-hw-accent"
                onClick={() => {
                  setRecents(clearRecentSearches());
                  setActiveId(null);
                  inputRef.current?.focus();
                }}
              >
                Clear recent searches
              </button>
            )}
          </div>
        )}
      </div>
      <AskFooter mode={mode} response={session.response} consentId={consentId} />
    </>
  );
}

export default AskPanel;
