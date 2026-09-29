import {useEffect, useState} from "react";
import {Search} from "lucide-react";
import AskDialog from "./AskDialog";
import {ASK_PLACEHOLDER} from "./askCopy";
import {isApplePlatform, isAskShortcut, isEditableElement} from "./askKeyboard";

interface AskEntryProps {
  variant?: "hardwood" | "original";
}

const hardwood = {
  desktop: "flex min-h-11 w-[380px] max-w-full cursor-pointer items-center gap-2.5 rounded-hw border border-hw-line bg-hw-surface pr-2 pl-3.5 text-[13px] font-medium text-hw-muted shadow-hw-small hover:text-hw-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-hw-accent max-[700px]:hidden",
  mobile: "hidden min-h-11 cursor-pointer items-center gap-2 rounded-hw border border-hw-line bg-hw-surface px-3.5 text-[11px] font-extrabold tracking-[.1em] text-hw-ink uppercase shadow-hw-small focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-hw-accent max-[700px]:inline-flex",
  kbd: "inline-flex items-center rounded-md border border-hw-line bg-hw-surface-muted px-[7px] py-[5px] text-[10px] leading-none font-bold tracking-[.06em] uppercase",
};

const original = {
  desktop: "flex min-h-11 w-[380px] max-w-full cursor-pointer items-center gap-2.5 rounded-lg border border-slate-300 bg-white pr-2 pl-3.5 text-[13px] text-slate-500 hover:text-slate-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 max-[700px]:hidden dark:border-neutral-700 dark:bg-neutral-900 dark:text-neutral-400 dark:hover:text-neutral-100",
  mobile: "hidden min-h-11 cursor-pointer items-center gap-2 rounded-lg border border-slate-300 bg-white px-3.5 text-xs font-bold tracking-[.08em] text-slate-900 uppercase focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 max-[700px]:inline-flex dark:border-neutral-700 dark:bg-neutral-900 dark:text-neutral-100",
  kbd: "inline-flex items-center rounded-md border border-slate-300 bg-slate-100 px-[7px] py-[5px] text-[10px] leading-none font-bold uppercase dark:border-neutral-700 dark:bg-neutral-800",
};

/** Header entry point for Ask: a search-field button on desktop, an "Ask" button on phones, and Cmd/Ctrl+K. */
function AskEntry({variant = "hardwood"}: AskEntryProps) {
  const [isOpen, setIsOpen] = useState(false);
  const styles = variant === "hardwood" ? hardwood : original;
  const shortcutLabel = isApplePlatform() ? "⌘ K" : "Ctrl K";

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.defaultPrevented) return;
      if (isAskShortcut(event)) {
        event.preventDefault();
        setIsOpen(true);
      } else if (event.key === "/" && !event.metaKey && !event.ctrlKey && !event.altKey && !isEditableElement(event.target)) {
        event.preventDefault();
        setIsOpen(true);
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  return (
    <>
      <button
        type="button"
        className={styles.desktop}
        aria-haspopup="dialog"
        aria-keyshortcuts={isApplePlatform() ? "Meta+K /" : "Control+K /"}
        onClick={() => setIsOpen(true)}
      >
        <Search className="size-4 flex-none" aria-hidden="true" />
        <span className="flex-1 truncate text-left">{ASK_PLACEHOLDER}</span>
        <kbd className={styles.kbd} aria-hidden="true">{shortcutLabel}</kbd>
      </button>
      <button type="button" className={styles.mobile} aria-haspopup="dialog" onClick={() => setIsOpen(true)}>
        <Search className="size-4" aria-hidden="true" /> Ask
      </button>
      <AskDialog isOpen={isOpen} onOpenChange={setIsOpen} />
    </>
  );
}

export default AskEntry;
