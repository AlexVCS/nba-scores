import {useEffect, useState} from "react";
import type {AskClarification as AskClarificationData, AskClarificationOption} from "@/services/ask/types";
import {isEditableElement} from "./askKeyboard";
import {withoutSpoilers} from "./askSpoilers";
import {askCap, askTricode} from "./askStyles";

interface AskClarificationProps {
  clarification: AskClarificationData;
  revealed: boolean;
  onChoose: (option: AskClarificationOption) => void;
  onEditQuestion: () => void;
}

function AskClarification({clarification, revealed, onChoose, onEditQuestion}: AskClarificationProps) {
  const [revealedClarification, setRevealedClarification] = useState<AskClarificationData | null>(null);
  const optionsRevealed = revealedClarification === clarification;
  const options = withoutSpoilers(clarification.options, revealed || optionsRevealed);
  const shortcutCount = Math.min(options.length, 9);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Digits belong to the search field while it is focused or being edited.
      if (event.defaultPrevented || event.metaKey || event.ctrlKey || event.altKey || event.isComposing) return;
      if (isEditableElement(event.target) || isEditableElement(document.activeElement)) return;
      if (!/^[1-9]$/.test(event.key)) return;
      const option = options[Number(event.key) - 1];
      if (!option) return;
      event.preventDefault();
      onChoose(option);
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [options, onChoose]);

  return (
    <section aria-labelledby="ask-clarify-title" className="grid gap-3.5">
      <div>
        <h3 id="ask-clarify-title" className="text-xl leading-tight font-extrabold">{clarification.prompt}</h3>
        {clarification.detail && <p className="mt-1 text-[13px] text-hw-muted">{clarification.detail}</p>}
      </div>
      {options.length > 0 && (
        <ul className="grid grid-cols-2 gap-2.5 max-[700px]:grid-cols-1">
          {options.map((option, index) => (
            <li key={option.id}>
              <button
                type="button"
                className="flex min-h-14 w-full cursor-pointer items-center gap-3 rounded-[12px] border border-hw-line bg-hw-surface p-3.5 text-left hover:border-hw-accent focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-hw-accent"
                aria-keyshortcuts={index < shortcutCount ? String(index + 1) : undefined}
                onClick={() => onChoose(option)}
              >
                {option.team && <span className={`${askTricode} h-10 min-w-12`}>{option.team.tricode}</span>}
                <span className="min-w-0 flex-1">
                  <span className="block text-sm leading-tight font-extrabold">
                    {option.label}
                    {option.sublabel && <span className="ml-1.5 text-[10px] font-bold text-hw-muted">{option.sublabel}</span>}
                  </span>
                  {option.detail && <span className={`${askCap} mt-1.5 block`}>{option.detail}</span>}
                </span>
                {index < shortcutCount && (
                  <kbd className="rounded-md border border-hw-line bg-hw-surface-muted px-[7px] py-[5px] text-[10px] font-bold text-hw-muted max-[700px]:hidden" aria-hidden="true">
                    {index + 1}
                  </kbd>
                )}
              </button>
            </li>
          ))}
        </ul>
      )}
      {!revealed && !optionsRevealed && clarification.options.some(option => option.spoiler) && (
        <button
          type="button"
          className="min-h-8 w-fit cursor-pointer font-bold text-hw-accent-ink underline underline-offset-3 focus-visible:outline-2 focus-visible:outline-hw-accent"
          onClick={() => setRevealedClarification(clarification)}
        >
          Show all options
        </button>
      )}
      {clarification.hint && <p className="text-[11px] leading-[1.45] text-hw-muted">{clarification.hint}</p>}
      <div className="flex flex-wrap items-center gap-3 text-[11px] text-hw-muted">
        <button
          type="button"
          className="min-h-8 cursor-pointer font-bold text-hw-accent-ink underline underline-offset-3 focus-visible:outline-2 focus-visible:outline-hw-accent"
          onClick={onEditQuestion}
        >
          Edit your question instead
        </button>
        {shortcutCount > 1 && (
          <span className="max-[700px]:hidden">Outside the search field, press 1–{shortcutCount} to pick.</span>
        )}
      </div>
    </section>
  );
}

export default AskClarification;
