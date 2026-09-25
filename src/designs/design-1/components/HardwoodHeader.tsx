import {useId, useRef} from "react";
import {Link} from "react-router";
import DarkModeToggle from "@/components/DarkModeToggle";
import {useTheme} from "@/hooks/useTheme";
import {useResultsVisibility} from "@/hooks/useResultsVisibility";
import {designPath} from "../../designRoutes";
import {hwContainer} from "./hardwoodStyles";
import HardwoodResultsToggle from "./HardwoodResultsToggle";
import HardwoodSpoilerHint from "./HardwoodSpoilerHint";

interface HardwoodHeaderProps {
  section: "scores" | "playoffs" | "boxscore" | "series";
  scoresPath?: string;
}

function HardwoodHeader({section, scoresPath = "/"}: HardwoodHeaderProps) {
  const usesPlayoffzLogo = section === "playoffs" || section === "series";
  const {theme} = useTheme();
  const {showAllResults, setShowAllResults, isSpoilerHintDismissed, dismissSpoilerHint} = useResultsVisibility();
  const resultsControlRef = useRef<HTMLButtonElement>(null);
  const hintId = useId();
  const showHint = !showAllResults && !isSpoilerHintDismissed;
  const wording = section === "playoffs" ? "Results" : "Scorez";
  const dismissHint = () => {
    dismissSpoilerHint();
    resultsControlRef.current?.focus({preventScroll: true});
  };
  const playoffzSrc = theme === "dark" ? "/images/playoffz-dark.png" : "/images/playoffz.png";
  const scorezSrc = theme === "dark"
    ? "/images/nba-scorez-lockup-dark.svg"
    : "/images/nba-scorez-lockup.svg";
  const scoresActive = section === "scores" || section === "boxscore";
  const playoffsActive = section === "playoffs" || section === "series";
  const navLink =
    "relative py-3 text-xs font-bold tracking-[.12em] text-hw-court uppercase no-underline after:absolute after:right-0 after:-bottom-px after:left-0 after:h-1";

  return (
    <header className={`${hwContainer} border-b border-hw-line pt-5`}>
      <div className="flex min-h-14 items-center justify-end gap-3 border-b border-hw-line py-1.5">
        <div
          className="flex items-center gap-1 rounded-hw border border-hw-line bg-hw-surface p-1 shadow-hw-small"
          role="group"
          aria-label="Viewing preferences"
        >
          <div className="[&_button]:size-11! [@media(pointer:fine)]:[&_button]:size-9! [&_svg]:size-[18px] [@media(pointer:fine)]:[&_svg]:size-4 [&_button]:rounded-[7px] [&_button]:text-hw-muted! [&_button:hover]:bg-hw-surface-muted [&_button:hover]:text-hw-accent-ink! [&_button:focus-visible]:outline-2 [&_button:focus-visible]:outline-offset-2 [&_button:focus-visible]:outline-hw-accent dark:[&_button:hover]:text-hw-accent!">
            <DarkModeToggle />
          </div>
          <HardwoodResultsToggle wording={wording} controlRef={resultsControlRef} hintId={showHint ? hintId : undefined} />
        </div>
      </div>
      <div className="grid grid-cols-[minmax(0,1fr)] xl:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] xl:grid-rows-[auto_auto_1fr]">
        {showHint && (
          <div className="w-full max-w-80 justify-self-end pt-3 xl:col-start-3 xl:row-span-3 xl:row-start-1 xl:w-72">
            <HardwoodSpoilerHint
              id={hintId}
              wording={wording}
              onDismiss={dismissHint}
              onShowResults={() => {
                setShowAllResults(true);
                dismissHint();
              }}
            />
          </div>
        )}
        <div className="py-3 md:py-3.5 xl:col-start-2 xl:row-start-1 xl:py-4">
          <Link className="mx-auto block w-fit" to={designPath("design-1", usesPlayoffzLogo ? "/playoffs" : scoresPath)}>
            {/* Both lockups share a 309-unit box with the badge, cap height and baseline
                in the same place, so sizing by height lands them identically and the
                nav below never shifts between Scorez and Playoffz. */}
            <img
              className="block h-[clamp(72px,6vw,88px)] w-auto max-[700px]:h-[clamp(76px,20vw,84px)]"
              src={usesPlayoffzLogo ? playoffzSrc : scorezSrc}
              alt={usesPlayoffzLogo ? "NBA Playoffz" : "NBA Scorez"}
            />
          </Link>
        </div>
        <nav className="flex items-center justify-center gap-[34px] xl:col-start-2 xl:row-start-2" aria-label="Gold on Hardwood navigation">
          <Link className={`${navLink} ${scoresActive ? "text-hw-ink after:bg-hw-accent-ink" : "after:bg-transparent"}`} to={designPath("design-1", scoresPath)}>Scorez</Link>
          <Link className={`${navLink} ${playoffsActive ? "text-hw-ink after:bg-hw-accent-ink" : "after:bg-transparent"}`} to={designPath("design-1", "/playoffs")}>Playoffz</Link>
        </nav>
      </div>
    </header>
  );
}

export default HardwoodHeader;
