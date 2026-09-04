import {Eye, EyeOff} from "lucide-react";
import {Button, Tooltip, TooltipTrigger} from "react-aria-components";
import {useResultsVisibility} from "@/hooks/useResultsVisibility";

function HardwoodResultsToggle() {
  const {showAllResults, toggleShowAllResults} = useResultsVisibility();
  const tooltip = showAllResults
    ? "All results shown. Turn on spoiler protection"
    : "Spoilers hidden. Show all results";

  return (
    <TooltipTrigger delay={350} closeDelay={100}>
      <Button
        type="button"
        aria-label="Show all results"
        aria-pressed={showAllResults}
        onPress={toggleShowAllResults}
        className={`inline-flex size-11 cursor-pointer items-center justify-center rounded-[7px] border transition-[background-color,border-color,color,transform] duration-160 ease-out data-focus-visible:outline-2 data-focus-visible:outline-offset-2 data-focus-visible:outline-hw-accent data-pressed:translate-y-px motion-reduce:transition-none ${showAllResults
          ? "border-hw-accent bg-hw-accent text-hw-accent-contrast shadow-hw-small"
          : "border-transparent bg-transparent text-hw-muted data-hovered:bg-hw-surface-muted data-hovered:text-hw-accent-ink dark:data-hovered:text-hw-accent"
        }`}
      >
        {showAllResults
          ? <Eye className="size-[19px]" aria-hidden="true" />
          : <EyeOff className="size-[19px]" aria-hidden="true" />}
      </Button>
      <Tooltip
        placement="bottom end"
        offset={8}
        className="z-50 max-w-64 rounded-[7px] bg-[#131210] px-2.5 py-2 font-hw-display text-[10px] leading-[1.35] font-bold tracking-[.04em] text-[#fffcf3] shadow-[0_8px_22px_rgb(0_0_0/35%)] dark:bg-[#fffcf3] dark:text-[#131210]"
      >
        {tooltip}
      </Tooltip>
    </TooltipTrigger>
  );
}

export default HardwoodResultsToggle;
