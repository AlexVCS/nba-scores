import {Link} from "react-router";
import DarkModeToggle from "@/components/DarkModeToggle";
import {useTheme} from "@/hooks/useTheme";
import {designPath} from "../../designRoutes";
import {hwContainer} from "./hardwoodStyles";
import HardwoodResultsToggle from "./HardwoodResultsToggle";

interface HardwoodHeaderProps {
  section: "scores" | "playoffs" | "boxscore" | "series";
  scoresPath?: string;
}

function HardwoodHeader({section, scoresPath = "/"}: HardwoodHeaderProps) {
  const usesPlayoffzLogo = section === "playoffs" || section === "series";
  const {theme} = useTheme();
  const playoffzSrc = theme === "dark" ? "/images/playoffz-dark.png" : "/images/playoffz.png";
  const scorezSrc = theme === "dark"
    ? "/images/nba-scorez-lockup-dark.svg"
    : "/images/nba-scorez-lockup.svg";
  const scoresActive = section === "scores" || section === "boxscore";
  const playoffsActive = section === "playoffs" || section === "series";
  const navLink =
    "relative py-3 text-xs font-bold tracking-[.12em] text-hw-court uppercase no-underline after:absolute after:right-0 after:-bottom-px after:left-0 after:h-1 after:bg-transparent";

  return (
    <header className={`${hwContainer} border-b border-hw-line pt-5`}>
      <div className="flex min-h-14 items-center justify-end border-b border-hw-line py-1.5">
        <div
          className="flex items-center gap-1 rounded-hw border border-hw-line bg-hw-surface p-1 shadow-hw-small"
          role="group"
          aria-label="Viewing preferences"
        >
          <div className="[&_button]:size-11! [&_button]:rounded-[7px] [&_button]:text-hw-muted! [&_button:hover]:bg-hw-surface-muted [&_button:hover]:text-hw-accent-ink! [&_button:focus-visible]:outline-2 [&_button:focus-visible]:outline-offset-2 [&_button:focus-visible]:outline-hw-accent dark:[&_button:hover]:text-hw-accent!">
            <DarkModeToggle />
          </div>
          <HardwoodResultsToggle />
        </div>
      </div>
      <div className="py-4 md:py-4.5 xl:py-5">
        <Link className="mx-auto block w-fit" to={designPath("design-1", scoresPath)}>
          {/* Both lockups share a 309-unit box with the badge, cap height and baseline
              in the same place, so sizing by height lands them identically and the
              nav below never shifts between Scorez and Playoffz. */}
          <img
            className="block h-[clamp(84px,9vw,126px)] w-auto max-[700px]:h-[clamp(76px,20vw,84px)]"
            src={usesPlayoffzLogo ? playoffzSrc : scorezSrc}
            alt={usesPlayoffzLogo ? "NBA Playoffz" : "NBA Scorez"}
          />
        </Link>
      </div>
      <nav className="flex items-center justify-center gap-[34px]" aria-label="Gold on Hardwood navigation">
        <Link className={`${navLink} ${scoresActive ? "text-hw-ink after:bg-hw-accent" : ""}`} to={designPath("design-1", scoresPath)}>Scorez</Link>
        <Link className={`${navLink} ${playoffsActive ? "text-hw-ink after:bg-hw-accent" : ""}`} to={designPath("design-1", "/playoffs")}>Playoffz</Link>
      </nav>
    </header>
  );
}

export default HardwoodHeader;
