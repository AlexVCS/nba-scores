const Header = () => {
  return (
    <article>
      <header className="flex flex-col justify-center items-center pt-4 gap-2">
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
      </header>
    </article>
  );
};

export default Header;