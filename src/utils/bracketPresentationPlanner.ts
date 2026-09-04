import type {BracketEdge, BracketGroup, RoundDefinition} from "@/helpers/helpers";
import type {PlayoffBracketModel, RenderSeries} from "@/utils/playoffBracketModel";

export type BracketPresentationMode = "mirrored" | "grouped" | "league" | "ledger" | "empty";
export type BracketSide = "left" | "right" | "center";

export interface BracketPresentationSlot {
  id: string;
  series: RenderSeries;
  groupId: string;
  round: number;
  roundIndex: number;
  order: number;
  isBye: boolean;
  incomingSeriesKeys: string[];
  outgoingSeriesKeys: string[];
}

export interface BracketPresentationColumn {
  round: RoundDefinition;
  slots: BracketPresentationSlot[];
}

export interface BracketPresentationGroup {
  group: BracketGroup;
  side: BracketSide;
  columns: BracketPresentationColumn[];
}

export interface BracketPresentationPlan {
  mode: BracketPresentationMode;
  exact: boolean;
  notice: string | null;
  groups: BracketPresentationGroup[];
  finals: BracketPresentationGroup | null;
  trustedEdges: BracketEdge[];
  rounds: RoundDefinition[];
  hasSeries: boolean;
}

const ROUND_ROBIN_NOTICE = "In 1954, each division opened with a three-team round robin. The top two teams advanced to the division finals.";

function orderedRounds(model: PlayoffBracketModel): RoundDefinition[] {
  return [...model.rounds].sort((a, b) => a.sortOrder - b.sortOrder || a.round - b.round);
}

function orderedGroups(model: PlayoffBracketModel): BracketGroup[] {
  return [...model.groups].sort((a, b) => a.sortOrder - b.sortOrder || a.label.localeCompare(b.label));
}

function trustedEdges(model: PlayoffBracketModel): BracketEdge[] {
  // Legacy models may contain edges inferred from winners. They are useful to the old
  // renderer, but are not authoritative enough for a historical presentation plan.
  if (model.fallbackMode) return [];

  const seriesByKey = new Map(model.series.map(series => [series.seriesKey, series]));
  const seen = new Set<string>();

  return model.edges.filter(edge => {
    const source = seriesByKey.get(edge.sourceSeriesKey);
    const target = seriesByKey.get(edge.targetSeriesKey);
    const identity = `${edge.sourceSeriesKey}:${edge.targetSeriesKey}`;
    if (!source || !target || source.round >= target.round || seen.has(identity)) return false;
    seen.add(identity);
    return true;
  });
}

function makeSlot(
  series: RenderSeries,
  roundIndex: number,
  edges: BracketEdge[],
): BracketPresentationSlot {
  return {
    id: series.seriesKey,
    series,
    groupId: series.bracketGroupId,
    round: series.round,
    roundIndex,
    order: series.bracketOrder,
    isBye: series.isByePlaceholder === true,
    incomingSeriesKeys: edges
      .filter(edge => edge.targetSeriesKey === series.seriesKey)
      .map(edge => edge.sourceSeriesKey),
    outgoingSeriesKeys: edges
      .filter(edge => edge.sourceSeriesKey === series.seriesKey)
      .map(edge => edge.targetSeriesKey),
  };
}

function planGroup(
  group: BracketGroup,
  side: BracketSide,
  rounds: RoundDefinition[],
  series: RenderSeries[],
  edges: BracketEdge[],
): BracketPresentationGroup {
  const groupSeries = series.filter(item => item.bracketGroupId === group.id);

  return {
    group,
    side,
    columns: rounds.map((round, roundIndex) => ({
      round,
      slots: groupSeries
        .filter(item => item.round === round.round)
        .sort((a, b) => a.bracketOrder - b.bracketOrder || a.seriesKey.localeCompare(b.seriesKey))
        .map(item => makeSlot(item, roundIndex, edges)),
    })).filter(column => column.slots.length > 0),
  };
}

function isMirroredPair(groups: BracketGroup[], model: PlayoffBracketModel): boolean {
  if (groups.length !== 2) return false;
  const supportedKind = groups[0].kind === "conference" || groups[0].kind === "division";
  return supportedKind
    && groups[0].kind === groups[1].kind
    && groups.every(group => model.series.some(series => series.bracketGroupId === group.id));
}

function presentationMode(
  model: PlayoffBracketModel,
  nonFinalGroups: BracketGroup[],
  finalsGroup: BracketGroup | undefined,
): BracketPresentationMode {
  if (model.series.length === 0) return "empty";
  if (!model.format.supportsExactBracket) return "ledger";
  if (finalsGroup && isMirroredPair(nonFinalGroups, model)) return "mirrored";
  if (nonFinalGroups.length === 1 && nonFinalGroups[0].kind === "league") return "league";
  return "grouped";
}

export function planBracketPresentation(model: PlayoffBracketModel): BracketPresentationPlan {
  const rounds = orderedRounds(model);
  const groups = orderedGroups(model).filter(group => model.series.some(series =>
    series.bracketGroupId === group.id && rounds.some(round => round.round === series.round),
  ));
  const finalsGroup = groups.find(group => group.kind === "finals");
  const nonFinalGroups = groups.filter(group => group.kind !== "finals");
  const edges = trustedEdges(model);
  const mode = presentationMode(model, nonFinalGroups, finalsGroup);
  const finalsRoundNumbers = new Set(
    model.series.filter(series => series.isFinals).map(series => series.round),
  );
  const branchRounds = rounds.filter(round => !finalsRoundNumbers.has(round.round));
  const finalRounds = rounds.filter(round => finalsRoundNumbers.has(round.round));

  const plannedGroups = nonFinalGroups.map((group, index) => planGroup(
    group,
    mode === "mirrored" ? (index === 0 ? "left" : "right") : "center",
    branchRounds,
    model.series,
    edges,
  ));
  const finals = finalsGroup
    ? planGroup(finalsGroup, "center", finalRounds, model.series, edges)
    : null;

  const isEarlyBaa = model.format.era === "baa-runners-up-bracket";

  return {
    mode,
    exact: model.format.supportsExactBracket && !model.fallbackMode,
    notice: model.format.era === "six-team-round-robin"
      ? ROUND_ROBIN_NOTICE
      : model.format.era === "three-division-transitional"
      ? "This season used three divisions. We show how teams advanced where historical records are clear."
      : isEarlyBaa
      ? model.format.notes.join(" ")
      : model.format.supportsExactBracket
      ? (model.fallbackMode ? model.format.notes[0] ?? "Legacy bracket metadata" : null)
      : model.format.notes.join(" ") || null,
    groups: plannedGroups.filter(group => group.columns.length > 0),
    finals: finals?.columns.length ? finals : null,
    trustedEdges: edges,
    rounds,
    hasSeries: model.series.length > 0,
  };
}
