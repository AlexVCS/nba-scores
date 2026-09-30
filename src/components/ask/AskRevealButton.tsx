import {Eye, EyeOff} from "lucide-react";
import {askButton, askInkButton, type AskRevealControls} from "./askStyles";

interface AskRevealButtonProps {
  group: string;
  controls: AskRevealControls;
  /** Names what is revealed without revealing it, e.g. "score" or "answer". */
  label: string;
  className?: string;
}

/** Local reveal for one group. Absent when the global preference already shows results. */
function AskRevealButton({group, controls, label, className = ""}: AskRevealButtonProps) {
  if (controls.showAllResults) return null;
  const revealed = controls.isRevealed(group);
  return revealed ? (
    <button type="button" className={`${askButton} ${className}`} onClick={() => controls.hide(group)}>
      <EyeOff className="size-[13px]" aria-hidden="true" /> Hide {label}
    </button>
  ) : (
    <button type="button" className={`${askInkButton} ${className}`} onClick={() => controls.reveal(group)}>
      <Eye className="size-[13px]" aria-hidden="true" /> Reveal {label}
    </button>
  );
}

export default AskRevealButton;
