import MagneticTextButton from "@/components/designs/motion/MagneticTextButton";

interface DesignEmptyStateProps {
  title: string;
  message: string;
  actionTo?: string;
  actionLabel?: string;
  className?: string;
}

function DesignEmptyState({
  title,
  message,
  actionTo,
  actionLabel,
  className = "",
}: DesignEmptyStateProps) {
  return (
    <section
      className={`rounded-[2rem] border border-dashed border-slate-300 bg-white/70 p-8 text-left shadow-[inset_0_1px_0_rgba(255,255,255,0.55)] dark:border-white/15 dark:bg-slate-950/45 ${className}`}
    >
      <div className="mb-6 h-1 w-24 rounded-full bg-slate-400 dark:bg-slate-500" />
      <h2 className="text-2xl font-black tracking-tight">{title}</h2>
      <p className="mt-2 max-w-[65ch] text-base leading-relaxed text-slate-600 dark:text-slate-300">
        {message}
      </p>
      {actionTo && actionLabel && (
        <div className="mt-5">
          <MagneticTextButton
            to={actionTo}
            className="border-slate-300 bg-white/70 text-slate-800 hover:border-slate-500 dark:border-white/15 dark:bg-white/10 dark:text-slate-100"
          >
            {actionLabel}
          </MagneticTextButton>
        </div>
      )}
    </section>
  );
}

export default DesignEmptyState;
