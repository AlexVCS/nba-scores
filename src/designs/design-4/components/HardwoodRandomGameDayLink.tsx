import {Link} from "react-router";
import {useRandomGameDay} from "@/hooks/useRandomGameDay";
import {designPath} from "../../designRoutes";
import {hwActionLink} from "./hardwoodStyles";

interface HardwoodRandomGameDayLinkProps {
  dateParam: string;
}

function HardwoodRandomGameDayLink({dateParam}: HardwoodRandomGameDayLinkProps) {
  const {isLoading, randomGameDay} = useRandomGameDay({dateParam});
  const primaryClasses = `${hwActionLink} border-hw-accent bg-hw-accent text-hw-accent-contrast hover:brightness-[.94] dark:border-hw-accent! dark:bg-hw-accent! dark:text-hw-accent-contrast!`;

  if (isLoading || !randomGameDay) {
    return <span className={`${primaryClasses} cursor-wait opacity-72`} aria-live="polite">Finding a game day…</span>;
  }

  return (
    <Link className={primaryClasses} to={designPath("design-4", `/?date=${randomGameDay}`)}>
      Random Game Day
    </Link>
  );
}

export default HardwoodRandomGameDayLink;
