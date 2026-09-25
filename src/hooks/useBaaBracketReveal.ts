import {useCallback, useEffect, useMemo, useState} from "react";
import {getBaaBracketTopology} from "@/utils/baaBracketTopology";
import type {PlayoffBracketModel} from "@/utils/playoffBracketModel";

const HIDDEN_STATUS = "Results are hidden until you choose to reveal them.";

interface RevealState {
  season: string;
  series: Set<string>;
  statusMessage: string;
}

interface BaaBracketRevealOptions {
  forceShowAll?: boolean;
}

/** Early BAA paths advance independently, so spoiler dependencies follow series edges. */
function useBaaBracketReveal(
  model: PlayoffBracketModel,
  {forceShowAll = false}: BaaBracketRevealOptions = {},
) {
  const [state, setState] = useState<RevealState>({
    season: model.season,
    series: new Set(),
    statusMessage: HIDDEN_STATUS,
  });
  const seriesByKey = useMemo(
    () => new Map(model.series.map(series => [series.seriesKey, series])),
    [model.series],
  );
  const topology = useMemo(() => getBaaBracketTopology(model), [model]);
  const incoming = useMemo(() => {
    const dependencies = new Map<string, string[]>();
    topology?.edges.forEach(edge => {
      const keys = dependencies.get(edge.targetSeriesKey) ?? [];
      keys.push(edge.sourceSeriesKey);
      dependencies.set(edge.targetSeriesKey, keys);
    });
    return dependencies;
  }, [topology]);
  const revealedSeries = useMemo(
    () => forceShowAll ? new Set(seriesByKey.keys())
      : state.season === model.season ? state.series : new Set<string>(),
    [forceShowAll, model.season, seriesByKey, state],
  );

  useEffect(() => {
    setState(previous => previous.season === model.season && !forceShowAll
      ? previous
      : {season: model.season, series: new Set(), statusMessage: HIDDEN_STATUS});
  }, [forceShowAll, model.season]);

  const canRevealSeries = useCallback((key: string) => (
    topology !== null && seriesByKey.has(key) && (forceShowAll || (incoming.get(key) ?? []).every(source => revealedSeries.has(source)))
  ), [forceShowAll, incoming, revealedSeries, seriesByKey, topology]);

  const revealSeries = useCallback((key: string) => {
    const series = seriesByKey.get(key);
    if (forceShowAll || !series || !topology) return;
    setState(previous => {
      const shown = previous.season === model.season ? previous.series : new Set<string>();
      if (!(incoming.get(key) ?? []).every(source => shown.has(source))) return previous;
      return {
        season: model.season,
        series: new Set([...shown, key]),
        statusMessage: `${series.isFinals ? series.roundName : `${series.bracketGroupLabel} ${series.roundName}`} results revealed.`,
      };
    });
  }, [forceShowAll, incoming, model.season, seriesByKey, topology]);

  const hideSeries = useCallback((key: string) => {
    const series = seriesByKey.get(key);
    if (forceShowAll || !series || !topology) return;
    const hidden = new Set([key]);
    const pending = [key];
    while (pending.length > 0) {
      const source = pending.pop();
      topology?.edges.forEach(edge => {
        if (edge.sourceSeriesKey === source && !hidden.has(edge.targetSeriesKey)) {
          hidden.add(edge.targetSeriesKey);
          pending.push(edge.targetSeriesKey);
        }
      });
    }
    setState(previous => ({
      season: model.season,
      series: new Set([...(previous.season === model.season ? previous.series : [])]
        .filter(shown => !hidden.has(shown))),
      statusMessage: `${series.isFinals ? series.roundName : `${series.bracketGroupLabel} ${series.roundName}`} and dependent results are hidden.`,
    }));
  }, [forceShowAll, model.season, seriesByKey, topology]);

  const showAllResults = useCallback(() => {
    if (forceShowAll) return;
    setState({season: model.season, series: new Set(seriesByKey.keys()), statusMessage: "All playoff results are shown."});
  }, [forceShowAll, model.season, seriesByKey]);

  const hideAllResults = useCallback(() => {
    if (forceShowAll) return;
    setState({season: model.season, series: new Set(), statusMessage: "All playoff results are hidden."});
  }, [forceShowAll, model.season]);

  return {
    revealedSeries,
    canRevealSeries,
    revealSeries,
    hideSeries,
    showAllResults,
    hideAllResults,
    statusMessage: forceShowAll ? "All playoff results are shown."
      : state.season === model.season ? state.statusMessage : HIDDEN_STATUS,
  };
}

export default useBaaBracketReveal;
