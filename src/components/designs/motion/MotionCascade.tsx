import {motion, useReducedMotion, type Variants} from "framer-motion";
import type {ReactNode} from "react";

interface MotionCascadeProps {
  children: ReactNode;
  className?: string;
}

function MotionCascade({children, className = ""}: MotionCascadeProps) {
  const prefersReducedMotion = useReducedMotion();

  const parentVariants: Variants = prefersReducedMotion
    ? {}
    : {
        hidden: {opacity: 1},
        visible: {
          opacity: 1,
          transition: {
            staggerChildren: 0.08,
            delayChildren: 0.05,
          },
        },
      };

  return (
    <motion.div
      className={className}
      variants={parentVariants}
      initial="hidden"
      animate="visible"
    >
      {children}
    </motion.div>
  );
}

export default MotionCascade;
