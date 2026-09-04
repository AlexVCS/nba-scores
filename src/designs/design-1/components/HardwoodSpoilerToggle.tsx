import {Eye, EyeOff} from "lucide-react";

interface HardwoodSpoilerToggleProps {
  isRevealed: boolean;
  onChange: (value: boolean) => void;
  label?: string;
}

function HardwoodSpoilerToggle({isRevealed, onChange, label = "scores"}: HardwoodSpoilerToggleProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={isRevealed}
      className="inline-flex min-h-[42px] cursor-pointer items-center gap-2.5 rounded-hw border-0 bg-hw-accent py-[7px] pr-3.5 pl-2 text-[11px] font-extrabold tracking-[.08em] text-hw-accent-contrast uppercase"
      onClick={() => onChange(!isRevealed)}
    >
      <span className="grid size-[27px] place-items-center rounded-[7px] bg-hw-accent-contrast text-hw-accent">
        {isRevealed ? <EyeOff className="w-[15px]" aria-hidden="true" /> : <Eye className="w-[15px]" aria-hidden="true" />}
      </span>
      <span>{isRevealed ? `Hide ${label}` : `Reveal ${label}`}</span>
    </button>
  );
}

export default HardwoodSpoilerToggle;
