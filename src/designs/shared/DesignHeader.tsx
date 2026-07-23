import {Link} from "react-router";
import DarkModeToggle from "@/components/DarkModeToggle";
import {getDesignDefinition} from "../designRegistry";
import {designPath} from "../designRoutes";
import type {AlternateDesignId} from "../types";

interface DesignHeaderProps {
  designId: AlternateDesignId;
  section: "scores" | "playoffs" | "boxscore" | "series";
}

const TAGLINES: Record<AlternateDesignId, string> = {
  "design-1": "The daily record of the Association",
  "design-2": "Live from the basketball control room",
  "design-3": "The game, after hours",
  "design-4": "Tonight’s board. Every possession matters.",
  "design-5": "Games, reduced to signal",
};

function DesignHeader({designId, section}: DesignHeaderProps) {
  const definition = getDesignDefinition(designId);

  return (
    <header className="concept-header">
      <div className="concept-header__utility">
        <span className="concept-header__issue">NBA / {String(definition.number).padStart(2, "0")}</span>
        <DarkModeToggle />
      </div>
      <div className="concept-header__brand">
        <Link to={designPath(designId, "/")} className="concept-header__title">
          {definition.name}
        </Link>
        <p>{TAGLINES[designId]}</p>
      </div>
      <nav aria-label={`${definition.name} navigation`}>
        <Link className={section === "scores" || section === "boxscore" ? "is-active" : ""} to={designPath(designId, "/")}>Scores</Link>
        <Link className={section === "playoffs" || section === "series" ? "is-active" : ""} to={designPath(designId, "/playoffs")}>Playoffs</Link>
      </nav>
    </header>
  );
}

export default DesignHeader;
