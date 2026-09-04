import {useEffect, useState} from "react";
import {Link, useLocation} from "react-router";
import {Layers3, X} from "lucide-react";
import {DESIGN_DEFINITIONS, getDesignDefinition} from "./designRegistry";
import {buildDesignHref} from "./designRoutes";
import type {DesignId} from "./types";

interface DesignSwitcherProps {
  activeDesign: DesignId;
}

function DesignSwitcher({activeDesign}: DesignSwitcherProps) {
  const location = useLocation();
  const [isOpen, setIsOpen] = useState(false);
  const active = getDesignDefinition(activeDesign);

  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setIsOpen(false);
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen]);

  const choices = DESIGN_DEFINITIONS.map((design) => (
    <Link
      key={design.id}
      to={buildDesignHref(design.id, location)}
      aria-current={design.id === activeDesign ? "page" : undefined}
      aria-label={`View ${design.name} design`}
      title={design.name}
      className="design-switcher__choice flex min-h-9 items-center justify-center rounded-full text-inherit no-underline transition-[color,background,transform] duration-160 hover:scale-[1.07] aria-[current=page]:bg-[var(--switcher-accent)] aria-[current=page]:text-[#080808] max-[899px]:justify-start max-[899px]:gap-3 max-[899px]:py-2 max-[899px]:px-3 max-[899px]:border max-[899px]:border-white/15 max-[899px]:rounded-xl motion-reduce:transition-none"
      onClick={() => setIsOpen(false)}
    >
      <span className="design-switcher__number [font:800_13px/1_Archivo,sans-serif] max-[899px]:grid max-[899px]:size-[27px] max-[899px]:place-items-center max-[899px]:rounded-full max-[899px]:bg-white/10">{design.number ?? 0}</span>
      <span className="design-switcher__name hidden max-[899px]:block max-[899px]:[font:700_11px/1_Archivo,sans-serif]">{design.shortName}</span>
    </Link>
  ));

  return (
    <>
      <nav className="design-switcher design-switcher--desktop fixed z-100 right-3 top-1/2 w-12 py-2 px-[5px] -translate-y-1/2 border border-[color-mix(in_srgb,var(--switcher-fg)_22%,transparent)] rounded-full bg-[color-mix(in_srgb,var(--switcher-bg)_92%,transparent)] text-[var(--switcher-fg)] shadow-[0_16px_42px_rgb(0_0_0/25%)] backdrop-blur-[14px] max-[899px]:hidden" aria-label="Choose application design">
        <span className="design-switcher__eyebrow block pt-[5px] pb-[7px] text-center [font:700_8px/1_Archivo,sans-serif] tracking-[.16em] opacity-60">VIEW</span>
        {choices}
      </nav>

      <button
        type="button"
        className="design-switcher__mobile-trigger hidden max-[899px]:inline-flex fixed z-90 right-3.5 max-[700px]:right-[max(14px,env(safe-area-inset-right))] bottom-[max(14px,env(safe-area-inset-bottom))] max-w-[calc(100vw-28px)] min-h-11 items-center gap-2 px-3.5 border border-white/25 rounded-full bg-[var(--switcher-bg)] text-[var(--switcher-fg)] shadow-[0_12px_32px_rgb(0_0_0/30%)] [font:800_11px/1_Archivo,sans-serif] tracking-[.04em]"
        aria-haspopup="dialog"
        aria-expanded={isOpen}
        onClick={() => setIsOpen(true)}
      >
        <Layers3 aria-hidden="true" size={17} />
        {active.number === null ? "Original" : `Design ${active.number}`}
      </button>

      {isOpen && (
        <div className="design-switcher__backdrop fixed z-110 inset-0 flex items-end bg-black/55 backdrop-blur-[5px]" role="presentation" onMouseDown={() => setIsOpen(false)}>
          <section
            role="dialog"
            aria-modal="true"
            aria-label="Choose application design"
            className="design-switcher__sheet w-full pt-4.5 px-4 pb-[max(18px,env(safe-area-inset-bottom))] rounded-t-[22px] bg-[var(--switcher-bg)] text-[var(--switcher-fg)] shadow-[0_-18px_50px_rgb(0_0_0/35%)]"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <header className="flex items-center justify-between mb-3.5">
              <div>
                <span className="block mb-1 [font:700_9px/1_Archivo,sans-serif] tracking-[.16em] uppercase opacity-55">Compare concepts</span>
                <strong className="block [font:800_20px/1.1_Archivo,sans-serif]">{active.name}</strong>
              </div>
              <button className="grid size-[42px] place-items-center border border-white/20 rounded-full bg-transparent text-inherit" type="button" onClick={() => setIsOpen(false)} aria-label="Close design switcher">
                <X aria-hidden="true" />
              </button>
            </header>
            <nav className="grid grid-cols-2 gap-[7px]" aria-label="Choose application design">{choices}</nav>
          </section>
        </div>
      )}
    </>
  );
}

export default DesignSwitcher;
