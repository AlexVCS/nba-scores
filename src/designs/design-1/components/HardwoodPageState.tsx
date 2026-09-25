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
      className="mx-auto mt-10 mb-[72px] w-[min(620px,calc(100%_-_56px))] rounded-[14px] border border-hw-line bg-hw-surface px-[clamp(24px,4vw,48px)] py-[clamp(28px,3.5vw,40px)] text-center max-[700px]:w-[min(calc(100%_-_28px),620px)] max-[700px]:px-5 max-[700px]:py-7"
      role={kind === "error" ? "alert" : "status"}
    >
      <h2 className="text-hw-heading leading-tight font-bold tracking-[.04em] uppercase">
        {title ?? defaults[kind][0]}
      </h2>
      <p className="mt-[9px] text-[13px] text-hw-muted">{detail ?? defaults[kind][1]}</p>
    </section>
  );
}

export default HardwoodPageState;
