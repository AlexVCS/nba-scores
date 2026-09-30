import {ArrowRight, Search} from "lucide-react";
import type {AskSuggestion} from "@/services/ask/types";
import {withoutSpoilers} from "./askSpoilers";
import {askCap} from "./askStyles";

interface AskSuggestionsProps {
  suggestions: AskSuggestion[];
  revealed: boolean;
  title: string;
  variant: "chips" | "list";
  onAsk: (question: string, options: {remember: boolean}) => void;
}

const CATEGORY_LABELS: Record<AskSuggestion["category"], string> = {
  games: "Games",
  stats: "Stats",
  series: "Series",
  postseason: "Postseason",
};

/** Standalone follow-up questions. Spoiler suggestions are dropped while hidden and never saved to recents. */
function AskSuggestions({suggestions, revealed, title, variant, onAsk}: AskSuggestionsProps) {
  const visible = withoutSpoilers(suggestions, revealed);
  if (visible.length === 0) return null;
  const titleId = `ask-suggestions-${variant}`;

  return (
    <section aria-labelledby={titleId}>
      <h3 id={titleId} className={`${askCap} mb-2.5`}>{title}</h3>
      {variant === "chips" ? (
        <div className="flex flex-wrap gap-1.5">
          {visible.map(suggestion => (
            <button
              key={suggestion.question}
              type="button"
              className="inline-flex min-h-9 cursor-pointer items-center gap-1.5 rounded-full border border-hw-line bg-hw-surface px-3 py-1.5 text-left text-xs leading-snug font-semibold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-hw-accent"
              onClick={() => onAsk(suggestion.question, {remember: !suggestion.spoiler})}
            >
              <Search className="size-3 flex-none" aria-hidden="true" /> {suggestion.question}
            </button>
          ))}
        </div>
      ) : (
        <ul className="overflow-hidden rounded-[12px] border border-hw-line">
          {visible.map(suggestion => (
            <li key={suggestion.question} className="border-t border-hw-line first:border-t-0">
              <button
                type="button"
                className="flex min-h-12 w-full cursor-pointer items-center gap-3 px-3.5 py-3 text-left focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-hw-accent"
                onClick={() => onAsk(suggestion.question, {remember: !suggestion.spoiler})}
              >
                <span className={`${askCap} w-[76px] flex-none`}>{CATEGORY_LABELS[suggestion.category]}</span>
                <span className="flex-1 text-[13px] leading-snug font-semibold">{suggestion.question}</span>
                <ArrowRight className="size-3.5 text-hw-muted" aria-hidden="true" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default AskSuggestions;
