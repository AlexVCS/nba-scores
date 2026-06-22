import {useEffect, useMemo, useState} from "react";
import {Switch} from "@adobe/react-spectrum";
import {Link, useSearchParams} from "react-router";
import PlayoffYearPicker from "@/components/PlayoffYearPicker";
import MotionCascade from "@/components/designs/motion/MotionCascade";
import DesignEmptyState from "@/components/designs/patterns/DesignEmptyState";
import SkeletonBlock from "@/components/designs/patterns/SkeletonBlock";
import StudioShell from "@/components/designs/StudioShell";
import {usePlayoffData} from "@/hooks/usePlayoffData";
import {PLAYOFF_PREVIEW_SEASON} from "@/routes/designs/designDefaults";
import {
  buildPlayoffBracketModel,
  canRevealRound as canRevealRoundFromModel,
} from "@/utils/playoffBracketModel";
import TransitRoundColumn from "./TransitRoundColumn";

function PlayoffzMapDesign() {
  const [searchParams, setSearchParams] = useSearchParams();
  const seasonParam = searchParams.get("season");
  const [season, setSeason] = useState<string | null>(seasonParam);
  const [revealedRounds, setRevealedRounds] = useState<Set<number>>(new Set());
  const [activeGroupId, setActiveGroupId] = useState<string>("");

  useEffect(() => {
    setSeason(seasonParam || PLAYOFF_PREVIEW_SEASON);
  }, [seasonParam]);

  useEffect(() => {
    if (!seasonParam) {
      setSearchParams({season: PLAYOFF_PREVIEW_SEASON}, {replace: true});
    }
  }, [seasonParam, setSearchParams]);

  const {data, isLoading, error} = usePlayoffData(season);
  const model = useMemo(() => (data ? buildPlayoffBracketModel(data) : null), [data]);
  const visibleGroups = useMemo(
    () =>
      model
        ? model.groups.filter((group) =>
            model.series.some((seriesItem) => seriesItem.bracketGroupId === group.id),
          )
        : [],
    [model],
  );

  useEffect(() => {
    if (!model) return;
    setRevealedRounds(
      new Set(
        model.rounds
          .filter((round) => round.defaultRevealed)
          .map((round) => round.round),
      ),
    );
  }, [model]);

  useEffect(() => {
    if (!activeGroupId && visibleGroups[0]) {
      setActiveGroupId(visibleGroups[0].id);
    }
  }, [activeGroupId, visibleGroups]);

  const activeGroup = visibleGroups.find((group) => group.id === activeGroupId) ?? visibleGroups[0];

  const revealRound = (round: number) => {
    setRevealedRounds((prev) => new Set([...prev, round]));
  };

  const hideRound = (round: number) => {
    setRevealedRounds((prev) => {
      const next = new Set(prev);
      for (const item of next) {
        if (item >= round) next.delete(item);
      }
      return next;
    });
  };

  return (
    <StudioShell
      title="Tournament Transit Map"
      eyebrow="Preview route /designs/playoffz-map"
      backTo="/playoffs"
      backLabel="Current Playoffz"
      variant="analytics"
      actions={<PlayoffYearPicker />}
    >
      <section className="grid gap-6 lg:grid-cols-[280px_minmax(0,1fr)]">
        <aside className="rounded-[2rem] border border-emerald-200 bg-emerald-50/70 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.65)] dark:border-emerald-300/15 dark:bg-emerald-300/10">
          <p className="text-xs font-black uppercase tracking-[0.24em] text-emerald-800 dark:text-emerald-200">
            Reveal rail
          </p>
          <p className="mt-3 text-base leading-relaxed text-slate-700 dark:text-slate-300">
            Each switch opens the next transfer point on the postseason map.
          </p>
          <div className="mt-5 grid gap-3">
            {model?.rounds.map((roundDef) => {
              const canReveal = canRevealRoundFromModel(
                roundDef.round,
                model.rounds,
                revealedRounds,
              );
              if (!canReveal) return null;
              const isRevealed = revealedRounds.has(roundDef.round);
              return (
                <Switch
                  key={roundDef.round}
                  isSelected={isRevealed}
                  onChange={(selected) =>
                    selected ? revealRound(roundDef.round) : hideRound(roundDef.round)
                  }
                >
                  <span className="text-slate-950 dark:text-slate-50">
                    {isRevealed ? `Hide ${roundDef.label}` : `Show ${roundDef.label}`}
                  </span>
                </Switch>
              );
            })}
          </div>
        </aside>

        <div className="min-w-0 rounded-[2rem] border border-slate-200 bg-[#fbfaf4]/85 p-4 shadow-[0_24px_70px_-48px_rgba(16,185,129,0.5)] dark:border-white/10 dark:bg-slate-950/70 sm:p-5">
          <div className="mb-5 flex flex-wrap items-center justify-between gap-3 border-b border-emerald-200 pb-4 dark:border-emerald-300/15">
            <div>
              <h2 className="text-3xl font-black tracking-tighter">
                {season ?? "Loading"} route map
              </h2>
              <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
                Select a line, then open a stop for the split-feature series route.
              </p>
            </div>
            <Link
              to="/designs/playoffz"
              className="rounded-full border border-emerald-300 px-4 py-2 text-sm font-black uppercase tracking-[0.16em] text-emerald-900 hover:bg-emerald-100 active:scale-[0.98] dark:border-emerald-300/20 dark:text-emerald-100 dark:hover:bg-emerald-300/10"
            >
              Control room
            </Link>
          </div>

          {isLoading && (
            <div className="grid gap-4 md:grid-cols-3">
              <SkeletonBlock className="h-96" />
              <SkeletonBlock className="h-96" />
              <SkeletonBlock className="h-96" />
            </div>
          )}
          {error && (
            <DesignEmptyState
              title="Transit map could not load"
              message={String(error)}
              className="border-emerald-300 bg-emerald-50 text-emerald-950 dark:border-emerald-300/25 dark:bg-emerald-300/10 dark:text-emerald-100"
            />
          )}
          {!isLoading && !error && model && activeGroup && (
            <>
              <div className="mb-5 flex gap-2 overflow-x-auto pb-1">
                {visibleGroups.map((group) => (
                  <button
                    key={group.id}
                    onClick={() => setActiveGroupId(group.id)}
                    className={`shrink-0 rounded-full border px-4 py-2 text-sm font-black uppercase tracking-[0.16em] transition-colors active:scale-[0.98] ${
                      activeGroup.id === group.id
                        ? "border-emerald-700 bg-emerald-700 text-white dark:border-emerald-300 dark:bg-emerald-300 dark:text-slate-950"
                        : "border-emerald-300 text-emerald-900 hover:bg-emerald-100 dark:border-emerald-300/20 dark:text-emerald-100 dark:hover:bg-emerald-300/10"
                    }`}
                  >
                    {group.kind === "finals"
                      ? "Finals"
                      : group.label.replace(" Conference", "").replace(" Division", "")}
                  </button>
                ))}
              </div>

              <MotionCascade className="grid gap-6 md:grid-flow-col md:auto-cols-[minmax(270px,1fr)] md:overflow-x-auto md:pb-4">
                {model.rounds
                  .filter((round) =>
                    canRevealRoundFromModel(round.round, model.rounds, revealedRounds),
                  )
                  .map((round) => {
                    const roundSeries = model.series
                      .filter(
                        (seriesItem) =>
                          seriesItem.bracketGroupId === activeGroup.id &&
                          seriesItem.round === round.round,
                      )
                      .sort((a, b) => a.bracketOrder - b.bracketOrder);
                    if (roundSeries.length === 0) return null;
                    return (
                      <TransitRoundColumn
                        key={`${activeGroup.id}-${round.round}`}
                        roundName={round.label}
                        series={roundSeries}
                        allSeries={model.series}
                        season={model.season}
                        isRevealed={revealedRounds.has(round.round)}
                      />
                    );
                  })}
              </MotionCascade>
            </>
          )}
        </div>
      </section>
    </StudioShell>
  );
}

export default PlayoffzMapDesign;
