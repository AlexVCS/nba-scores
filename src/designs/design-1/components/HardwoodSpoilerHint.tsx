interface HardwoodSpoilerHintProps {
  id: string;
  wording: "Scorez" | "Results";
  onShowResults: () => void;
  onDismiss: () => void;
}

function HardwoodSpoilerHint({id, wording, onShowResults, onDismiss}: HardwoodSpoilerHintProps) {
  const buttonClass = "min-h-11 cursor-pointer rounded-[7px] px-3 py-2 text-xs font-semibold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-hw-accent";

  return (
    <section
      id={id}
      aria-labelledby={`${id}-heading`}
      onKeyDown={(event) => {
        if (event.key === "Escape") {
          event.stopPropagation();
          onDismiss();
        }
      }}
      className="relative rounded-hw bg-hw-surface p-4 text-hw-ink shadow-hw-card"
    >
      <span aria-hidden="true" className="absolute -top-1.5 right-12 size-3 rotate-45 bg-hw-surface" />
      <h2 id={`${id}-heading`} className="text-base leading-snug font-extrabold">{wording} start hidden</h2>
      <p className="mt-1.5 text-[13px] leading-relaxed text-hw-muted">
        Avoid spoilers while you browse. Use this button to show all results.
      </p>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <button type="button" onClick={onShowResults} className={`${buttonClass} bg-hw-ink text-hw-surface hover:bg-hw-muted`}>
          Show all results
        </button>
        <button type="button" onClick={onDismiss} className={`${buttonClass} hover:bg-hw-surface-muted`}>
          Got it
        </button>
      </div>
    </section>
  );
}

export default HardwoodSpoilerHint;
