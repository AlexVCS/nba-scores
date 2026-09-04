import {describe, expect, it} from "vitest";
import type {BracketGroupKind, PlayoffFormat, TeamsInSeries} from "@/helpers/helpers";
import {planBracketPresentation} from "@/utils/bracketPresentationPlanner";
import type {PlayoffBracketModel, RenderSeries} from "@/utils/playoffBracketModel";

const bos = {id: 1, tricode: "BOS", name: "Celtics"};
const nyk = {id: 2, tricode: "NYK", name: "Knicks"};

function makeSeries(
  key: string,
  round: number,
  groupId: string,
  groupLabel: string,
  groupKind: BracketGroupKind,
  order = 0,
  teams: TeamsInSeries[] = [bos, nyk],
): RenderSeries {
  return {
    seriesKey: key,
    round,
    roundName: round === 4 ? "NBA Finals" : `Round ${round}`,
    bracketGroupId: groupId,
    bracketGroupLabel: groupLabel,
    bracketGroupKind: groupKind,
    bracketOrder: order,
    targetWins: 4,
    isFinals: groupKind === "finals",
    teams,
    wins: {},
    winnerTeamId: null,
    winnerTeamTricode: null,
    gameCount: 0,
    games: [],
  };
}

const modernFormat: PlayoffFormat = {
  era: "modern-play-in-era",
  playoffYear: 2026,
  finalsRound: 4,
  bracketType: "single-elimination",
  supportsExactBracket: true,
  notes: [],
};

function modernModel(): PlayoffBracketModel {
  return {
    season: "2025-26",
    format: modernFormat,
    groups: [
      {id: "west", label: "Western Conference", kind: "conference", sortOrder: 10},
      {id: "east", label: "Eastern Conference", kind: "conference", sortOrder: 20},
      {id: "finals", label: "NBA Finals", kind: "finals", sortOrder: 99},
    ],
    rounds: [
      {round: 1, label: "First Round", sortOrder: 1, defaultRevealed: true},
      {round: 2, label: "Conference Semifinals", sortOrder: 2, defaultRevealed: false},
      {round: 4, label: "NBA Finals", sortOrder: 4, defaultRevealed: false},
    ],
    series: [
      makeSeries("west-r1-b", 1, "west", "Western Conference", "conference", 1),
      makeSeries("west-r1-a", 1, "west", "Western Conference", "conference", 0),
      makeSeries("west-r2", 2, "west", "Western Conference", "conference"),
      makeSeries("east-r1", 1, "east", "Eastern Conference", "conference"),
      makeSeries("east-r2", 2, "east", "Eastern Conference", "conference"),
      makeSeries("finals", 4, "finals", "NBA Finals", "finals"),
    ],
    edges: [
      {sourceSeriesKey: "west-r1-a", targetSeriesKey: "west-r2", winnerTeamId: 1},
      {sourceSeriesKey: "west-r2", targetSeriesKey: "finals", winnerTeamId: 1},
      {sourceSeriesKey: "missing", targetSeriesKey: "finals", winnerTeamId: 1},
      {sourceSeriesKey: "finals", targetSeriesKey: "west-r1-a", winnerTeamId: 1},
    ],
    fallbackMode: false,
  };
}

describe("planBracketPresentation", () => {
  it("plans a modern bracket as mirrored branches with a shared Finals", () => {
    const plan = planBracketPresentation(modernModel());

    expect(plan.mode).toBe("mirrored");
    expect(plan.groups.map(group => [group.group.label, group.side])).toEqual([
      ["Western Conference", "left"],
      ["Eastern Conference", "right"],
    ]);
    expect(plan.groups[0].columns.map(column => column.round.label)).toEqual([
      "First Round",
      "Conference Semifinals",
    ]);
    expect(plan.groups[0].columns[0].slots.map(slot => slot.id)).toEqual([
      "west-r1-a",
      "west-r1-b",
    ]);
    expect(plan.finals?.columns[0].slots[0].incomingSeriesKeys).toEqual(["west-r2"]);
    expect(plan.trustedEdges).toHaveLength(2);
  });

  it("uses actual division labels and supports a league-only chronological layout", () => {
    const division = modernModel();
    division.format = {...modernFormat, era: "eight-team-division", bracketType: "multi-division"};
    division.groups[0] = {...division.groups[0], id: "west-division", label: "Western Division", kind: "division"};
    division.groups[1] = {...division.groups[1], id: "east-division", label: "Eastern Division", kind: "division"};
    division.series = division.series.map(item => item.bracketGroupId === "west"
      ? {...item, bracketGroupId: "west-division", bracketGroupLabel: "Western Division", bracketGroupKind: "division"}
      : item.bracketGroupId === "east"
        ? {...item, bracketGroupId: "east-division", bracketGroupLabel: "Eastern Division", bracketGroupKind: "division"}
        : item);

    expect(planBracketPresentation(division).groups.map(group => group.group.label)).toEqual([
      "Western Division",
      "Eastern Division",
    ]);

    const league: PlayoffBracketModel = {
      ...modernModel(),
      groups: [{id: "league", label: "League Bracket", kind: "league", sortOrder: 1}],
      series: [makeSeries("league-r1", 1, "league", "League Bracket", "league")],
      edges: [],
    };
    const leaguePlan = planBracketPresentation(league);
    expect(leaguePlan.mode).toBe("league");
    expect(leaguePlan.groups.map(group => group.group.label)).toEqual(["League Bracket"]);
    expect(leaguePlan.finals).toBeNull();
  });

  it("uses a ledger for inexact history and never invents or accepts invalid edges", () => {
    const model = modernModel();
    model.format = {
      era: "six-team-round-robin",
      playoffYear: 1954,
      finalsRound: 4,
      bracketType: "round-robin-plus-finals",
      supportsExactBracket: false,
      notes: ["Division round-robin format."],
    };

    const plan = planBracketPresentation(model);
    expect(plan.mode).toBe("ledger");
    expect(plan.exact).toBe(false);
    expect(plan.notice).toBe("In 1954, each division opened with a three-team round robin. The top two teams advanced to the division finals.");
    expect(plan.trustedEdges.map(edge => edge.sourceSeriesKey)).toEqual(["west-r1-a", "west-r2"]);

    model.fallbackMode = true;
    expect(planBracketPresentation(model).trustedEdges).toEqual([]);
  });

  it("omits absent rounds from asymmetric groups without moving their original round positions", () => {
    const model = modernModel();
    model.series = model.series.filter(series => series.seriesKey !== "east-r1");
    const plan = planBracketPresentation(model);
    expect(plan.mode).toBe("mirrored");
    expect(plan.groups.map(group => group.columns.length)).toEqual([2, 1]);
    expect(plan.groups[1].columns[0].round.round).toBe(2);
    expect(plan.groups[1].columns[0].slots[0].roundIndex).toBe(1);
    expect(plan.groups[0].columns[0].slots[0].outgoingSeriesKeys).toEqual(["west-r2"]);
    expect(plan.groups[0].columns[1].slots[0].incomingSeriesKeys).toEqual(["west-r1-a"]);
    expect(plan.groups[0].columns[1].slots[0].outgoingSeriesKeys).toEqual(["finals"]);
    expect(plan.trustedEdges).toHaveLength(2);
    expect(plan.rounds).toEqual(model.rounds);
  });

  it("keeps recorded bye slots and result-hidden series", () => {
    const model = modernModel();
    model.series[0] = {...model.series[0], teams: [], isByePlaceholder: true};
    const plan = planBracketPresentation(model);
    const firstRound = plan.groups[0].columns[0];
    expect(firstRound.slots).toHaveLength(2);
    expect(firstRound.slots.find(slot => slot.id === "west-r1-b")?.isBye).toBe(true);
    expect(firstRound.slots.find(slot => slot.id === "west-r1-a")?.series.winnerTeamId).toBeNull();
  });

  it("handles empty and incomplete models without synthetic slots", () => {
    const empty: PlayoffBracketModel = {
      season: "1946-47",
      format: {...modernFormat, era: "unknown", finalsRound: null},
      groups: [],
      rounds: [],
      edges: [{sourceSeriesKey: "missing-a", targetSeriesKey: "missing-b", winnerTeamId: null}],
      series: [],
      fallbackMode: true,
    };
    const emptyPlan = planBracketPresentation(empty);
    expect(emptyPlan.mode).toBe("empty");
    expect(emptyPlan.hasSeries).toBe(false);
    expect(emptyPlan.groups).toEqual([]);

    const incomplete = modernModel();
    incomplete.series = incomplete.series.filter(item => item.seriesKey === "west-r1-a");
    incomplete.edges = [];
    const incompletePlan = planBracketPresentation(incomplete);
    expect(incompletePlan.mode).toBe("grouped");
    expect(incompletePlan.groups.map(group => group.group.id)).toEqual(["west"]);
    expect(incompletePlan.groups[0].columns.map(column => column.round.round)).toEqual([1]);
    expect(incompletePlan.finals).toBeNull();
  });
});

it("explains the early BAA routes without missing-record caveats or empty rounds", () => {
  const model = modernModel();
  model.format = {...modernFormat, era: "baa-runners-up-bracket", supportsExactBracket: false,
    notes: ["Division winners played each other for one Finals spot. The second- and third-place teams played two rounds for the other."]};
  model.series = model.series.filter(series => series.seriesKey !== "east-r1");
  const plan = planBracketPresentation(model);
  expect(plan.notice).toBe(model.format.notes[0]);
  expect(plan.groups[1].columns.map(column => column.round.round)).toEqual([2]);
});
