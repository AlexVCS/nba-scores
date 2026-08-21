import { useTheme } from "@/hooks/useTheme";

type HeaderProps = {
  variant?: "default" | "playoffs";
};

const Header = ({ variant = "default" }: HeaderProps) => {
  const isPlayoffs = variant === "playoffs";
  const { theme } = useTheme();
  const playoffzSrc = theme === "dark" ? "/images/playoffz-dark.png" : "/images/playoffz.png";

  return (
    <article>
      <header className="flex flex-col justify-center items-center pt-4 gap-2">
        {isPlayoffs ? (
          <img
            className="w-48 sm:w-xs"
            src={playoffzSrc}
            alt="NBA Playoffz Logo"
          />
        ) : (
          <img
            className="w-xs"
            src="/images/dark-mode-logo.webp"
            alt="NBA Scorez Logo"
          />
        )}
      </header>
    </article>
  );
};

export default Header;
