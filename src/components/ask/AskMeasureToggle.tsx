import type {AskAggregation} from "@/services/ask/types";

interface AskMeasureToggleProps {
  measure: AskAggregation;
  onChange: (measure: AskAggregation) => void;
  /** What the buttons switch, for screen readers: "Kevin Durant 2015-16 statistics". */
  subject: string;
}

const OPTIONS: {id: AskAggregation; label: string}[] = [
  {id: "per_game", label: "Per game"},
  {id: "total", label: "Totals"},
];

// Segmented control in the Hardwood style of the boxscore facet switch: a labelled group of
// toggle buttons, so each button announces whether it is pressed.
function AskMeasureToggle({measure, onChange, subject}: AskMeasureToggleProps) {
  return (
    <div className="inline-flex gap-[3px] rounded-[13px] border border-hw-line bg-hw-surface p-[3px]" role="group"
         aria-label={`Show ${subject} per game or as totals`}>
      {OPTIONS.map(option => (
        <button
          key={option.id}
          type="button"
          className="min-h-11 cursor-pointer rounded-hw border-0 bg-transparent px-3 text-[10px] font-extrabold tracking-[.1em] text-hw-muted uppercase transition-colors duration-[160ms] aria-pressed:bg-hw-accent aria-pressed:text-hw-accent-contrast focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-hw-accent-ink motion-reduce:transition-none [@media(pointer:fine)]:min-h-[34px]"
          aria-pressed={option.id === measure}
          onClick={() => onChange(option.id)}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

export default AskMeasureToggle;
