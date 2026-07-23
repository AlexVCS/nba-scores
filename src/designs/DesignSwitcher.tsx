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
      className="design-switcher__choice"
      onClick={() => setIsOpen(false)}
    >
      <span className="design-switcher__number">{design.number ?? "O"}</span>
      <span className="design-switcher__name">{design.shortName}</span>
    </Link>
  ));

  return (
    <>
      <nav className="design-switcher design-switcher--desktop" aria-label="Choose application design">
        <span className="design-switcher__eyebrow">VIEW</span>
        {choices}
      </nav>

      <button
        type="button"
        className="design-switcher__mobile-trigger"
        aria-haspopup="dialog"
        aria-expanded={isOpen}
        onClick={() => setIsOpen(true)}
      >
        <Layers3 aria-hidden="true" size={17} />
        {active.number === null ? "Original" : `Design ${active.number}`}
      </button>

      {isOpen && (
        <div className="design-switcher__backdrop" role="presentation" onMouseDown={() => setIsOpen(false)}>
          <section
            role="dialog"
            aria-modal="true"
            aria-label="Choose application design"
            className="design-switcher__sheet"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <header>
              <div>
                <span>Compare concepts</span>
                <strong>{active.name}</strong>
              </div>
              <button type="button" onClick={() => setIsOpen(false)} aria-label="Close design switcher">
                <X aria-hidden="true" />
              </button>
            </header>
            <nav aria-label="Choose application design">{choices}</nav>
          </section>
        </div>
      )}
    </>
  );
}

export default DesignSwitcher;
