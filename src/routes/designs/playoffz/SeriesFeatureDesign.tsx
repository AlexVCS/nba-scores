import {useMemo} from "react";
import {Link, useParams, useSearchParams} from "react-router-dom";
import MotionCascade from "@/components/designs/motion/MotionCascade";
import DesignEmptyState from "@/components/designs/patterns/DesignEmptyState";
import SkeletonBlock from "@/components/designs/patterns/SkeletonBlock";
import StudioShell from "@/components/designs/StudioShell";
import {usePlayoffData} from "@/hooks/usePlayoffData";
import {buildPlayoffBracketModel} from "@/utils/playoffBracketModel";
import {findSeriesBySlug, yearToSeason} from "@/utils/seriesSlug";
import SeriesFeatureHero from "./SeriesFeatureHero";
import SeriesGameLedger from "./SeriesGameLedger";

function SeriesFeatureDesign() {
  const {year, seriesSlug} = useParams<{year: string; seriesSlug: string}>();
  const isValidYear = !!year && /^\d{4}$/.test(year);
  const season = isValidYear ? yearToSeason(year) : null;
  const [searchParams, setSearchParams] = useSearchParams();
  const isRevealed = searchParams.get("revealed") === "true";
  const {data, isLoading, error} = usePlayoffData(season);
  const model = useMemo(() => (data ? buildPlayoffBracketModel(data) : null), [data]);
  const slugSeries = model ? findSeriesBySlug(seriesSlug ?? "", model.series) : undefined;
  const series = slugSeries
    ? model?.series.find((item) => item.seriesKey === slugSeries.seriesKey)
    : undefined;

  const setIsRevealed = (value: boolean) => {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        if (value) next.set("revealed", "true");
        else next.delete("revealed");
        return next;
      },
      {replace: true},
    );
  };

  return (
    <StudioShell
      title="Split-Screen Series Feature"
      eyebrow="Preview route /designs/series-feature"
      backTo={`/designs/playoffz-map${season ? `?season=${season}` : ""}`}
      backLabel="Transit map"
      variant="editorial"
    >
      <section className="grid gap-6">
        {!isValidYear && (
          <DesignEmptyState
            title="Invalid season year"
            message="Use a four-digit playoff year to open this feature layout."
            actionTo="/designs/playoffz-map"
            actionLabel="Open transit map"
          />
        )}

        {isLoading && (
          <div className="grid gap-4 lg:grid-cols-[0.85fr_1.15fr]">
            <SkeletonBlock className="h-[520px]" />
            <SkeletonBlock className="h-[520px]" />
          </div>
        )}

        {error && (
          <DesignEmptyState
            title="Series feature could not load"
            message={String(error)}
            className="border-amber-300 bg-amber-50 text-amber-950 dark:border-amber-300/25 dark:bg-amber-300/10 dark:text-amber-100"
          />
        )}

        {!isLoading && !error && isValidYear && !series && (
          <DesignEmptyState
            title="Series not found"
            message="The selected matchup was not found for this playoff season."
            actionTo={`/designs/playoffz-map${season ? `?season=${season}` : ""}`}
            actionLabel="Back to map"
          />
        )}

        {series && data && (
          <>
            <SeriesFeatureHero
              series={series}
              season={data.season}
              isRevealed={isRevealed}
              onRevealChange={setIsRevealed}
            />
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-xs font-black uppercase tracking-[0.24em] text-amber-700 dark:text-amber-300">
                  Ledger
                </p>
                <h2 className="text-3xl font-black tracking-tighter">
                  Game-by-game file
                </h2>
              </div>
              <Link
                to={`/designs/playoffz-map?season=${season}`}
                className="hidden rounded-full border border-amber-300 px-4 py-2 text-sm font-black uppercase tracking-[0.16em] text-amber-900 hover:bg-amber-100 active:scale-[0.98] dark:border-amber-300/20 dark:text-amber-100 dark:hover:bg-amber-300/10 sm:inline-flex"
              >
                Map
              </Link>
            </div>
            {series.games.length === 0 ? (
              <DesignEmptyState
                title="No games listed"
                message="This matchup does not include a game ledger."
              />
            ) : (
              <MotionCascade>
                <SeriesGameLedger
                  series={series}
                  isRevealed={isRevealed}
                  season={data.season}
                />
              </MotionCascade>
            )}
            <div className="h-16 sm:hidden" />
            <div className="fixed inset-x-0 bottom-0 bg-[#fbf7ef]/90 px-4 py-3 backdrop-blur dark:bg-zinc-950/90 sm:hidden">
              <Link
                to={`/designs/playoffz-map?season=${season}`}
                className="flex w-full justify-center rounded-full border border-amber-300 px-4 py-3 text-sm font-black uppercase tracking-[0.16em] text-amber-900 active:scale-[0.98] dark:border-amber-300/20 dark:text-amber-100"
              >
                Back to map
              </Link>
            </div>
          </>
        )}
      </section>
    </StudioShell>
  );
}

export default SeriesFeatureDesign;
