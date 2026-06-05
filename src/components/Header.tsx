type HeaderProps = {
  variant?: "default" | "playoffs";
};

const Header = ({ variant = "default" }: HeaderProps) => {
  const isPlayoffs = variant === "playoffs";

  return (
    <article>
      <header className="flex flex-col justify-center items-center pt-4 gap-2">
        {isPlayoffs ? (
          <img
            className="w-xs"
            src="/images/playoffz.png"
            alt="NBA Playoffz Logo"
          />
        ) : (
          <>
            <img
              className="w-xs dark:hidden"
              src="/images/light-mode-logo.webp"
              alt="NBA Scorez Logo"
            />
            <img
              className="w-xs hidden dark:block"
              src="/images/dark-mode-logo.webp"
              alt="NBA Scorez Logo"
            />
          </>
        )}
      </header>
    </article>
  );
};

export default Header;