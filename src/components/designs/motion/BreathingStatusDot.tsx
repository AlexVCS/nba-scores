import {memo} from "react";
import {motion, useReducedMotion} from "framer-motion";

interface BreathingStatusDotProps {
  tone?: "live" | "final" | "scheduled";
}

const toneClasses = {
  live: "bg-rose-500",
  final: "bg-emerald-500",
  scheduled: "bg-slate-400",
};

function BreathingStatusDot({tone = "scheduled"}: BreathingStatusDotProps) {
  const prefersReducedMotion = useReducedMotion();

  return (
    <span className="relative inline-flex h-3 w-3 items-center justify-center">
      {!prefersReducedMotion && (
        <motion.span
          className={`absolute h-3 w-3 rounded-full ${toneClasses[tone]} opacity-35`}
          animate={{scale: [1, 1.8, 1], opacity: [0.35, 0, 0.35]}}
          transition={{
            duration: 2.4,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        />
      )}
      <span className={`relative h-2.5 w-2.5 rounded-full ${toneClasses[tone]}`} />
    </span>
  );
}

export default memo(BreathingStatusDot);
