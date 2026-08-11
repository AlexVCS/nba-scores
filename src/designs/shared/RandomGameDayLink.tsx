import {Link} from "react-router";
import {useRandomGameDay} from "@/hooks/useRandomGameDay";
import {designPath} from "../designRoutes";
import type {AlternateDesignId} from "../types";

interface RandomGameDayLinkProps {
  dateParam: string;
  designId: AlternateDesignId;
}

function RandomGameDayLink({dateParam, designId}: RandomGameDayLinkProps) {
  const {isLoading, randomGameDay} = useRandomGameDay({dateParam});

  if (isLoading || !randomGameDay) {
    return <span className="concept-empty-links__primary is-loading" aria-live="polite">Finding a game day…</span>;
  }

  return (
    <Link className="concept-empty-links__primary" to={designPath(designId, `/?date=${randomGameDay}`)}>
      Random Game Day
    </Link>
  );
}

export default RandomGameDayLink;
