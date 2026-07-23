import {Eye, EyeOff} from "lucide-react";

interface SpoilerToggleProps {
  isRevealed: boolean;
  onChange: (value: boolean) => void;
  label?: string;
}

function SpoilerToggle({isRevealed, onChange, label = "scores"}: SpoilerToggleProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={isRevealed}
      className="concept-spoiler-toggle"
      onClick={() => onChange(!isRevealed)}
    >
      <span className="concept-spoiler-toggle__icon">
        {isRevealed ? <EyeOff aria-hidden="true" /> : <Eye aria-hidden="true" />}
      </span>
      <span>{isRevealed ? `Hide ${label}` : `Reveal ${label}`}</span>
    </button>
  );
}

export default SpoilerToggle;
