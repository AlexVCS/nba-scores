import {useEffect, useState} from "react";

/**
 * Height of the visible viewport while Ask is open on a phone. It shrinks when the on-screen keyboard
 * opens, so a sheet sized to it keeps its scrollable list above the keyboard.
 */
export function useAskViewportHeight(enabled: boolean): number | null {
  const [height, setHeight] = useState<number | null>(null);

  useEffect(() => {
    const viewport = window.visualViewport;
    if (!enabled || !viewport) return;
    const update = () => setHeight(Math.round(viewport.height));
    update();
    viewport.addEventListener("resize", update);
    viewport.addEventListener("scroll", update);
    return () => {
      viewport.removeEventListener("resize", update);
      viewport.removeEventListener("scroll", update);
      setHeight(null);
    };
  }, [enabled]);

  return enabled ? height : null;
}
