import {LockKeyhole} from "lucide-react";

interface LockedSeriesSlotProps {
  roundLabel: string;
  prerequisiteLabel?: string;
  className?: string;
}

function LockedSeriesSlot({roundLabel, prerequisiteLabel, className = ""}: LockedSeriesSlotProps) {
  return (
    <div
      className={`flex min-h-[104px] items-center justify-center rounded-hw border border-dashed border-hw-line bg-hw-surface-muted px-4 py-5 text-center text-hw-muted shadow-hw-small ${className}`}
      aria-label={`${roundLabel} matchup locked${prerequisiteLabel ? ` until ${prerequisiteLabel} is revealed` : ""}`}
    >
      <div className="flex max-w-[18rem] flex-col items-center gap-2">
        <LockKeyhole aria-hidden="true" size={18} strokeWidth={2.2} />
        <p className="text-[11px] font-extrabold tracking-[.08em] uppercase">Matchup locked</p>
        {prerequisiteLabel ? (
          <p className="text-xs leading-5">Reveal {prerequisiteLabel} to see this matchup.</p>
        ) : null}
      </div>
    </div>
  );
}

export default LockedSeriesSlot;
