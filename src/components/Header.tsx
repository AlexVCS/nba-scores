const Header = () => {
  return (
    <article>
      <header className="flex flex-col justify-center items-center pt-4 gap-2">
        <img className="w-24" src="/images/nba_logo.svg" alt="NBA Logo" />
        <h1 className="text-4xl dark:text-slate-50 text-neutral-950">Scorez</h1>
      </header>
    </article>
  );
}

export default Header