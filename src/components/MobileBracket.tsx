import { useState, useEffect, useMemo, useRef } from 'react';
import type { BracketGroup } from '@/helpers/helpers';
import type { PlayoffBracketModel, RenderSeries } from '@/utils/playoffBracketModel';
import MobileSeriesCard from './MobileSeriesCard';

interface MobileBracketProps {
  model: PlayoffBracketModel;
  revealedRounds: Set<number>;
  revealRound: (round: number) => void;
  hideRound: (round: number) => void;
  canRevealRound: (round: number) => boolean;
  seriesRouteBase?: 'production' | 'design';
}

function RoundSection({
  roundName,
  series,
  allSeries,
  season,
  isRevealed,
  onToggle,
  seriesRouteBase = 'production',
}: {
  round: number;
  roundName: string;
  series: RenderSeries[];
  allSeries: RenderSeries[];
  season: string;
  isRevealed: boolean;
  onToggle: () => void;
  seriesRouteBase?: 'production' | 'design';
}) {
  const canScrollForMore = series.length > 1;
  const [showScrollHint, setShowScrollHint] = useState(false);
  const prevRevealedRef = useRef(isRevealed);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!prevRevealedRef.current && isRevealed && canScrollForMore) {
      setShowScrollHint(true);
      timerRef.current = setTimeout(() => setShowScrollHint(false), 2500);
    }
    prevRevealedRef.current = isRevealed;
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [isRevealed, canScrollForMore]);

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-bold uppercase tracking-widest text-gray-400">
          {roundName}
        </span>
        <button
          onClick={onToggle}
          className="text-xs text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 border border-gray-400 dark:border-gray-600 hover:border-gray-600 dark:hover:border-gray-400 rounded px-2 py-0.5 transition-colors duration-150"
        >
          {isRevealed ? 'Hide results' : 'Show results'}
        </button>
      </div>
      <div className="flex flex-col gap-2">
        {series.map(s => (
          <MobileSeriesCard
            key={s.seriesKey}
            series={s}
            allSeries={allSeries}
            season={season}
            isRevealed={isRevealed}
            seriesRouteBase={seriesRouteBase}
          />
        ))}
      </div>
      {showScrollHint && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 flex items-center gap-2 px-4 py-2 rounded-full bg-gray-800 border border-gray-600 shadow-lg z-50 pointer-events-none">
          <span className="text-xs text-gray-200 whitespace-nowrap">scroll for more</span>
        </div>
      )}
    </div>
  );
}

function MobileBracket({
  model,
  revealedRounds,
  revealRound,
  hideRound,
  canRevealRound,
  seriesRouteBase = 'production',
}: MobileBracketProps) {
  const visibleGroups = useMemo(
    () => model.groups.filter(group => model.series.some(series => series.bracketGroupId === group.id)),
    [model.groups, model.series]
  );
  const [activeGroupId, setActiveGroupId] = useState(visibleGroups[0]?.id ?? '');
  const [isStuck, setIsStuck] = useState(false);
  const sentinelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!visibleGroups.some(group => group.id === activeGroupId)) {
      setActiveGroupId(visibleGroups[0]?.id ?? '');
    }
  }, [activeGroupId, visibleGroups]);

  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!sentinel) return;
    const observer = new IntersectionObserver(
      ([entry]) => setIsStuck(!entry.isIntersecting),
      { threshold: 0 }
    );
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, []);

  const renderGroup = (group: BracketGroup) => {
    const groupSeries = model.series.filter(series => series.bracketGroupId === group.id);
    const visibleRounds = model.rounds.filter(round =>
      canRevealRound(round.round) && groupSeries.some(series => series.round === round.round)
    );

    if (visibleRounds.length === 0) {
      return (
        <p className="text-sm text-gray-400 text-center py-6">
          Reveal earlier results to unlock this round.
        </p>
      );
    }

    return (
      <div className="flex flex-col gap-6">
        {visibleRounds.map(round => {
          const roundSeries = groupSeries
            .filter(series => series.round === round.round)
            .sort((a, b) => a.bracketOrder - b.bracketOrder);
          return (
            <RoundSection
              key={round.round}
              round={round.round}
              roundName={round.label}
              series={roundSeries}
              allSeries={model.series}
              season={model.season}
              isRevealed={revealedRounds.has(round.round)}
              onToggle={() =>
                revealedRounds.has(round.round) ? hideRound(round.round) : revealRound(round.round)
              }
              seriesRouteBase={seriesRouteBase}
            />
          );
        })}
      </div>
    );
  };

  const activeGroup = visibleGroups.find(group => group.id === activeGroupId) ?? visibleGroups[0];

  return (
    <div className="pb-8">
      <div ref={sentinelRef} className="h-0" />
      <div className={`flex overflow-x-auto border-b-2 border-gray-700 mb-5 sticky top-0 z-10 transition-colors duration-150 ${isStuck ? 'bg-gray-900' : ''}`}>
        {visibleGroups.map(group => (
          <button
            key={group.id}
            onClick={() => setActiveGroupId(group.id)}
            className={`min-w-fit flex-1 px-3 py-2 text-sm font-semibold transition-colors duration-150 ${
              activeGroup?.id === group.id
                ? 'text-amber-500 border-b-2 border-amber-500 -mb-0.5'
                : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            {group.kind === 'finals' ? 'Finals' : group.label.replace(' Conference', '').replace(' Division', '')}
          </button>
        ))}
      </div>

      {activeGroup && renderGroup(activeGroup)}
    </div>
  );
}

export default MobileBracket;
