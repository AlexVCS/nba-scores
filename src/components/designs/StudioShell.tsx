import type {ReactNode} from "react";
import {Link} from "react-router";
import DarkModeToggle from "@/components/DarkModeToggle";
import RoutePatternNav from "@/components/designs/patterns/RoutePatternNav";

interface StudioShellProps {
  title: string;
  eyebrow: string;
  children: ReactNode;
  actions?: ReactNode;
  backTo?: string;
  backLabel?: string;
  variant?: "studio" | "arcade" | "tournament" | "editorial" | "analytics";
}

const variantClasses = {
  studio:
    "bg-[radial-gradient(circle_at_top_left,rgba(14,165,233,0.20),transparent_32rem),linear-gradient(135deg,#f8fafc,#e2e8f0)] dark:bg-[radial-gradient(circle_at_top_left,rgba(56,189,248,0.16),transparent_34rem),linear-gradient(135deg,#020617,#111827_55%,#020617)]",
  arcade:
    "bg-[radial-gradient(circle_at_top,rgba(245,158,11,0.20),transparent_24rem),linear-gradient(180deg,#160c08,#030303_55%,#111)]",
  tournament:
    "bg-[linear-gradient(135deg,#f8fafc,#dbeafe_48%,#f8fafc)] dark:bg-[radial-gradient(circle_at_50%_0%,rgba(59,130,246,0.18),transparent_30rem),linear-gradient(135deg,#020617,#0f172a_45%,#020617)]",
  editorial:
    "bg-[linear-gradient(135deg,#fff7ed,#f8fafc_45%,#e0f2fe)] dark:bg-[linear-gradient(135deg,#0c0a09,#111827_42%,#082f49)]",
  analytics:
    "bg-[linear-gradient(135deg,#f1f5f9,#ffffff_42%,#ecfeff)] dark:bg-[radial-gradient(circle_at_top_right,rgba(20,184,166,0.16),transparent_26rem),linear-gradient(135deg,#020617,#0f172a_55%,#042f2e)]",
};

function StudioShell({
  title,
  eyebrow,
  children,
  actions,
  backTo = "/",
  backLabel = "Production",
  variant = "studio",
}: StudioShellProps) {
  const isArcade = variant === "arcade";

  return (
    <main
      className={`min-h-screen overflow-x-hidden text-slate-950 dark:text-slate-50 ${variantClasses[variant]}`}
    >
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-5 px-3 py-3 sm:px-5 lg:px-8">
        <nav
          className={`flex flex-wrap items-center justify-between gap-3 rounded-lg border px-3 py-2 shadow-sm backdrop-blur ${
            isArcade
              ? "border-amber-500/30 bg-black/70 text-amber-100 shadow-amber-950/40"
              : "border-white/55 bg-white/70 dark:border-white/10 dark:bg-slate-950/55"
          }`}
        >
          <div className="flex items-center gap-3">
            <DarkModeToggle />
            <Link
              to={backTo}
              className={`text-sm font-bold underline-offset-4 hover:underline ${
                isArcade
                  ? "text-amber-300 hover:text-amber-100"
                  : "text-sky-700 hover:text-sky-900 dark:text-sky-300 dark:hover:text-sky-100"
              }`}
            >
              {backLabel}
            </Link>
          </div>
          <RoutePatternNav />
        </nav>

        <header className="grid gap-4 py-2 sm:grid-cols-[1fr_auto] sm:items-end">
          <div>
            <p
              className={`text-xs font-black uppercase tracking-[0.34em] ${
                isArcade
                  ? "text-amber-400"
                  : "text-sky-700 dark:text-sky-300"
              }`}
            >
              {eyebrow}
            </p>
            <h1
              className={`mt-1 max-w-4xl text-3xl font-black tracking-tight sm:text-5xl ${
                isArcade
                  ? "font-mono text-amber-100 [text-shadow:0_0_20px_rgba(245,158,11,0.45)]"
                  : ""
              }`}
            >
              {title}
            </h1>
          </div>
          {actions && <div className="sm:justify-self-end">{actions}</div>}
        </header>

        {children}
      </div>
    </main>
  );
}

export default StudioShell;
