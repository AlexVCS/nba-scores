import {Link} from "react-router";
import DarkModeToggle from "@/components/DarkModeToggle";
import {designPath} from "../../designRoutes";
import {hwContainer} from "./hardwoodStyles";

interface HardwoodHeaderProps {
  section: "scores" | "playoffs" | "boxscore" | "series";
}

function HardwoodHeader({section}: HardwoodHeaderProps) {
  const usesPlayoffzLogo = section === "playoffs" || section === "series";
  const scoresActive = section === "scores" || section === "boxscore";
  const playoffsActive = section === "playoffs" || section === "series";
  const navLink =
    "relative py-3 text-xs font-bold tracking-[.12em] text-hw-court uppercase no-underline after:absolute after:right-0 after:-bottom-px after:left-0 after:h-1 after:bg-transparent";

  return (
    <header className={`${hwContainer} border-b border-hw-line pt-5`}>
      <div className="flex min-h-[38px] items-center justify-end border-b border-hw-line">
        <DarkModeToggle />
      </div>
      <div className="py-5.5 max-[700px]:py-5">
        <Link className="mx-auto block w-fit" to={designPath("design-4", "/")}>
          <img
            className={usesPlayoffzLogo
              ? "block h-auto w-[clamp(250px,28vw,340px)]"
              : "my-[clamp(-40px,-3vw,-28px)] block h-auto w-[clamp(230px,24vw,300px)] max-[700px]:w-[clamp(200px,64vw,260px)]"}
            src={usesPlayoffzLogo ? "/images/playoffz.png" : "/images/dark-mode-logo.webp"}
            alt={usesPlayoffzLogo ? "NBA Playoffz" : "NBA Scorez"}
          />
        </Link>
      </div>
      <nav className="flex items-center justify-center gap-[34px]" aria-label="Gold on Hardwood navigation">
        <Link className={`${navLink} ${scoresActive ? "text-hw-ink after:bg-hw-accent" : ""}`} to={designPath("design-4", "/")}>Scorez</Link>
        <Link className={`${navLink} ${playoffsActive ? "text-hw-ink after:bg-hw-accent" : ""}`} to={designPath("design-4", "/playoffs")}>Playoffz</Link>
      </nav>
    </header>
  );
}

export default HardwoodHeader;
