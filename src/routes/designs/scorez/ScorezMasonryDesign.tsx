import {useEffect, useState} from "react";
import {Switch} from "@adobe/react-spectrum";
import {useQuery} from "@tanstack/react-query";
import {useSearchParams} from "react-router";
import GameDatePicker from "@/components/GameDatePicker";
import MotionCascade from "@/components/designs/motion/MotionCascade";
import DesignEmptyState from "@/components/designs/patterns/DesignEmptyState";
import SkeletonBlock from "@/components/designs/patterns/SkeletonBlock";
import StudioShell from "@/components/designs/StudioShell";
import {getItem, setItem} from "@/helpers/helpers";
import {SCOREZ_PREVIEW_DATE} from "@/routes/designs/designDefaults";
import {getScores} from "@/services/nbaService";
import MasonryGameTile, {type DesignScoreGame} from "./MasonryGameTile";

function ScorezMasonryDesign() {
  const [searchParams, setSearchParams] = useSearchParams({date: ""});
  const dateParam = searchParams.get("date") || SCOREZ_PREVIEW_DATE;
  const [showScores, setShowScores] = useState(() => {
    const item = getItem("showScores");
    return item === undefined ? false : item;
  });

  useEffect(() => {
    if (!searchParams.get("date")) {
      setSearchParams({date: SCOREZ_PREVIEW_DATE}, {replace: true});
    }
  }, [searchParams, setSearchParams]);

  useEffect(() => {
    setItem("showScores", showScores);
  }, [showScores]);

  const {isLoading, data, error} = useQuery({
    queryKey: ["design-masonry-games", dateParam],
    queryFn: () => getScores(dateParam) as Promise<{games: DesignScoreGame[]}>,
  });

  const games = data?.games ?? [];
  const hasStartedGames = games.some((game) => game.gameStatus !== 1);

  return (
    <StudioShell
      title="Masonry Schedule Wall"
      eyebrow="Preview route /designs/scorez-masonry"
      backTo="/"
      backLabel="Current Scorez"
      variant="editorial"
      actions={<GameDatePicker />}
    >
      <section className="mx-auto grid w-full max-w-[1400px] gap-6">
        <div className="grid gap-5 md:grid-cols-[minmax(0,1.4fr)_minmax(240px,0.6fr)] md:items-end">
          <div className="max-w-3xl">
            <p className="text-base leading-relaxed text-slate-600 dark:text-slate-300">
              A curated wall for the day’s matchups, weighted toward games that
              have already tipped. Deep rose is the only accent; the rest is
              thin-line editorial structure.
            </p>
          </div>
          <div className="rounded-[1.5rem] border border-slate-200 bg-white/75 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.5)] dark:border-white/10 dark:bg-zinc-950/55">
            <p className="text-xs font-black uppercase tracking-[0.2em] text-slate-500 dark:text-slate-400">
              Board count
            </p>
            <p className="text-3xl font-black tracking-tighter">
              {isLoading ? "--" : games.length}
            </p>
            {hasStartedGames && (
              <div className="mt-3">
                <Switch isSelected={showScores} onChange={setShowScores}>
                  <span className="text-slate-950 dark:text-slate-50">
                    {showScores ? "Hide Scores" : "Show Scores"}
                  </span>
                </Switch>
              </div>
            )}
          </div>
        </div>

        {isLoading && (
          <div className="grid gap-4 md:grid-cols-3">
            <SkeletonBlock className="h-80 md:col-span-2" />
            <SkeletonBlock className="h-80" />
            <SkeletonBlock className="h-64" />
            <SkeletonBlock className="h-64 md:col-span-2" />
          </div>
        )}

        {error && (
          <DesignEmptyState
            title="Scores could not load"
            message={String(error)}
            className="border-rose-300 bg-rose-50 text-rose-900 dark:border-rose-300/25 dark:bg-rose-300/10 dark:text-rose-100"
          />
        )}

        {!isLoading && !error && games.length === 0 && (
          <DesignEmptyState
            title="No games on this date"
            message="Pick another day to rebuild the schedule wall with active matchups."
            actionTo="/designs/scorez-coverflow"
            actionLabel="Try coverflow"
          />
        )}

        {!isLoading && !error && games.length > 0 && (
          <MotionCascade className="grid gap-4 md:grid-cols-3">
            {games.map((game, index) => (
              <MasonryGameTile
                key={game.gameId}
                game={game}
                showScores={showScores}
                featured={index === 0 && game.gameStatus !== 1}
              />
            ))}
          </MotionCascade>
        )}
      </section>
    </StudioShell>
  );
}

export default ScorezMasonryDesign;
