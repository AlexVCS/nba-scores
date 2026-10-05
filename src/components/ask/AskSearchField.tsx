import type {ChangeEvent, KeyboardEvent, Ref} from "react";
import {Search, XCircle} from "lucide-react";
import {ASK_PLACEHOLDER} from "./askCopy";

interface AskSearchFieldProps {
  inputRef: Ref<HTMLInputElement>;
  value: string;
  onChange: (value: string) => void;
  onKeyDown: (event: KeyboardEvent<HTMLInputElement>) => void;
  onClear: () => void;
  onClose: () => void;
  listboxId: string;
  isExpanded: boolean;
  activeDescendant?: string;
}

function AskSearchField({inputRef, value, onChange, onKeyDown, onClear, onClose, listboxId, isExpanded, activeDescendant}: AskSearchFieldProps) {
  return (
    <div className="flex flex-none items-center gap-3 border-b-4 border-hw-accent px-5 py-4 max-[700px]:px-3.5 max-[700px]:pt-3 max-[700px]:pb-2.5">
      <div className="flex min-h-10 min-w-0 flex-1 items-center gap-3 max-[700px]:gap-2 max-[700px]:rounded-[10px] max-[700px]:border max-[700px]:border-hw-line max-[700px]:bg-hw-surface-muted max-[700px]:px-2.5">
        <Search className="size-5 flex-none text-hw-accent-ink max-[700px]:size-[17px] max-[700px]:text-hw-muted" aria-hidden="true" />
        <input
          ref={inputRef}
          type="text"
          role="combobox"
          aria-label="Ask a question"
          aria-autocomplete="list"
          aria-expanded={isExpanded}
          aria-controls={isExpanded ? listboxId : undefined}
          aria-activedescendant={activeDescendant}
          autoComplete="off"
          autoCorrect="off"
          spellCheck={false}
          enterKeyHint="search"
          maxLength={200}
          placeholder={ASK_PLACEHOLDER}
          className="min-w-0 flex-1 bg-transparent text-[17px] leading-snug font-semibold text-hw-ink caret-hw-accent-ink outline-none placeholder:font-medium placeholder:text-hw-muted max-[700px]:text-base"
          value={value}
          onChange={(event: ChangeEvent<HTMLInputElement>) => onChange(event.target.value)}
          onKeyDown={onKeyDown}
        />
        {value && (
          <button
            type="button"
            className="-mr-1 grid size-9 flex-none cursor-pointer place-items-center rounded-full text-hw-muted hover:text-hw-ink focus-visible:outline-2 focus-visible:outline-hw-accent"
            aria-label="Clear question"
            onClick={onClear}
          >
            <XCircle className="size-[17px]" aria-hidden="true" />
          </button>
        )}
      </div>
      <button
        type="button"
        className="inline-flex cursor-pointer items-center rounded-md border border-hw-line bg-hw-surface-muted px-[7px] py-[5px] text-[10px] leading-none font-bold tracking-[.06em] text-hw-muted uppercase focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-hw-accent max-[700px]:hidden"
        aria-label="Close Ask"
        onClick={onClose}
      >
        esc
      </button>
      <button
        type="button"
        className="hidden min-h-11 cursor-pointer px-1 text-sm font-bold text-hw-accent-ink focus-visible:outline-2 focus-visible:outline-hw-accent max-[700px]:inline-flex max-[700px]:items-center"
        onClick={onClose}
      >
        Cancel
      </button>
    </div>
  );
}

export default AskSearchField;
