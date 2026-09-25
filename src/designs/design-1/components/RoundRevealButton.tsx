import {Eye, EyeOff, LockKeyhole} from "lucide-react";

interface RoundRevealButtonProps {
  label: string;
  isRevealed: boolean;
  canReveal: boolean;
  prerequisiteLabel?: string;
  onReveal: () => void;
  onHide: () => void;
}

function RoundRevealButton({
  label,
  isRevealed,
  canReveal,
  prerequisiteLabel,
  onReveal,
  onHide,
}: RoundRevealButtonProps) {
  const copy = isRevealed ? "Hide results" : "Reveal results";
  const accessibleCopy = isRevealed
    ? `Hide ${label} and later round results`
    : `Reveal ${label} results`;

  if (!canReveal && !isRevealed) {
    return (
      <span
        className="inline-flex min-h-11 items-center gap-2 px-1 text-[10px] font-extrabold tracking-[.08em] text-hw-court uppercase dark:text-hw-muted"
        title={prerequisiteLabel ? `Reveal ${prerequisiteLabel} first` : undefined}
        aria-label={`${label} locked${prerequisiteLabel ? ` until ${prerequisiteLabel} is revealed` : ""}`}
      >
        <LockKeyhole aria-hidden="true" size={14} strokeWidth={2.4} />
        Locked
      </span>
    );
  }

  const Icon = isRevealed ? EyeOff : Eye;
  return (
    <button
      type="button"
      onClick={isRevealed ? onHide : onReveal}
      className={`inline-flex min-h-11 max-w-full items-center justify-center gap-2 rounded-hw px-3 text-[10px] font-extrabold tracking-[.08em] whitespace-nowrap uppercase shadow-hw-small transition-[background-color,color,transform] duration-160 ease-out focus-visible:outline-3 focus-visible:outline-offset-3 focus-visible:outline-hw-accent-ink dark:focus-visible:outline-hw-accent active:translate-y-px disabled:cursor-not-allowed disabled:opacity-55 motion-reduce:transition-none ${isRevealed ? "bg-hw-surface text-hw-accent-ink dark:text-hw-accent" : "bg-hw-ink text-hw-surface dark:bg-hw-accent dark:text-hw-accent-contrast"}`}
      aria-pressed={isRevealed}
      aria-label={accessibleCopy}
    >
      <Icon aria-hidden="true" size={14} strokeWidth={2.4} />
      {copy}
    </button>
  );
}

export default RoundRevealButton;
