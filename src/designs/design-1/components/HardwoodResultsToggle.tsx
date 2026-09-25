import type {Ref} from "react";
import {Eye, EyeOff} from "lucide-react";
import {Button, Tooltip, TooltipTrigger} from "react-aria-components";
import {useResultsVisibility} from "@/hooks/useResultsVisibility";

interface HardwoodResultsToggleProps {
  wording: "Scorez" | "Results";
  controlRef: Ref<HTMLButtonElement>;
  hintId?: string;
}

function HardwoodResultsToggle({wording, controlRef, hintId}: HardwoodResultsToggleProps) {
  const {showAllResults, toggleShowAllResults, dismissSpoilerHint} = useResultsVisibility();
  const label = `${wording} ${showAllResults ? "shown" : "hidden"}`;
  const action = showAllResults ? "Hide all results" : "Show all results";

  return (
    <TooltipTrigger delay={350} closeDelay={100} isDisabled={Boolean(hintId)}>
      <Button
        ref={controlRef}
        type="button"
        aria-label={`${label}. ${action}`}
        aria-describedby={hintId}
        aria-pressed={showAllResults}
        onPress={() => {
          dismissSpoilerHint();
          toggleShowAllResults();
        }}
        className={`inline-flex min-h-11 cursor-pointer [@media(pointer:fine)]:min-h-9 items-center justify-center rounded-[7px] border text-xs font-semibold transition-[background-color,border-color,color,transform] duration-160 ease-out data-focus-visible:outline-2 data-focus-visible:outline-offset-2 data-focus-visible:outline-hw-accent data-pressed:translate-y-px motion-reduce:transition-none ${hintId ? "gap-2 px-3 py-2" : "size-11 [@media(pointer:fine)]:size-9"} ${showAllResults
          ? "border-hw-accent bg-hw-accent text-hw-accent-contrast shadow-hw-small"
          : "border-transparent bg-transparent text-hw-muted data-hovered:bg-hw-surface-muted data-hovered:text-hw-accent-ink dark:data-hovered:text-hw-accent"
        }`}
      >
        {showAllResults
          ? <Eye className="size-[18px] shrink-0 [@media(pointer:fine)]:size-4" aria-hidden="true" />
          : <EyeOff className="size-[18px] shrink-0 [@media(pointer:fine)]:size-4" aria-hidden="true" />}
        {hintId && <span>{label}</span>}
      </Button>
      <Tooltip
        placement="bottom end"
        offset={8}
        className="z-50 max-w-64 rounded-[7px] bg-[#131210] px-2.5 py-2 font-hw-display text-[10px] leading-[1.35] font-bold tracking-[.04em] text-[#fffcf3] shadow-[0_8px_22px_rgb(0_0_0/35%)] dark:bg-[#fffcf3] dark:text-[#131210]"
      >
        {action}
      </Tooltip>
    </TooltipTrigger>
  );
}

export default HardwoodResultsToggle;
