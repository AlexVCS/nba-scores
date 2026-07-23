interface PageStateProps {
  kind: "loading" | "error" | "empty";
  title?: string;
  detail?: string;
}

function PageState({kind, title, detail}: PageStateProps) {
  const defaults = {
    loading: ["Loading the floor", "Pulling the latest data."],
    error: ["The feed went quiet", "Please try this page again shortly."],
    empty: ["No games on the board", "Choose another night."],
  } as const;

  return (
    <section className={`concept-page-state concept-page-state--${kind}`} role={kind === "error" ? "alert" : "status"}>
      <span aria-hidden="true">{kind === "loading" ? "•••" : kind === "error" ? "!" : "0"}</span>
      <h2>{title ?? defaults[kind][0]}</h2>
      <p>{detail ?? defaults[kind][1]}</p>
    </section>
  );
}

export default PageState;
