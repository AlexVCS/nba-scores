import {useEffect, useMemo, useRef, useState} from "react";
import type {PlayoffBracketModel, RenderSeries} from "@/utils/playoffBracketModel";
import MobileSeriesCard from "./MobileSeriesCard";

interface MobileBracketProps {
  model: PlayoffBracketModel;
  revealedRounds: Set<number>;
  revealRound: (round: number) => void;
  hideRound: (round: number) => void;
  canRevealRound: (round: number) => boolean;
  revealThroughRound: (round: number) => void;
  showAllResults: () => void;
  hideAllResults: () => void;
  suppressRevealControls?: boolean;
}

function roundSectionId(season: string, round: number) {
  return `mobile-bracket-${season}-${round}`;
}

function MobileBracket({
  model,
  revealedRounds,
  revealRound,
  hideRound,
  canRevealRound,
  revealThroughRound,
  showAllResults,
  hideAllResults,
  suppressRevealControls = false,
}: MobileBracketProps) {
  const roundsWithSeries = useMemo(
    () => model.rounds.filter(round => model.series.some(series => series.round === round.round)),
    [model.rounds, model.series]
  );
  const [currentRound, setCurrentRound] = useState(roundsWithSeries[0]?.round ?? 0);
  const sectionRefs = useRef(new Map<number, HTMLElement>());

  useEffect(() => {
    setCurrentRound(roundsWithSeries[0]?.round ?? 0);
  }, [model.season, roundsWithSeries]);

  useEffect(() => {
    const sections = [...sectionRefs.current.values()];
    if (sections.length === 0) return;
    const observer = new IntersectionObserver(entries => {
      const nearest = entries
        .filter(entry => entry.isIntersecting)
        .sort((a, b) => Math.abs(a.boundingClientRect.top) - Math.abs(b.boundingClientRect.top))[0];
      if (nearest) setCurrentRound(Number((nearest.target as HTMLElement).dataset.round));
    }, {rootMargin: "-96px 0px -55% 0px", threshold: 0});
    sections.forEach(section => observer.observe(section));
    return () => observer.disconnect();
  }, [model.season, roundsWithSeries]);

  const jumpToRound = (round: number) => {
    sectionRefs.current.get(round)?.scrollIntoView({behavior: "smooth", block: "start"});
    setCurrentRound(round);
  };

  const toggleRound = (round: number) => {
    if (revealedRounds.has(round)) {
      hideRound(round);
      return;
    }
    revealRound(round);
  };

  const showLockedRound = (round: number) => {
    revealThroughRound(round);
    requestAnimationFrame(() => jumpToRound(round));
  };

  const handleGlobalResults = () => {
    const firstRound = roundsWithSeries[0];
    if (!firstRound) return;
    if (revealedRounds.size > 0) {
      hideAllResults();
    } else {
      showAllResults();
    }
    jumpToRound(firstRound.round);
  };

  return (
    <div className="mobile-bracket pb-8">
      <nav className="mobile-bracket__round-rail sticky top-0 z-[100] -mx-1 mb-5 overflow-x-auto border-b border-hw-line bg-hw-page! px-1" aria-label="Playoff rounds">
        <div className="flex w-max min-w-full justify-center gap-2 py-2">
          {roundsWithSeries.map(round => {
            const isLocked = !canRevealRound(round.round);
            return (
              <button key={round.round} type="button" onClick={() => jumpToRound(round.round)}
                className={`mobile-bracket__round-jump flex min-h-11 flex-col items-center justify-center rounded-lg border px-3 text-xs font-extrabold uppercase tracking-wider focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-hw-accent ${currentRound === round.round ? "mobile-bracket__round-jump--current" : ""} ${isLocked ? "mobile-bracket__round-jump--locked border-hw-line! bg-hw-surface-muted! text-hw-muted! opacity-100!" : currentRound === round.round ? "border-hw-accent! bg-hw-accent! text-hw-accent-contrast!" : "border-hw-line! bg-hw-surface! text-hw-muted!"}`}
                aria-current={currentRound === round.round ? "location" : undefined}
                aria-controls={roundSectionId(model.season, round.round)}>
                <span>{round.label}</span>
                {isLocked && <span className="text-[10px] font-semibold normal-case tracking-normal">Results hidden</span>}
              </button>
            );
          })}
        </div>
      </nav>

      {!suppressRevealControls && <div className="mb-4 flex justify-center">
        <button type="button" onClick={handleGlobalResults} className="mobile-bracket__hide-all min-h-11 px-3 text-xs font-extrabold uppercase tracking-wider focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-hw-accent">
          {revealedRounds.size > 0 ? "Hide all results" : "Show all results"}
        </button>
      </div>}

      <div className="flex flex-col gap-7">
        {roundsWithSeries.map((round, roundIndex) => {
          const isLocked = !canRevealRound(round.round);
          const isRevealed = revealedRounds.has(round.round);
          const previousRound = roundsWithSeries[roundIndex - 1];
          const hiddenPrerequisites = roundsWithSeries
            .slice(0, roundIndex)
            .filter(item => !revealedRounds.has(item.round));
          const groups = model.groups.map(group => ({
            ...group,
            series: model.series.filter(series => series.round === round.round && series.bracketGroupId === group.id).sort((a, b) => a.bracketOrder - b.bracketOrder),
          })).filter(group => group.series.length > 0);

          return (
            <section key={round.round} id={roundSectionId(model.season, round.round)} data-round={round.round}
              ref={element => { if (element) sectionRefs.current.set(round.round, element); else sectionRefs.current.delete(round.round); }}
              className={`mobile-bracket__round scroll-mt-20 ${isLocked ? "mobile-bracket__round--locked" : ""}`}
              aria-labelledby={`${roundSectionId(model.season, round.round)}-heading`}>
              <div className="mobile-bracket__round-header mb-3 flex items-center justify-between gap-3">
                <h2 id={`${roundSectionId(model.season, round.round)}-heading`} className="text-sm font-extrabold uppercase tracking-wider">{round.label}</h2>
                {!suppressRevealControls && !isLocked && <button type="button" onClick={() => toggleRound(round.round)}
                  className={`mobile-bracket__reveal min-h-11 shrink-0 rounded-lg px-3 text-xs font-extrabold uppercase tracking-wider focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-hw-accent ${isRevealed ? "mobile-bracket__reveal--hide" : ""}`}
                  aria-pressed={isRevealed}>{isRevealed ? "Hide results" : "Show results"}</button>}
              </div>

              {isLocked ? (
                <div className="rounded-xl border border-hw-line bg-hw-surface/80 p-3 shadow-hw-small">
                  <div className="mb-4 flex items-start justify-between gap-3">
                    <p className="self-center text-sm font-extrabold leading-tight">This round's results are hidden</p>
                    <button
                      type="button"
                      onClick={() => showLockedRound(round.round)}
                      className="min-h-11 shrink-0 rounded-lg bg-hw-accent px-3 text-[10px] font-extrabold uppercase tracking-wider text-hw-accent-contrast shadow-hw-small focus-visible:outline-3 focus-visible:outline-offset-3 focus-visible:outline-hw-accent"
                      aria-label={`Show ${hiddenPrerequisites.map(item => item.label).join(" and ")} results to unlock ${round.label}`}
                    >
                      Show results
                    </button>
                  </div>

                  <div className="flex flex-col gap-5" aria-label={`${round.label} matchup placeholders`}>
                    {groups.map(group => (
                      <div key={group.id}>
                        <h3 className="mb-2 text-[10px] font-extrabold uppercase tracking-widest text-hw-muted">
                          {group.kind === "finals" ? "NBA Finals" : group.label}
                        </h3>
                        <div className="flex flex-col gap-2">
                          {group.series.map((series, seriesIndex) => (
                            <div
                              key={series.seriesKey}
                              className="grid min-h-20 grid-cols-[1fr_auto_1fr] items-center gap-3 rounded-xl border border-hw-line bg-hw-surface-muted px-3 py-3"
                              aria-label={`Hidden matchup ${seriesIndex + 1} of ${group.series.length}`}
                            >
                              <div className="flex items-center justify-end gap-2" aria-hidden="true">
                                <span className="h-3 w-16 max-w-[45%] rounded bg-hw-line" />
                                <span className="size-9 rounded-full border border-hw-line bg-hw-surface" />
                              </div>
                              <span className="flex size-11 items-center justify-center rounded-lg border border-hw-line text-[10px] font-extrabold uppercase tracking-wider text-hw-muted" aria-hidden="true">VS</span>
                              <div className="flex items-center gap-2" aria-hidden="true">
                                <span className="size-9 rounded-full border border-hw-line bg-hw-surface" />
                                <span className="h-3 w-16 max-w-[45%] rounded bg-hw-line" />
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                  <p className="sr-only">Choose Show results to reveal {previousRound?.label ?? "earlier round"} results and unlock these matchups.</p>
                </div>
              ) : (
                <div className="flex flex-col gap-5">
                  {groups.map(group => <div key={group.id} className="mobile-bracket__group">
                    <h3 className="mobile-bracket__group-label mb-2 text-[11px] font-extrabold uppercase tracking-widest">{group.kind === "finals" ? "NBA Finals" : group.label}</h3>
                    <div className="flex flex-col gap-2">
                      {group.series.map((series: RenderSeries) => <MobileSeriesCard key={series.seriesKey} series={series} allSeries={model.series} season={model.season} isRevealed={isRevealed} />)}
                    </div>
                  </div>)}
                </div>
              )}
            </section>
          );
        })}
      </div>
    </div>
  );
}

export default MobileBracket;
