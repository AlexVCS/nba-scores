interface SkeletonBlockProps {
  className?: string;
}

function SkeletonBlock({className = ""}: SkeletonBlockProps) {
  return (
    <div
      className={`relative overflow-hidden rounded-lg bg-slate-200/80 dark:bg-white/10 ${className}`}
    >
      <div className="absolute inset-0 -translate-x-full animate-[pulse_1.8s_ease-in-out_infinite] bg-gradient-to-r from-transparent via-white/45 to-transparent dark:via-white/10" />
    </div>
  );
}

export default SkeletonBlock;
