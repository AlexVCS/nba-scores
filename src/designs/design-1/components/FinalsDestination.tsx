import {LockKeyhole} from "lucide-react";
import type {ReactNode} from "react";

interface FinalsDestinationProps {
  isLocked: boolean;
  prerequisiteLabel?: string;
  children?: ReactNode;
  className?: string;
}

function FinalsDestination({isLocked, prerequisiteLabel, children, className = ""}: FinalsDestinationProps) {
  return (
    <section
      className={`relative flex ${isLocked ? "min-h-44" : ""} items-center justify-center text-center text-hw-ink ${className}`}
      aria-label="NBA Finals"
    >
      {isLocked ? (
        <div className="flex max-w-48 flex-col items-center gap-2.5 text-hw-muted">
          <LockKeyhole aria-hidden="true" size={22} strokeWidth={2.2} />
          <h2 className="text-sm font-black tracking-[.1em] text-hw-ink uppercase">Finals locked</h2>
          <p className="text-xs leading-5">
            {prerequisiteLabel ? `Reveal ${prerequisiteLabel} to unlock the Finals.` : "Reveal earlier rounds to unlock the Finals."}
          </p>
        </div>
      ) : (
        <div className="w-full">{children}</div>
      )}
    </section>
  );
}

export default FinalsDestination;
