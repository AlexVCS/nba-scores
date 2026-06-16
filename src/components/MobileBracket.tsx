import { useState, useEffect, useRef } from 'react';
import type { SeriesData } from '@/helpers/helpers';
import { groupSeriesByConference } from '@/utils/bracketTransformer';
import MobileSeriesCard from './MobileSeriesCard';

type ConferenceTab = 'West' | 'East' | 'Finals';

interface MobileBracketProps {
  playoffPicture: SeriesData[];
  season: string;
  revealedRounds: Set<number>;
  revealRound: (round: number) => void;
  hideRound: (round: number) => void;
  canRevealRound: (round: number) => boolean;
}

const TABS: { key: ConferenceTab; label: string }[] = [
  { key: 'West', label: 'Western' },
  { key: 'East', label: 'Eastern' },
  { key: 'Finals', label: 'Finals' },
];

function RoundSection({
  roundName,
  series,
  allSeries,
  season,
  isRevealed,
  onToggle,
}: {
  round: number;
  roundName: string;
  series: SeriesData[];
  allSeries: SeriesData[];
  season: string;
  isRevealed: boolean;
  onToggle: () => void;
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
          />
        ))}
      </div>
      {showScrollHint && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 flex items-center gap-2 px-4 py-2 rounded-full bg-gray-800 border border-gray-600 shadow-lg z-50 pointer-events-none">
          <span className="animate-bounce text-base leading-none">🏀</span>
          <span className="text-xs text-gray-200 whitespace-nowrap">scroll for more</span>
        </div>
      )}
    </div>
  );
}

function MobileBracket({
  playoffPicture,
  season,
  revealedRounds,
  revealRound,
  hideRound,
  canRevealRound,
}: MobileBracketProps) {
  const [activeTab, setActiveTab] = useState<ConferenceTab>('West');
  const [isStuck, setIsStuck] = useState(false);
  const sentinelRef = useRef<HTMLDivElement>(null);
  const { east, west, finals } = groupSeriesByConference(playoffPicture);
  const showFinalsTab = canRevealRound(4);

  useEffect(() => {
    if (!showFinalsTab && activeTab === 'Finals') {
      setActiveTab('West');
    }
  }, [showFinalsTab, activeTab]);

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

  const renderConference = (confSeries: SeriesData[]) => {
    const rounds = [...new Set(confSeries.map(s => s.round))].sort((a, b) => a - b);
    const visibleRounds = rounds.filter(r => canRevealRound(r));

    return (
      <div className="flex flex-col gap-6">
        {visibleRounds.map(round => {
          const roundSeries = confSeries.filter(s => s.round === round);
          const roundName = roundSeries[0]?.roundName ?? `Round ${round}`;
          return (
            <RoundSection
              key={round}
              round={round}
              roundName={roundName}
              series={roundSeries}
              allSeries={playoffPicture}
              season={season}
              isRevealed={revealedRounds.has(round)}
              onToggle={() =>
                revealedRounds.has(round) ? hideRound(round) : revealRound(round)
              }
            />
          );
        })}
      </div>
    );
  };

  const renderFinals = () => {
    if (!canRevealRound(4)) {
      return (
        <p className="text-sm text-gray-400 text-center py-6">
          Reveal Conference Finals results to unlock the NBA Finals
        </p>
      );
    }
    if (finals.length === 0) {
      return (
        <p className="text-sm text-gray-400 text-center py-6">
          NBA Finals matchup not yet set
        </p>
      );
    }
    const roundName = finals[0].roundName;
    const isRevealed = revealedRounds.has(4);
    return (
      <RoundSection
        round={4}
        roundName={roundName}
        series={finals}
        allSeries={playoffPicture}
        season={season}
        isRevealed={isRevealed}
        onToggle={() => (isRevealed ? hideRound(4) : revealRound(4))}
      />
    );
  };

  return (
    <div className="pb-8">
      <div ref={sentinelRef} className="h-0" />
      <div className={`flex border-b-2 border-gray-700 mb-5 sticky top-0 z-10 transition-colors duration-150 ${isStuck ? 'bg-gray-900' : ''}`}>
        {TABS.filter(({ key }) => key !== 'Finals' || showFinalsTab).map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={`flex-1 py-2 text-sm font-semibold transition-colors duration-150 ${
              activeTab === key
                ? 'text-amber-500 border-b-2 border-amber-500 -mb-0.5'
                : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {activeTab === 'West' && renderConference(west)}
      {activeTab === 'East' && renderConference(east)}
      {activeTab === 'Finals' && renderFinals()}
    </div>
  );
}

export default MobileBracket;
