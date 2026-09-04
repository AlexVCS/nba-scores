import {useLayoutEffect, useRef} from "react";

/** Measure both reveal states at their real column widths, before positioning tracks. */
export default function useDesktopBracketGeometry(dependency: unknown, rowSeparation = 2, enabled = true) {
  const bracketRef = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    const bracket = bracketRef.current;
    if (!enabled || !bracket) return;
    bracket.style.setProperty("--hw-bracket-row-separation", String(rowSeparation));
    const probes = Array.from(bracket.querySelectorAll<HTMLElement>(".hw-bracket-measure > *"));
    const measure = () => {
      let cardHeight = 98;
      let finalsHeight = 0;
      for (const probe of probes) {
        const height = probe.getBoundingClientRect().height;
        if (probe.parentElement?.hasAttribute("data-finals-measure")) {
          finalsHeight = Math.max(finalsHeight, height);
        } else {
          cardHeight = Math.max(cardHeight, height);
        }
      }
      bracket.style.setProperty("--hw-bracket-card-height", `${Math.ceil(cardHeight)}px`);
      bracket.style.setProperty("--hw-bracket-finals-height", `${Math.ceil(finalsHeight)}px`);
    };
    measure();
    if (typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(measure);
    probes.forEach(probe => observer.observe(probe));
    return () => observer.disconnect();
  }, [dependency, rowSeparation, enabled]);

  return bracketRef;
}
