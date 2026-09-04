interface HardwoodPageStateProps {
  kind: "loading" | "error" | "empty";
  title?: string;
  detail?: string;
}

function HardwoodPageState({kind, title, detail}: HardwoodPageStateProps) {
  const defaults = {
    loading: ["Loading the floor", "Pulling the latest data."],
    error: ["The feed went quiet", "Please try this page again shortly."],
    empty: ["No games on the board", "Choose another night."],
  } as const;

  return (
    <section
      className="mx-auto mt-[54px] mb-[90px] w-[min(1180px,calc(100%_-_56px))] rounded-[14px] border border-hw-line bg-hw-surface px-[clamp(32px,7vw,92px)] py-[clamp(48px,6vw,76px)] text-center max-[700px]:w-[min(calc(100%_-_28px),1180px)] max-[700px]:px-5 max-[700px]:py-[42px]"
      role={kind === "error" ? "alert" : "status"}
    >
      <span className="mb-[18px] inline-grid size-[52px] place-items-center rounded-hw bg-hw-accent font-extrabold text-hw-accent-contrast" aria-hidden="true">
        {kind === "loading" ? "•••" : kind === "error" ? "!" : "0"}
      </span>
      <h2 className="text-[clamp(1.8rem,5vw,3.2rem)] leading-none font-extrabold tracking-[.01em] uppercase">
        {title ?? defaults[kind][0]}
      </h2>
      <p className="mt-[9px] text-[13px] text-hw-muted">{detail ?? defaults[kind][1]}</p>
    </section>
  );
}

export default HardwoodPageState;
