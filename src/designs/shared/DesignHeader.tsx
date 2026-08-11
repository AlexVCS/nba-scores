import {Link} from "react-router";
import DarkModeToggle from "@/components/DarkModeToggle";
import {getDesignDefinition} from "../designRegistry";
import {designPath} from "../designRoutes";
import type {AlternateDesignId} from "../types";

interface DesignHeaderProps {
  designId: AlternateDesignId;
  section: "scores" | "playoffs" | "boxscore" | "series";
}

const LOGO_DESIGNS = new Set<AlternateDesignId>(["design-1", "design-4"]);

const TAGLINES: Record<Exclude<AlternateDesignId, "design-1" | "design-4">, string> = {
  "design-2": "Every game on the radar, coast to coast",
  "design-3": "Tonight’s numbers, up in lights",
};

function DesignHeader({designId, section}: DesignHeaderProps) {
  const definition = getDesignDefinition(designId);
  const isPlaybook = designId === "design-1";
  const showsLogo = LOGO_DESIGNS.has(designId);
  const usesPlayoffzLogo = designId === "design-4" && (section === "playoffs" || section === "series");

  return (
    <header className="concept-header">
      <div className="concept-header__utility">
        {!isPlaybook && designId !== "design-4" && (
          <span className="concept-header__issue">NBA / {String(definition.number).padStart(2, "0")}</span>
        )}
        <DarkModeToggle />
      </div>
      <div className="concept-header__brand">
        {showsLogo ? (
          <Link to={designPath(designId, "/")} className="concept-header__logo-link">
            <img
              className={`concept-header__logo${usesPlayoffzLogo ? " concept-header__logo--playoffz" : ""}`}
              src={usesPlayoffzLogo ? "/images/playoffz.png" : "/images/dark-mode-logo.webp"}
              alt={usesPlayoffzLogo ? "NBA Playoffz" : "NBA Scorez"}
            />
          </Link>
        ) : (
          <>
            <Link to={designPath(designId, "/")} className="concept-header__title">
              {definition.name}
            </Link>
            <p>{TAGLINES[designId as Exclude<AlternateDesignId, "design-1" | "design-4">]}</p>
          </>
        )}
      </div>
      <nav aria-label={`${definition.name} navigation`}>
        <Link className={section === "scores" || section === "boxscore" ? "is-active" : ""} to={designPath(designId, "/")}>Scorez</Link>
        <Link className={section === "playoffs" || section === "series" ? "is-active" : ""} to={designPath(designId, "/playoffs")}>Playoffz</Link>
      </nav>
    </header>
  );
}

export default DesignHeader;
