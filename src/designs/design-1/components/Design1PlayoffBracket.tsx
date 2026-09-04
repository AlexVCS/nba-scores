/* Hallmark · pre-emit critique: P4 H4 E4 S5 R4 V4 */
import {useMemo, type ReactNode} from "react";
import MobileBracket from "@/components/MobileBracket";
import {useBracketSeriesPath} from "@/components/bracketSeriesPath";
import type {PlayoffBracketResponse, RoundDefinition} from "@/helpers/helpers";
import {useBracketReveal} from "@/hooks/useBracketReveal";
import useMediaQuery from "@/hooks/useMediaQuery";
import {useResultsVisibility} from "@/hooks/useResultsVisibility";
import {
  type BracketPresentationColumn,
  type BracketPresentationGroup,
  type BracketPresentationSlot,
  planBracketPresentation,
} from "@/utils/bracketPresentationPlanner";
import {buildPlayoffBracketModel} from "@/utils/playoffBracketModel";
import type {RenderSeries} from "@/utils/playoffBracketModel";
import {buildSeriesSlug} from "@/utils/seriesSlug";
import {getBaaBracketTopology} from "@/utils/baaBracketTopology";
import BaaPlayoffBracket from "./BaaPlayoffBracket";
import FinalsRoundHeader from "./FinalsRoundHeader";
import useDesktopBracketGeometry from "./useDesktopBracketGeometry";
import {bracketRow, bracketRowSeparation} from "./desktopBracketGeometry";
import {
  BracketSeriesCard,
  FinalsDestination,
  LockedSeriesSlot,
  RoundRevealButton,
} from "./bracketPrimitives";

interface Design1PlayoffBracketProps {
  playoffPicture: PlayoffBracketResponse;
}

interface RoundColumnProps {
  column: BracketPresentationColumn;
  season: string;
  revealedRounds: Set<number>;
  canRevealRound: (round: number) => boolean;
  revealRound: (round: number) => void;
  hideRound: (round: number) => void;
  previousRound?: RoundDefinition;
  allSeries: RenderSeries[];
  headingId: string;
  previousColumn?: BracketPresentationColumn;
  nextColumn?: BracketPresentationColumn;
  nextColumnIsFinals?: boolean;
  connectorSide?: "left" | "right";
  exactLayout?: boolean;
  suppressRevealControls: boolean;
}

interface ConnectorJunction {
  targetSeriesKey: string;
  sourceSlotIds: string[];
  startRow: number;
  endRow: number;
}

function slotsConnect(source: BracketPresentationSlot, target: BracketPresentationSlot) {
  return source.outgoingSeriesKeys.includes(target.id)
    && target.incomingSeriesKeys.includes(source.id);
}

function columnsConnect(sourceColumn?: BracketPresentationColumn, targetColumn?: BracketPresentationColumn) {
  if (!sourceColumn || !targetColumn) return false;
  return sourceColumn.slots.some(source => targetColumn.slots.some(target => slotsConnect(source, target)));
}

function RoundColumn({
  column,
  season,
  revealedRounds,
  canRevealRound,
  revealRound,
  hideRound,
  previousRound,
  allSeries,
  headingId,
  previousColumn,
  nextColumn,
  nextColumnIsFinals = false,
  connectorSide = "right",
  exactLayout = false,
  suppressRevealControls,
}: RoundColumnProps) {
  const buildSeriesPath = useBracketSeriesPath();
  const isRevealed = revealedRounds.has(column.round.round);
  const canReveal = canRevealRound(column.round.round);
  const previousSlotsById = new Map(previousColumn?.slots.map(slot => [slot.id, slot]) ?? []);
  const nextSlotsById = new Map(nextColumn?.slots.map(slot => [slot.id, slot]) ?? []);
  const junctionsByTarget = new Map<string, {target: BracketPresentationSlot; sources: BracketPresentationSlot[]}>();

  if (exactLayout && nextColumn) {
    for (const source of column.slots) {
      for (const targetSeriesKey of source.outgoingSeriesKeys) {
        const target = nextSlotsById.get(targetSeriesKey);
        if (!target || !slotsConnect(source, target)) continue;
        const junction = junctionsByTarget.get(targetSeriesKey) ?? {target, sources: []};
        junction.sources.push(source);
        junctionsByTarget.set(targetSeriesKey, junction);
      }
    }
  }

  const junctions: ConnectorJunction[] = [...junctionsByTarget.entries()].map(([targetSeriesKey, {target, sources}]) => {
    const targetRow = nextColumnIsFinals ? 4 : bracketRow(target.roundIndex, target.order);
    const rows = [targetRow, ...sources.map(source => bracketRow(source.roundIndex, source.order))];
    return {
      targetSeriesKey,
      sourceSlotIds: sources.map(source => source.id),
      startRow: Math.min(...rows),
      endRow: Math.max(...rows),
    };
  });
  const outgoingSlotIds = new Set(junctions.flatMap(junction => junction.sourceSlotIds));
  const incomingSlotIds = new Set(column.slots
    .filter(target => target.incomingSeriesKeys.some(sourceSeriesKey => {
      const source = previousSlotsById.get(sourceSeriesKey);
      return source ? slotsConnect(source, target) : false;
    }))
    .map(slot => slot.id));

  const connectorStubs = (slot: BracketPresentationSlot) => (
    <>
      {outgoingSlotIds.has(slot.id) ? (
        <span
          className={connectorSide === "left"
            ? "pointer-events-none absolute top-1/2 -left-3 z-0 w-3 border-t-2 border-hw-bracket-line"
            : "pointer-events-none absolute top-1/2 -right-3 z-0 w-3 border-t-2 border-hw-bracket-line"}
          aria-hidden="true"
        />
      ) : null}
      {incomingSlotIds.has(slot.id) ? (
        <span
          className={connectorSide === "left"
            ? "pointer-events-none absolute top-1/2 -right-3 z-0 w-3 border-t-2 border-hw-bracket-line"
            : "pointer-events-none absolute top-1/2 -left-3 z-0 w-3 border-t-2 border-hw-bracket-line"}
          aria-hidden="true"
        />
      ) : null}
    </>
  );

  return (
    <section
      className={`hw-bracket-round ${exactLayout ? "hw-bracket-round--exact" : "hw-bracket-round--fallback"}`}
      aria-labelledby={headingId}
    >
      <div className={`mb-4 flex ${suppressRevealControls ? "" : "min-h-[76px]"} min-w-0 flex-col items-center gap-2 border-b-[3px] border-hw-accent pb-3 text-center`}>
        <h3
          id={headingId}
          className="max-w-full text-[11px] leading-[1.35] font-black tracking-[.12em] text-hw-ink uppercase"
        >
          {column.round.label}
        </h3>
        {!suppressRevealControls && (
          <RoundRevealButton
            label={column.round.label}
            isRevealed={isRevealed}
            canReveal={canReveal}
            prerequisiteLabel={previousRound?.label}
            onReveal={() => revealRound(column.round.round)}
            onHide={() => hideRound(column.round.round)}
          />
        )}
      </div>

      {exactLayout ? (
        <div className="hw-bracket-measure" aria-hidden="true" {...{inert: ""}}>
          {column.slots.map(slot => (
            <BracketSeriesCard key={slot.id} series={slot.series} href="#" isRevealed />
          ))}
          {previousRound ? <LockedSeriesSlot roundLabel={column.round.label} prerequisiteLabel={previousRound.label} /> : null}
        </div>
      ) : null}

      <div className="hw-bracket-slots isolate">
        {junctions.map(junction => junction.startRow !== junction.endRow ? (
          <span
            key={junction.targetSeriesKey}
            className={connectorSide === "left"
              ? "pointer-events-none z-0 hw-bracket-junction col-start-1 w-0 -translate-x-3 justify-self-start border-l-2 border-hw-bracket-line"
              : "pointer-events-none z-0 hw-bracket-junction col-start-1 w-0 translate-x-3 justify-self-end border-l-2 border-hw-bracket-line"}
            style={{gridRow: `${junction.startRow} / ${junction.endRow + 1}`}}
            aria-hidden="true"
          />
        ) : null)}
        {!canReveal && !isRevealed ? (
          column.slots.map(slot => (
            <div
              key={slot.id}
              className="hw-bracket-slot z-[1]"
              style={exactLayout ? {gridRow: bracketRow(slot.roundIndex, slot.order)} : undefined}
            >
              {connectorStubs(slot)}
              <LockedSeriesSlot
                roundLabel={column.round.label}
                prerequisiteLabel={previousRound?.label}
              />
            </div>
          ))
        ) : (
          column.slots.map(slot => (
            <div
              key={slot.id}
              className="hw-bracket-slot z-[1]"
              style={exactLayout ? {gridRow: bracketRow(slot.roundIndex, slot.order)} : undefined}
            >
              {connectorStubs(slot)}
              <BracketSeriesCard
                series={slot.series}
                href={buildSeriesPath(season, buildSeriesSlug(slot.series, allSeries))}
                isRevealed={isRevealed}
              />
            </div>
          ))
        )}
      </div>
    </section>
  );
}

interface GroupBracketProps {
  plannedGroup: BracketPresentationGroup;
  season: string;
  rounds: RoundDefinition[];
  revealedRounds: Set<number>;
  canRevealRound: (round: number) => boolean;
  revealRound: (round: number) => void;
  hideRound: (round: number) => void;
  mirrored?: boolean;
  exactLayout?: boolean;
  connectToFinals?: boolean;
  finalsColumn?: BracketPresentationColumn;
  idPrefix: string;
  suppressRevealControls: boolean;
}

function GroupBracket({
  plannedGroup,
  season,
  rounds,
  revealedRounds,
  canRevealRound,
  revealRound,
  hideRound,
  mirrored = false,
  exactLayout = false,
  connectToFinals = false,
  finalsColumn,
  idPrefix,
  suppressRevealControls,
}: GroupBracketProps) {
  const previousRound = (round: number) => {
    const index = rounds.findIndex(item => item.round === round);
    return index > 0 ? rounds[index - 1] : undefined;
  };

  return (
    <section
      aria-labelledby={`${idPrefix}-group-${plannedGroup.group.id}`}
      className="min-w-0"
      style={exactLayout ? {gridColumn: `span ${plannedGroup.columns.length}`} : undefined}
    >
      <div className={`hw-bracket-group ${exactLayout ? "" : "hw-bracket-group--fallback"} ${mirrored && plannedGroup.side === "right" ? "hw-bracket-group--mirrored" : ""}`}>
        {plannedGroup.columns.map((column, index) => (
          <div key={column.round.round} className="min-w-0 [direction:ltr]">
            <div className="flex h-9 items-start justify-center text-center">
              {index === 0 ? (
                <h2
                  id={`${idPrefix}-group-${plannedGroup.group.id}`}
                  className="whitespace-nowrap text-xs font-black tracking-[.16em] text-black uppercase dark:text-white"
                >
                  {plannedGroup.group.label}
                </h2>
              ) : null}
            </div>
            <RoundColumn
              column={column}
              season={season}
              revealedRounds={revealedRounds}
              canRevealRound={canRevealRound}
              revealRound={revealRound}
              hideRound={hideRound}
              previousRound={previousRound(column.round.round)}
              allSeries={plannedGroup.columns.flatMap(item => item.slots.map(slot => slot.series))}
              headingId={`${idPrefix}-round-${plannedGroup.group.id}-${column.round.round}`}
              previousColumn={exactLayout ? plannedGroup.columns[index - 1] : undefined}
              nextColumn={exactLayout ? plannedGroup.columns[index + 1] ?? (connectToFinals ? finalsColumn : undefined) : undefined}
              nextColumnIsFinals={exactLayout && index === plannedGroup.columns.length - 1 && connectToFinals && Boolean(finalsColumn)}
              connectorSide={mirrored && plannedGroup.side === "right" ? "left" : "right"}
              exactLayout={exactLayout}
              suppressRevealControls={suppressRevealControls}
            />
          </div>
        ))}
      </div>
    </section>
  );
}

interface FinalsColumnProps {
  finalsContent: ReactNode;
  finalsRound?: RoundDefinition;
  finalsRevealed: boolean;
  finalsCanReveal: boolean;
  finalsPrerequisite?: RoundDefinition;
  revealRound: (round: number) => void;
  hideRound: (round: number) => void;
  incomingSides?: Array<"left" | "right">;
  idPrefix: string;
  suppressRevealControls: boolean;
}

function FinalsColumn({finalsContent, finalsRound, finalsRevealed, finalsCanReveal, finalsPrerequisite, revealRound, hideRound, incomingSides = [], idPrefix, suppressRevealControls}: FinalsColumnProps) {
  return (
    <section className="hw-bracket-round hw-bracket-round--exact hw-bracket-finals" aria-labelledby={`${idPrefix}-finals-heading`}>
      <FinalsRoundHeader
        headingId={`${idPrefix}-finals-heading`}
        finalsRound={finalsRound}
        finalsRevealed={finalsRevealed}
        finalsCanReveal={finalsCanReveal}
        finalsPrerequisite={finalsPrerequisite}
        revealRound={revealRound}
        hideRound={hideRound}
        suppressRevealControls={suppressRevealControls}
      />
      <div className="hw-bracket-measure" data-finals-measure aria-hidden="true" {...{inert: ""}}>
        <FinalsDestination isLocked prerequisiteLabel={finalsPrerequisite?.label} />
        <FinalsDestination isLocked={false}>{finalsContent}</FinalsDestination>
      </div>
      <div className="hw-bracket-slots">
        <div className="hw-bracket-slot z-[1]" style={{gridRow: 4}}>
          {incomingSides.includes("left") ? (
            <span className="pointer-events-none absolute top-1/2 -left-3 z-0 w-3 border-t-2 border-hw-bracket-line" aria-hidden="true" />
          ) : null}
          {incomingSides.includes("right") ? (
            <span className="pointer-events-none absolute top-1/2 -right-3 z-0 w-3 border-t-2 border-hw-bracket-line" aria-hidden="true" />
          ) : null}
          <FinalsDestination isLocked={!finalsCanReveal && !finalsRevealed} prerequisiteLabel={finalsPrerequisite?.label}>
            {finalsContent}
          </FinalsDestination>
        </div>
      </div>
    </section>
  );
}

function Design1PlayoffBracket({playoffPicture}: Design1PlayoffBracketProps) {
  const model = useMemo(() => buildPlayoffBracketModel(playoffPicture), [playoffPicture]);
  const plan = useMemo(() => planBracketPresentation(model), [model]);
  const rowSeparation = bracketRowSeparation(plan.groups.flatMap(group => group.columns.map(column => column.slots)));
  const {showAllResults: showAllResultsGlobally} = useResultsVisibility();
  const reveal = useBracketReveal(model, {forceShowAll: showAllResultsGlobally});
  const buildSeriesPath = useBracketSeriesPath();
  const finalsColumn = plan.finals?.columns[0];
  const finalsRound = finalsColumn?.round;
  const finalsRevealed = finalsRound ? reveal.revealedRounds.has(finalsRound.round) : false;
  const finalsCanReveal = finalsRound ? reveal.canRevealRound(finalsRound.round) : false;
  const finalsPrerequisite = finalsRound
    ? plan.rounds[plan.rounds.findIndex(round => round.round === finalsRound.round) - 1]
    : undefined;
  const anyRevealed = reveal.revealedRounds.size > 0;
  const usesExactTree = plan.exact && plan.mode === "mirrored";
  const usesCompactGroups = !usesExactTree && Boolean(finalsColumn)
    && plan.groups.length > 0 && plan.groups.length <= 2
    && plan.groups.every(group => group.columns.length === 1 && group.columns[0].slots.length <= 4);
  // Match the layout's CSS breakpoint, including compact historical brackets.
  const mountDesktop = useMediaQuery(usesCompactGroups ? "(min-width: 1100px)" : "(min-width: 1440px)");
  const bracketRef = useDesktopBracketGeometry(plan, rowSeparation, mountDesktop);
  const exactColumnCount = plan.groups.reduce((count, group) => count + group.columns.length, 1);
  const connectsGroupToFinals = (group?: BracketPresentationGroup) => {
    const sourceColumn = group ? group.columns[group.columns.length - 1] : undefined;
    return columnsConnect(sourceColumn, finalsColumn);
  };

  const finalsContent = finalsColumn?.slots.map(slot => (
    <BracketSeriesCard
      key={slot.id}
      series={slot.series}
      href={buildSeriesPath(model.season, buildSeriesSlug(slot.series, model.series))}
      isRevealed={finalsRevealed}
    />
  ));

  if (model.format.era === "baa-runners-up-bracket" && getBaaBracketTopology(model)) {
    return <BaaPlayoffBracket model={model} forceShowAll={showAllResultsGlobally} />;
  }

  return (
    <div className="hw-playoff-bracket font-hw-display text-hw-ink">
      <p className="sr-only" role="status" aria-live="polite">
        {reveal.statusMessage}
      </p>

        {plan.notice ? (
          <p className="mx-auto mb-6 w-fit max-w-full rounded-hw border border-hw-line bg-hw-surface-muted px-4 py-3 text-center text-xs leading-5 text-hw-muted">
            {plan.notice.split(/\b(BAA)\b/).map((text, index) => text === "BAA" ? (
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
        ) : null}

      <div className={usesCompactGroups ? "min-[1100px]:hidden" : "min-[1440px]:hidden"}>
        <MobileBracket
          model={model}
          revealedRounds={reveal.revealedRounds}
          revealRound={reveal.revealRound}
          hideRound={reveal.hideRound}
          canRevealRound={reveal.canRevealRound}
          revealThroughRound={reveal.revealThroughRound}
          showAllResults={reveal.showAllResults}
          hideAllResults={reveal.hideAllResults}
          suppressRevealControls={showAllResultsGlobally}
        />
      </div>

      {mountDesktop && <div ref={bracketRef} className={usesCompactGroups ? "hidden min-[1100px]:block" : "hidden min-[1440px]:block"}>
        {!showAllResultsGlobally && <div className="mb-6 flex justify-center">
            <button
              type="button"
              onClick={anyRevealed ? reveal.hideAllResults : reveal.showAllResults}
              className="min-h-11 rounded-hw border border-hw-line bg-hw-surface px-4 text-[10px] font-black tracking-[.1em] text-hw-accent-ink uppercase shadow-hw-small focus-visible:outline-3 focus-visible:outline-offset-3 focus-visible:outline-hw-accent dark:text-hw-accent"
            >
              {anyRevealed ? "Hide all results" : "Show all results"}
            </button>
        </div>}


        {!plan.hasSeries ? (
          <p className="rounded-hw bg-hw-surface p-6 text-center text-sm text-hw-muted shadow-hw-card">No bracket data is available for this season.</p>
        ) : (
          <>
            <div>
              {usesExactTree && plan.groups.length === 2 ? (
                <div
                  className="grid min-w-0 items-stretch justify-center gap-6 pb-4"
                  style={{gridTemplateColumns: `repeat(${exactColumnCount}, minmax(0, var(--hw-bracket-column-width)))`}}
                >
                  <GroupBracket
                    plannedGroup={plan.groups[0]}
                    season={model.season}
                    rounds={plan.rounds}
                    revealedRounds={reveal.revealedRounds}
                    canRevealRound={reveal.canRevealRound}
                    revealRound={reveal.revealRound}
                    hideRound={reveal.hideRound}
                    mirrored
                    exactLayout
                    connectToFinals={connectsGroupToFinals(plan.groups[0])}
                    finalsColumn={finalsColumn}
                    idPrefix="design-1-desktop-west"
                    suppressRevealControls={showAllResultsGlobally}
                  />
                  <FinalsColumn idPrefix="design-1-desktop" finalsContent={finalsContent} finalsRound={finalsRound} finalsRevealed={finalsRevealed} finalsCanReveal={finalsCanReveal} finalsPrerequisite={finalsPrerequisite} revealRound={reveal.revealRound} hideRound={reveal.hideRound} suppressRevealControls={showAllResultsGlobally} incomingSides={[
                    ...(connectsGroupToFinals(plan.groups[0]) ? ["left" as const] : []),
                    ...(connectsGroupToFinals(plan.groups[1]) ? ["right" as const] : []),
                  ]} />
                  <GroupBracket
                    plannedGroup={plan.groups[1]}
                    season={model.season}
                    rounds={plan.rounds}
                    revealedRounds={reveal.revealedRounds}
                    canRevealRound={reveal.canRevealRound}
                    revealRound={reveal.revealRound}
                    hideRound={reveal.hideRound}
                    mirrored
                    exactLayout
                    connectToFinals={connectsGroupToFinals(plan.groups[1])}
                    finalsColumn={finalsColumn}
                    idPrefix="design-1-desktop-east"
                    suppressRevealControls={showAllResultsGlobally}
                  />
                </div>
              ) : (
                <div className={usesCompactGroups ? "hw-bracket-compact" : "space-y-10"}>
                  <div className={usesCompactGroups ? "contents" : "flex flex-wrap items-start justify-center gap-10"}>
                    {plan.groups.map(group => (
                      <div key={group.group.id} className="overflow-x-auto pb-3">
                        <GroupBracket
                          plannedGroup={group}
                          season={model.season}
                          rounds={plan.rounds}
                          revealedRounds={reveal.revealedRounds}
                          canRevealRound={reveal.canRevealRound}
                          revealRound={reveal.revealRound}
                          hideRound={reveal.hideRound}
                          idPrefix={`design-1-desktop-${group.group.id}`}
                          suppressRevealControls={showAllResultsGlobally}
                        />
                      </div>
                    ))}
                  </div>
                  {finalsColumn ? (
                    <div className="hw-bracket-fallback-finals mx-auto">
                      <FinalsRoundHeader
                        headingId="design-1-desktop-finals-heading"
                        finalsRound={finalsRound}
                        finalsRevealed={finalsRevealed}
                        finalsCanReveal={finalsCanReveal}
                        finalsPrerequisite={finalsPrerequisite}
                        revealRound={reveal.revealRound}
                        hideRound={reveal.hideRound}
                        suppressRevealControls={showAllResultsGlobally}
                      />
                      <FinalsDestination isLocked={!finalsCanReveal && !finalsRevealed} prerequisiteLabel={finalsPrerequisite?.label}>
                        {finalsContent}
                      </FinalsDestination>
                    </div>
                  ) : null}
                </div>
              )}
            </div>
          </>
        )}
      </div>}
    </div>
  );
}

export default Design1PlayoffBracket;
