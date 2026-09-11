import { useEffect, useId, useRef, useState } from "react";
import type { FormEvent } from "react";
import { useLocation } from "react-router";
import { Search, X } from "lucide-react";
import type { AskResponse } from "@/helpers/ask";
import { askQuestion } from "@/services/nbaService";
import { designPath, detectDesignId } from "@/designs/designRoutes";
import AskAnswerCard from "./AskAnswerCard";
import { ASK_ROOT, ASK_BUTTON, ASK_EXAMPLE, ASK_INTERPRETATION, ASK_INTERPRETATION_CHIP, ASK_NOTICE, ASK_PANEL, ASK_PULSE } from "./askStyles";

interface AskSearchProps {
  className?: string;
}

const EXAMPLE_QUESTIONS = [
  {
    label: "Tatum, G5 of the 2024 Finals",
    question: "How many points did Tatum score in game 5 of the 2024 Finals?",
  },
  {
    label: "Thunder on Jan 2, 2024",
    question: "Show the Thunder game on January 2, 2024.",
  },
  { label: "2023 NBA Finals", question: "Who won the 2023 NBA Finals?" },
  {
    label: "Thunder's 2024 playoffs",
    question: "Summarize the Thunder's 2024 playoffs.",
  },
];

const STATUS_TEXT = {
  ok: "Search results",
  unsupported:
    "This search isn't supported yet. Try a game, boxscore statistic, playoff series, or postseason summary.",
  needs_clarification:
    "Add a team, a date, or a playoff year so we can find the right result.",
  not_found:
    "No matching records were found. Try another date or a more specific question.",
  unavailable:
    "Basketball data is unavailable right now. Please try again shortly.",
};

function AskSearch({ className = "" }: AskSearchProps) {
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const { pathname } = useLocation();
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<AskResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const request = useRef<AbortController | null>(null);
  const [resultVersion, setResultVersion] = useState(0);
  const makePath = (path: string) =>
    /^\/(original|design-1)(?:\/|$)/.test(pathname)
      ? designPath(detectDesignId(pathname), path)
      : path;

  useEffect(() => () => request.current?.abort(), []);

  async function runSearch(value: string) {
    const cleaned = value.trim();
    if (!cleaned) return;
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    setLoading(true);
    setError("");
    setResult(null);
    setResultVersion((version) => version + 1);
    try {
      const response = await askQuestion(cleaned, controller.signal);
      if (!controller.signal.aborted) setResult(response);
    } catch (caught) {
      if (!controller.signal.aborted)
        setError(
          caught instanceof Error
            ? caught.message
            : "Search failed. Please try again.",
        );
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void runSearch(question);
  }

  function clearSearch() {
    request.current?.abort();
    setQuestion("");
    setLoading(false);
    setResult(null);
    setError("");
    inputRef.current?.focus();
  }

  function chooseExample(example: (typeof EXAMPLE_QUESTIONS)[number]) {
    setQuestion(example.question);
    inputRef.current?.focus();
    void runSearch(example.question);
  }

  const hasFeedback = loading || Boolean(error) || Boolean(result);
  const notice =
    result && result.status !== "ok"
      ? result.message || STATUS_TEXT[result.status]
      : error;

  return (
    <section className={`${ASK_ROOT} ${className}`}>
      <div className="grid gap-4">
        <form onSubmit={submit} role="search" aria-label="Basketball search">
          <label className="sr-only" htmlFor={inputId}>
            Ask about NBA games and statistics
          </label>
          <div className="relative grid grid-cols-[auto_1fr] items-center @[600px]:flex @[600px]:overflow-hidden @[600px]:rounded-[10px] @[600px]:border @[600px]:border-[var(--ask-line)] @[600px]:bg-[var(--ask-surface)] @[600px]:shadow-[var(--hw-shadow-small,0_5px_14px_rgb(43_29_6/14%))] has-[input:focus-visible]:border-[var(--ask-muted)]">
            <Search className="z-1 ml-4 shrink-0 self-center [grid-area:1/1] text-[var(--ask-muted)]" size={19} aria-hidden="true" />
            <input
              className="min-h-[54px] min-w-0 flex-1 rounded-[10px] border border-[var(--ask-line)] bg-[var(--ask-surface)] px-12 py-[.8rem] text-[15px] text-[var(--ask-ink)] shadow-[var(--hw-shadow-small,0_5px_14px_rgb(43_29_6/14%))] outline-0 [grid-area:1/1/2/3] placeholder:text-[var(--ask-muted)] placeholder:opacity-100 focus-visible:border-[var(--ask-muted)] [&::-webkit-search-cancel-button]:hidden [&::-webkit-search-cancel-button]:appearance-none @[600px]:rounded-none @[600px]:border-0 @[600px]:bg-transparent @[600px]:px-3 @[600px]:shadow-none"
              id={inputId}
              ref={inputRef}
              type="search"
              value={question}
              onChange={(event) => {
                const value = event.target.value;
                setQuestion(value);
                if (!value) {
                  request.current?.abort();
                  setLoading(false);
                  setResult(null);
                  setError("");
                }
              }}
              maxLength={300}
              required
              autoComplete="off"
              placeholder="Ask about a game, a stat, or a playoff series…"
            />
            {question && (
              <button type="button" className={`${ASK_BUTTON} z-1 mr-[5px] grid h-11 w-11 shrink-0 basis-11 place-items-center justify-self-end rounded-[7px] border-0 bg-transparent p-0 text-[var(--ask-ink)] [grid-area:1/2] hover:bg-[var(--ask-muted-surface)] @[600px]:mr-0`} aria-label="Clear search" onClick={clearSearch}>
                <X size={18} aria-hidden="true" />
              </button>
            )}
            <button
              type="submit"
              className={`${ASK_BUTTON} col-span-2 mt-2 min-h-12 self-stretch rounded-[7px] border-0 bg-[var(--ask-accent)] px-[1.35rem] py-[.65rem] text-[11px] tracking-[.1em] text-[#131210] uppercase transition-[filter] duration-160 ease-out enabled:hover:brightness-[.94] disabled:cursor-default disabled:opacity-50 motion-reduce:transition-none @[600px]:m-[5px] @[600px]:min-h-11`}
              disabled={loading || !question.trim()}
            >
              {loading ? "Searching..." : "Search"}
            </button>
          </div>
          {!hasFeedback && (
            <div className="mt-[.65rem] flex items-start gap-2 overflow-hidden text-[var(--ask-muted)] @[600px]:items-center">
              <p className="shrink-0 text-[11px] font-extrabold tracking-[.12em] uppercase">Try:</p>
              <ul className="m-0 flex list-none flex-nowrap gap-[.4rem] overflow-x-auto p-0 pb-[.35rem] @[600px]:flex-wrap @[600px]:overflow-visible @[600px]:pb-0" aria-label="Example questions">
                {EXAMPLE_QUESTIONS.map((example) => (
                  <li className="shrink-0" key={example.question}>
                    <button
                      className={ASK_EXAMPLE}
                      type="button"
                      onClick={() => chooseExample(example)}
                    >
                      {example.label}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </form>
        <div role="status" aria-live="polite" className="sr-only">
          {loading
            ? "Searching basketball records"
            : result
              ? result.message || STATUS_TEXT[result.status]
              : ""}
        </div>
        {loading && (
          <div className={`${ASK_PANEL} grid min-h-[190px] gap-[.8rem] p-6`} aria-hidden="true">
            <span className={`${ASK_PULSE} h-[22px] w-[min(75%,520px)]`} />
            <span className={`${ASK_PULSE} h-3 w-[min(45%,320px)]`} />
            <span className={`${ASK_PULSE} h-16 w-full self-end`} />
          </div>
        )}
        {notice && (
          <div role={error ? "alert" : "status"} className={ASK_NOTICE}>
            <p>{notice}</p>
            {result?.status === "needs_clarification" && (
              <p className={ASK_INTERPRETATION}>
                <span>Interpreted as:</span>{" "}
                {(result.interpretation?.length
                  ? result.interpretation
                  : ["[add the missing detail]"]
                ).map((part) => (
                  <span
                    className={`${ASK_INTERPRETATION_CHIP} ${part.startsWith("[") ? "rounded border border-dashed border-[var(--ask-muted)] px-[.35rem] py-[.1rem]" : ""}`}
                    key={part}
                  >
                    {part}
                  </span>
                ))}
              </p>
            )}
            <div className="mt-4 flex flex-wrap gap-[.45rem]">
              {EXAMPLE_QUESTIONS.slice(0, 2).map((example) => (
                <button
                  type="button"
                  className={ASK_EXAMPLE}
                  key={example.question}
                  onClick={() => chooseExample(example)}
                >
                  {example.label}
                </button>
              ))}
            </div>
          </div>
        )}
        {result && result.items.length > 0 && (
          <ul
            className="m-0 grid list-none gap-4 p-0"
            aria-label="Search results"
            key={resultVersion}
          >
            {result.items.map((item, index) => (
              <AskAnswerCard
                key={index}
                item={item}
                interpretation={result.interpretation ?? []}
                makePath={makePath}
              />
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}

export default AskSearch;
