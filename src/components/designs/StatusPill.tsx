import type {ReactNode} from "react";

interface StatusPillProps {
  children: ReactNode;
  tone?: "neutral" | "live" | "final" | "scheduled" | "warning";
  className?: string;
}

const toneClasses = {
  neutral:
    "border-slate-300/70 bg-white/70 text-slate-700 dark:border-white/10 dark:bg-white/8 dark:text-slate-200",
  live:
    "border-red-400/70 bg-red-50 text-red-700 dark:border-red-400/50 dark:bg-red-500/15 dark:text-red-200",
  final:
    "border-emerald-500/50 bg-emerald-50 text-emerald-800 dark:border-emerald-400/40 dark:bg-emerald-500/15 dark:text-emerald-200",
  scheduled:
    "border-sky-400/50 bg-sky-50 text-sky-800 dark:border-sky-400/40 dark:bg-sky-500/15 dark:text-sky-200",
  warning:
    "border-amber-400/60 bg-amber-50 text-amber-800 dark:border-amber-400/50 dark:bg-amber-500/15 dark:text-amber-200",
};

function StatusPill({
  children,
  tone = "neutral",
  className = "",
}: StatusPillProps) {
  return (
    <span
      className={`inline-flex min-h-7 items-center rounded-full border px-3 py-1 text-xs font-bold uppercase tracking-[0.18em] ${toneClasses[tone]} ${className}`}
    >
      {children}
    </span>
  );
}

export default StatusPill;
