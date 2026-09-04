import {Eye, EyeOff, LockKeyhole, Trophy} from "lucide-react";
import {useBracketSeriesPath} from "@/components/bracketSeriesPath";
import useBaaBracketReveal from "@/hooks/useBaaBracketReveal";
import {getBaaBracketTopology} from "@/utils/baaBracketTopology";
import type {PlayoffBracketModel, RenderSeries} from "@/utils/playoffBracketModel";
import {buildSeriesSlug} from "@/utils/seriesSlug";
import BracketSeriesCard from "./BracketSeriesCard";

interface BaaPlayoffBracketProps {
  model: PlayoffBracketModel;
  forceShowAll: boolean;
}

function BaaPlayoffBracket({model, forceShowAll}: BaaPlayoffBracketProps) {
  const topology = getBaaBracketTopology(model);
  const reveal = useBaaBracketReveal(model, {forceShowAll});
  const buildSeriesPath = useBracketSeriesPath();
  if (!topology) return null;

  const renderSeries = (series: RenderSeries, title: string, position: string, prerequisite?: string) => {
    const available = reveal.canRevealSeries(series.seriesKey);
    const shown = reveal.revealedSeries.has(series.seriesKey);
    const Icon = shown ? EyeOff : Eye;
    return (
      <section className={`hw-baa-series hw-baa-series--${position}`} aria-label={title}>
        <h3 className="hw-baa-series-title">
          {series.isFinals ? <Trophy size={16} aria-hidden="true" /> : null}
          {title}
          {(position === "division" || position === "qualifier") && <span className="hw-baa-mobile-round">Semifinal</span>}
        </h3>
        {available || shown ? (
          <BracketSeriesCard
            series={series}
            href={buildSeriesPath(model.season, buildSeriesSlug(series, model.series))}
            isRevealed={shown}
            showFullNames
            className="hw-baa-card"
          />
        ) : (
          <div className="hw-baa-locked rounded-hw border border-dashed border-hw-bracket-line bg-hw-surface/85 text-hw-muted">
            <LockKeyhole size={18} aria-hidden="true" />
            <p>{series.isFinals ? "The two semifinal winners" : "The two quarterfinal winners"}</p>
            <p className="text-[10px] leading-4">Reveal {prerequisite} to see the matchup.</p>
          </div>
        )}
        {!forceShowAll && (
          <div className="hw-baa-series-control">
            {available || shown ? (
              <button
                type="button"
                onClick={() => shown ? reveal.hideSeries(series.seriesKey) : reveal.revealSeries(series.seriesKey)}
                aria-label={`${shown ? "Hide" : "Reveal"} ${title} results`}
                aria-pressed={shown}
                className="hw-baa-reveal"
              >
                <Icon size={14} aria-hidden="true" />
                <span className="hw-baa-reveal-desktop-copy">{shown ? "Hide results" : "Reveal results"}</span>
                <span className="hw-baa-reveal-mobile-copy">{shown ? "Hide results" : "Show results"}</span>
              </button>
            ) : <span className="text-[10px] text-hw-court">Waiting for {prerequisite}</span>}
          </div>
        )}
        {(position === "division" || position === "qualifier") && (
          <p className="hw-baa-mobile-destination">Winner advances to Finals</p>
        )}
      </section>
    );
  };

  return (
    <div className="hw-baa-bracket font-hw-display text-hw-ink">
      <p className="sr-only" role="status" aria-live="polite">{reveal.statusMessage}</p>
      {model.format.notes.length > 0 && (
        <p className="mx-auto mb-6 w-fit max-w-full rounded-hw border border-hw-line bg-hw-surface-muted px-4 py-3 text-center text-xs leading-5 text-hw-muted">
          {model.format.notes.join(" ").split(/\b(BAA)\b/).map((text, index) => text === "BAA" ? (
            <a
              key={index}
              href="https://en.wikipedia.org/wiki/Basketball_Association_of_America"
              title="Basketball Association of America"
              className="underline underline-offset-2 hover:text-hw-ink"
            >
              BAA
            </a>
          ) : text)}
        </p>
      )}
      {!forceShowAll && (
        <div className="mb-6 flex justify-center">
          <button
            type="button"
            onClick={reveal.revealedSeries.size ? reveal.hideAllResults : reveal.showAllResults}
            className="hw-baa-all-results min-h-11 rounded-hw border border-hw-line bg-hw-surface px-4 text-[10px] font-black tracking-[.1em] text-hw-accent-ink uppercase shadow-hw-small focus-visible:outline-3 focus-visible:outline-offset-3 focus-visible:outline-hw-accent dark:text-hw-accent"
          >
            {reveal.revealedSeries.size ? "Hide all results" : "Show all results"}
          </button>
        </div>
      )}
      <div className="hw-baa-tree">
        <div className="hw-baa-column-heading hw-baa-column-heading--quarters">Quarterfinals</div>
        <div className="hw-baa-column-heading hw-baa-column-heading--semis">Semifinals</div>
        <div className="hw-baa-column-heading hw-baa-column-heading--finals">Finals</div>
        <div className="hw-baa-connections hw-baa-connections--qualifiers" aria-hidden="true">
          <svg viewBox="0 0 48 520" preserveAspectRatio="none"><path d="M0 196 H24 V404 H0 M24 300 H48" /></svg>
        </div>
        <div className="hw-baa-connections hw-baa-connections--finals" aria-hidden="true">
          <svg viewBox="0 0 48 520" preserveAspectRatio="none"><path d="M0 92 H24 V300 H0 M24 196 H48" /></svg>
        </div>
        {renderSeries(topology.divisionWinner, "Division winners", "division")}
        {topology.quarterfinals.map((series, index) => (
          <div key={series.seriesKey} className={`hw-baa-quarter hw-baa-quarter--${index + 1}`}>
            {renderSeries(series, `Quarterfinal ${index + 1}`, "quarter")}
          </div>
        ))}
        {renderSeries(topology.qualifierSemifinal, "Other qualifiers", "qualifier", "both quarterfinals")}
        {renderSeries(topology.finals, "BAA Finals", "finals", "both semifinals")}
      </div>
    </div>
  );
}

export default BaaPlayoffBracket;
