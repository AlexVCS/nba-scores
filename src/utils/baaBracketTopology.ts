import type {BracketEdge} from "@/helpers/helpers";
import type {PlayoffBracketModel, RenderSeries} from "@/utils/playoffBracketModel";

export interface BaaBracketTopology {
  divisionWinner: RenderSeries;
  quarterfinals: RenderSeries[];
  qualifierSemifinal: RenderSeries;
  finals: RenderSeries;
  edges: BracketEdge[];
}

/**
 * The 1947 and 1948 formats have two independent routes to the Finals.
 * Wire their known stages, without consulting results or participant identities.
 * https://en.wikipedia.org/wiki/1947_BAA_playoffs
 * https://en.wikipedia.org/wiki/1948_BAA_playoffs
 * An incomplete or differently shaped response stays in the existing renderer.
 */
export function getBaaBracketTopology(model: PlayoffBracketModel): BaaBracketTopology | null {
  if (model.format.era !== "baa-runners-up-bracket"
    || ![1947, 1948].includes(model.format.playoffYear)
    || model.series.length !== 5
    || new Set(model.series.map(series => series.seriesKey)).size !== 5) return null;

  const divisionWinners = model.series.filter(series => series.bracketGroupId === "division-winners" && series.round === 2 && !series.isFinals);
  const quarterfinals = model.series
    .filter(series => series.bracketGroupId === "other-qualifiers" && series.round === 1 && !series.isFinals)
    .sort((a, b) => a.bracketOrder - b.bracketOrder || a.seriesKey.localeCompare(b.seriesKey));
  const qualifierSemifinals = model.series.filter(series => series.bracketGroupId === "other-qualifiers" && series.round === 2 && !series.isFinals);
  const finalSeries = model.series.filter(series => series.isFinals && series.round === 3);
  if (divisionWinners.length !== 1 || quarterfinals.length !== 2
    || qualifierSemifinals.length !== 1 || finalSeries.length !== 1) return null;

  const divisionWinner = divisionWinners[0];
  const qualifierSemifinal = qualifierSemifinals[0];
  const finals = finalSeries[0];
  const edge = (source: RenderSeries, target: RenderSeries): BracketEdge => ({
    sourceSeriesKey: source.seriesKey,
    targetSeriesKey: target.seriesKey,
    winnerTeamId: null,
  });

  return {
    divisionWinner,
    quarterfinals,
    qualifierSemifinal,
    finals,
    edges: [
      ...quarterfinals.map(series => edge(series, qualifierSemifinal)),
      edge(divisionWinner, finals),
      edge(qualifierSemifinal, finals),
    ],
  };
}
