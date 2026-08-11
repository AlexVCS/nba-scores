import {useEffect, useState} from "react";
import type {RefObject} from "react";
import {Link} from "react-router";

interface HardwoodFloatingBracketLinkProps {
  href: string;
  watchRef: RefObject<HTMLElement | null>;
}

function HardwoodFloatingBracketLink({href, watchRef}: HardwoodFloatingBracketLinkProps) {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const target = watchRef.current;
    if (!target) return;
    const observer = new IntersectionObserver(([entry]) => setIsVisible(!entry.isIntersecting));
    observer.observe(target);
    return () => observer.disconnect();
  }, [watchRef]);

  return (
    <Link
      className={`fixed bottom-[max(18px,env(safe-area-inset-bottom))] left-1/2 z-40 -translate-x-1/2 rounded-hw border border-hw-line bg-hw-surface/88 px-4 py-2.5 text-[10px] font-extrabold tracking-[.12em] text-hw-ink uppercase no-underline shadow-hw-small backdrop-blur-[10px] transition-[opacity,transform] duration-[180ms] [transition-timing-function:ease-out] hover:text-hw-accent-ink focus-visible:outline-3 focus-visible:outline-offset-3 focus-visible:outline-hw-accent motion-reduce:transition-none ${isVisible ? "translate-y-0 opacity-100" : "pointer-events-none translate-y-2 opacity-0 motion-reduce:translate-y-0"}`}
      to={href}
      aria-hidden={!isVisible}
      tabIndex={isVisible ? undefined : -1}
    >
      BRACKET
    </Link>
  );
}

export default HardwoodFloatingBracketLink;
