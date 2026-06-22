import {useEffect, useState} from "react";
import {Link, useSearchParams} from "react-router";
import PlayoffBracketFlow from "@/components/PlayoffBracketFlow";
import PlayoffYearPicker from "@/components/PlayoffYearPicker";
import StatusPill from "@/components/designs/StatusPill";
import StudioShell from "@/components/designs/StudioShell";
import {usePlayoffData} from "@/hooks/usePlayoffData";
import {PLAYOFF_PREVIEW_SEASON} from "@/routes/designs/designDefaults";

function PlayoffzDesign() {
  const [searchParams, setSearchParams] = useSearchParams();
  const seasonParam = searchParams.get("season");
  const [season, setSeason] = useState<string | null>(seasonParam);

  useEffect(() => {
    setSeason(seasonParam || PLAYOFF_PREVIEW_SEASON);
  }, [seasonParam]);

  useEffect(() => {
    if (!seasonParam) {
      setSearchParams({season: PLAYOFF_PREVIEW_SEASON}, {replace: true});
    }
  }, [seasonParam, setSearchParams]);

  const {data, isLoading, error} = usePlayoffData(season);

  return (
    <StudioShell
      title="Tournament Control Room"
      eyebrow="Preview route /designs/playoffz"
      backTo="/playoffs"
      backLabel="Current Playoffz"
      variant="tournament"
      actions={<PlayoffYearPicker />}
    >
      <section className="grid gap-5">
        <div className="grid gap-3 rounded-lg border border-white/70 bg-white/75 p-4 shadow-xl shadow-blue-200/30 backdrop-blur dark:border-white/10 dark:bg-slate-950/65 dark:shadow-black/25 sm:grid-cols-[1fr_auto] sm:items-center">
          <div>
            <StatusPill tone="scheduled">Bracket command</StatusPill>
            <h2 className="mt-3 text-2xl font-black tracking-tight">
              {season ?? "Loading season"} Playoff Picture
            </h2>
            <p className="mt-1 max-w-2xl text-sm text-slate-600 dark:text-slate-300">
              Reveal each round from the control strip, then open any matchup in
              the editorial preview route.
            </p>
          </div>
          <Link
            to="/designs/scorez"
            className="w-fit rounded-md bg-slate-950 px-4 py-3 text-sm font-black text-white hover:bg-blue-700 dark:bg-white dark:text-slate-950 dark:hover:bg-blue-100"
          >
            Daily Scorez
          </Link>
        </div>

        {isLoading && (
          <div className="rounded-lg border border-white/70 bg-white/75 p-10 text-center font-bold dark:border-white/10 dark:bg-slate-950/60">
            Loading playoff control board...
          </div>
        )}
        {error && (
          <div className="rounded-lg border border-red-300 bg-red-50 p-10 text-center font-bold text-red-800 dark:border-red-400/40 dark:bg-red-500/10 dark:text-red-200">
            Error loading playoff data: {String(error)}
          </div>
        )}
        {data && (
          <div className="rounded-lg border border-slate-300/70 bg-slate-100/70 p-3 shadow-2xl shadow-blue-300/20 dark:border-white/10 dark:bg-slate-950/70 dark:shadow-black/30 sm:p-5">
            <div className="mb-4 grid gap-3 border-b border-slate-300 pb-4 dark:border-white/10 sm:grid-cols-3">
              <div>
                <p className="text-xs font-black uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">
                  Series
                </p>
                <p className="text-2xl font-black">{data.seriesCount}</p>
              </div>
              <div>
                <p className="text-xs font-black uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">
                  Games
                </p>
                <p className="text-2xl font-black">{data.gameCount}</p>
              </div>
              <div>
                <p className="text-xs font-black uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">
                  Format
                </p>
                <p className="text-sm font-bold">
                  {data.format?.bracketType ?? "playoff bracket"}
                </p>
              </div>
            </div>
            <PlayoffBracketFlow playoffPicture={data} seriesRouteBase="design" />
          </div>
        )}
      </section>
    </StudioShell>
  );
}

export default PlayoffzDesign;
