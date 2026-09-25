import type {RoundDefinition} from "@/helpers/helpers";
import RoundRevealButton from "./RoundRevealButton";

interface FinalsRoundHeaderProps {
  finalsRound?: RoundDefinition;
  finalsRevealed: boolean;
  finalsCanReveal: boolean;
  finalsPrerequisite?: RoundDefinition;
  revealRound: (round: number) => void;
  hideRound: (round: number) => void;
  headingId: string;
  suppressRevealControls: boolean;
}

function FinalsRoundHeader({
  finalsRound,
  finalsRevealed,
  finalsCanReveal,
  finalsPrerequisite,
  revealRound,
  hideRound,
  headingId,
  suppressRevealControls,
}: FinalsRoundHeaderProps) {
  return (
    <div className={`mb-4 flex ${suppressRevealControls ? "" : "min-h-[76px]"} min-w-0 flex-col items-center gap-2 border-b-[3px] border-hw-accent-ink pb-3 text-center`}>
      <h2 id={headingId} className="text-[11px] leading-[1.35] font-black tracking-[.12em] text-hw-ink uppercase">{finalsRound?.label ?? "Finals"}</h2>
      {finalsRound && !suppressRevealControls ? (
        <RoundRevealButton
          label={finalsRound.label}
          isRevealed={finalsRevealed}
          canReveal={finalsCanReveal}
          prerequisiteLabel={finalsPrerequisite?.label}
          onReveal={() => revealRound(finalsRound.round)}
          onHide={() => hideRound(finalsRound.round)}
        />
      ) : null}
    </div>
  );
}

export default FinalsRoundHeader;
