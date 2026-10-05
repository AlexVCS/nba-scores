import { useTheme } from "@/hooks/useTheme";
import AskEntry from "@/components/ask/AskEntry";

type HeaderProps = {
  variant?: "default" | "playoffs";
};

const Header = ({ variant = "default" }: HeaderProps) => {
  const isPlayoffs = variant === "playoffs";
  const { theme } = useTheme();
  const playoffzSrc = theme === "dark" ? "/images/playoffz-dark.png" : "/images/playoffz.png";
  const scorezSrc = theme === "dark"
    ? "/images/nba-scorez-lockup-dark.svg"
    : "/images/nba-scorez-lockup.svg";

  return (
    <article>
      <header className="flex flex-col justify-center items-center pt-4 gap-2">
        <div className="flex w-full justify-center px-4 pb-2">
          <AskEntry variant="original" />
        </div>
        {isPlayoffs ? (
          <img
            className="w-48 sm:w-xs"
            src={playoffzSrc}
            alt="NBA Playoffz Logo"
          />
        ) : (
          <img
            className="w-xs"
            src={scorezSrc}
            alt="NBA Scorez Logo"
          />
        )}
      </header>
    </article>
  );
};

export default Header;
