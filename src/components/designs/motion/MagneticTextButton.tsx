import {motion, useMotionValue, useReducedMotion, useTransform} from "framer-motion";
import type {MouseEvent, ReactNode} from "react";
import {Link} from "react-router";

const MotionLink = motion.create(Link);

interface MagneticTextButtonProps {
  children: ReactNode;
  to?: string;
  href?: string;
  className?: string;
}

function MagneticTextButton({
  children,
  to,
  href,
  className = "",
}: MagneticTextButtonProps) {
  const prefersReducedMotion = useReducedMotion();
  const pointerX = useMotionValue(0);
  const pointerY = useMotionValue(0);
  const x = useTransform(pointerX, [-60, 60], [-5, 5]);
  const y = useTransform(pointerY, [-30, 30], [-3, 3]);

  const handleMove = (event: MouseEvent<HTMLElement>) => {
    if (prefersReducedMotion) return;
    const rect = event.currentTarget.getBoundingClientRect();
    pointerX.set(event.clientX - rect.left - rect.width / 2);
    pointerY.set(event.clientY - rect.top - rect.height / 2);
  };

  const handleLeave = () => {
    pointerX.set(0);
    pointerY.set(0);
  };

  const sharedClassName = `inline-flex items-center justify-center rounded-full border px-4 py-2 text-sm font-black uppercase tracking-[0.16em] transition-colors active:scale-[0.98] ${className}`;

  if (href) {
    return (
      <motion.a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className={sharedClassName}
        style={prefersReducedMotion ? undefined : {x, y}}
        onMouseMove={handleMove}
        onMouseLeave={handleLeave}
      >
        {children}
      </motion.a>
    );
  }

  return (
    <MotionLink
      to={to ?? "#"}
      className={sharedClassName}
      style={prefersReducedMotion ? undefined : {x, y}}
      onMouseMove={handleMove}
      onMouseLeave={handleLeave}
    >
      {children}
    </MotionLink>
  );
}

export default MagneticTextButton;
