import {useEffect, useState} from "react";
import {Switch} from "@adobe/react-spectrum";
import {useQuery} from "@tanstack/react-query";
import {useSearchParams} from "react-router";
import GameDatePicker from "@/components/GameDatePicker";
import DesignEmptyState from "@/components/designs/patterns/DesignEmptyState";
import SkeletonBlock from "@/components/designs/patterns/SkeletonBlock";
import StudioShell from "@/components/designs/StudioShell";
import {getItem, setItem} from "@/helpers/helpers";
import {SCOREZ_PREVIEW_DATE} from "@/routes/designs/designDefaults";
import {getScores} from "@/services/nbaService";
import CoverflowGamePanel from "./CoverflowGamePanel";
import type {DesignScoreGame} from "./MasonryGameTile";

function ScorezCoverflowDesign() {
  const [searchParams, setSearchParams] = useSearchParams({date: ""});
  const dateParam = searchParams.get("date") || SCOREZ_PREVIEW_DATE;
  const [focusedGameId, setFocusedGameId] = useState<string | null>(null);
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
    queryKey: ["design-coverflow-games", dateParam],
    queryFn: () => getScores(dateParam) as Promise<{games: DesignScoreGame[]}>,
  });

  const games = data?.games ?? [];
  const focusedGame = games.find((game) => game.gameId === focusedGameId) ?? games[0];
  const hasStartedGames = games.some((game) => game.gameStatus !== 1);

  return (
    <StudioShell
      title="Coverflow Matchup Rail"
      eyebrow="Preview route /designs/scorez-coverflow"
      backTo="/"
      backLabel="Current Scorez"
      variant="studio"
      actions={<GameDatePicker />}
    >
      <section className="grid min-h-[70dvh] gap-6 md:grid-cols-[minmax(280px,0.75fr)_minmax(0,1.25fr)] md:items-center">
        <aside className="rounded-[2rem] border border-slate-200 bg-white/75 p-5 shadow-[0_24px_60px_-42px_rgba(2,132,199,0.45)] dark:border-white/10 dark:bg-zinc-950/62">
          <p className="text-xs font-black uppercase tracking-[0.24em] text-sky-700 dark:text-sky-300">
            Focus panel
          </p>
          <h2 className="mt-3 text-4xl font-black tracking-tighter">
            {focusedGame
              ? `${focusedGame.awayTeam.teamTricode} at ${focusedGame.homeTeam.teamTricode}`
              : "Awaiting schedule"}
          </h2>
          <p className="mt-4 text-base leading-relaxed text-slate-600 dark:text-slate-300">
            Scroll the rail to scan the slate. Hover or focus a panel to bring
            its matchup into the control surface.
          </p>
          <div className="mt-6 grid gap-3">
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 dark:border-white/10 dark:bg-white/5">
              <p className="text-xs font-black uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">
                Status
              </p>
              <p className="font-bold">
                {focusedGame?.gameStatusText ?? "No matchup selected"}
              </p>
            </div>
            {hasStartedGames && (
              <Switch isSelected={showScores} onChange={setShowScores}>
                <span className="text-slate-950 dark:text-slate-50">
                  {showScores ? "Hide Scores" : "Show Scores"}
                </span>
              </Switch>
            )}
          </div>
        </aside>

        <div className="min-w-0">
          {isLoading && (
            <div className="flex gap-4 overflow-hidden">
              <SkeletonBlock className="h-[420px] w-[78vw] shrink-0 md:w-[420px]" />
              <SkeletonBlock className="h-[420px] w-[78vw] shrink-0 md:w-[360px]" />
            </div>
          )}

          {error && (
            <DesignEmptyState
              title="Rail could not load"
              message={String(error)}
              className="border-sky-300 bg-sky-50 text-sky-900 dark:border-sky-300/25 dark:bg-sky-300/10 dark:text-sky-100"
            />
          )}

          {!isLoading && !error && games.length === 0 && (
            <DesignEmptyState
              title="No panels available"
              message="Select another date to fill the coverflow rail."
              actionTo="/designs/scorez-masonry"
              actionLabel="Open masonry wall"
            />
          )}

          {!isLoading && !error && games.length > 0 && (
            <div className="flex snap-x snap-mandatory gap-4 overflow-x-auto overflow-y-visible px-1 py-8">
              {games.map((game) => (
                <CoverflowGamePanel
                  key={game.gameId}
                  game={game}
                  showScores={showScores}
                  isFocused={(focusedGame?.gameId ?? games[0]?.gameId) === game.gameId}
                  onFocus={() => setFocusedGameId(game.gameId)}
                />
              ))}
            </div>
          )}
        </div>
      </section>
    </StudioShell>
  );
}

export default ScorezCoverflowDesign;
