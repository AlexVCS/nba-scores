import {describe, expect, it} from "vitest";
import type {TeamsInSeries} from "@/helpers/helpers";
import {bracketSizing} from "@/utils/bracketSizing";
import {transformToBracketData, type BracketNodeData} from "@/utils/bracketTransformer";
import type {PlayoffBracketModel, RenderSeries} from "@/utils/playoffBracketModel";

const westTeam = {id: 1, tricode: "DEN", name: "Nuggets"};
const eastTeam = {id: 2, tricode: "NYK", name: "Knicks"};
const opponent = {id: 3, tricode: "BOS", name: "Celtics"};

function series(
  seriesKey: string,
  round: number,
  bracketGroupId: "west-conference" | "east-conference" | "finals",
  teams: TeamsInSeries[],
  isFinals = false,
): RenderSeries {
  return {
    seriesKey,
    round,
    roundName: isFinals ? "NBA Finals" : `Round ${round}`,
    bracketGroupId,
    bracketGroupLabel: isFinals
      ? "NBA Finals"
      : bracketGroupId === "west-conference"
        ? "Western Conference"
        : "Eastern Conference",
    bracketGroupKind: isFinals ? "finals" : "conference",
    bracketOrder: 0,
    targetWins: 4,
    isFinals,
    teams,
    wins: {[teams[0].id]: 4, [teams[1].id]: 2},
    winnerTeamId: teams[0].id,
    winnerTeamTricode: teams[0].tricode,
    gameCount: 0,
    games: [],
  };
}

const modernModel: PlayoffBracketModel = {
  season: "2025-26",
  format: {
    era: "modern-play-in-era",
    playoffYear: 2026,
    finalsRound: 4,
    bracketType: "single-elimination",
    supportsExactBracket: true,
    notes: [],
  },
  groups: [
    {id: "west-conference", label: "Western Conference", kind: "conference", sortOrder: 10},
    {id: "east-conference", label: "Eastern Conference", kind: "conference", sortOrder: 20},
    {id: "finals", label: "NBA Finals", kind: "finals", sortOrder: 99},
  ],
  rounds: [
    {round: 1, label: "First Round", sortOrder: 1, defaultRevealed: true},
    {round: 2, label: "Conference Semifinals", sortOrder: 2, defaultRevealed: false},
    {round: 3, label: "Conference Finals", sortOrder: 3, defaultRevealed: false},
    {round: 4, label: "NBA Finals", sortOrder: 4, defaultRevealed: false},
  ],
  edges: [],
  series: [
    series("west-r1", 1, "west-conference", [westTeam, opponent]),
    series("west-r2", 2, "west-conference", [westTeam, opponent]),
    series("west-r3", 3, "west-conference", [westTeam, opponent]),
    series("east-r1", 1, "east-conference", [eastTeam, opponent]),
    series("east-r2", 2, "east-conference", [eastTeam, opponent]),
    series("east-r3", 3, "east-conference", [eastTeam, opponent]),
    series("finals", 4, "finals", [westTeam, eastTeam], true),
  ],
  fallbackMode: false,
};

describe("transformToBracketData", () => {
  const revealedRounds = new Set([1, 2, 3, 4]);

  it("omits round-name nodes but keeps both conference labels", () => {
    const {nodes} = transformToBracketData(modernModel, revealedRounds, "2025-26", bracketSizing.lg);

    expect(nodes.some(node => node.type === "roundLabel" || node.id.startsWith("round-label-"))).toBe(false);
    expect(nodes.filter(node => node.type === "conferenceLabel").map(node => node.data.label)).toEqual([
      "Western Conf.",
      "Eastern Conf.",
    ]);
  });

  it("keeps the conference branches mirrored around the centered Finals", () => {
    const {nodes} = transformToBracketData(modernModel, revealedRounds, "2025-26", bracketSizing.lg);
    const seriesNodes = nodes.filter(node => node.type === "seriesNode") as Array<{
      id: string;
      position: {x: number; y: number};
      data: BracketNodeData;
    }>;
    const westFirstRound = seriesNodes.find(node => node.id === "west-r1");
    const eastFirstRound = seriesNodes.find(node => node.id === "east-r1");
    const finals = seriesNodes.find(node => node.id === "finals");
    const westLabel = nodes.find(node => node.id === "group-label-west");
    const eastLabel = nodes.find(node => node.id === "group-label-east");

    expect(westFirstRound).toBeDefined();
    expect(eastFirstRound).toBeDefined();
    expect(finals).toBeDefined();

    const westCenter = westFirstRound!.position.x + westFirstRound!.data.displayWidth / 2;
    const eastCenter = eastFirstRound!.position.x + eastFirstRound!.data.displayWidth / 2;
    const finalsCenter = finals!.position.x + finals!.data.displayWidth / 2;

    expect(westFirstRound!.position.y).toBe(eastFirstRound!.position.y);
    expect(finalsCenter).toBe((westCenter + eastCenter) / 2);
    expect(westLabel?.position.x).toBe(westCenter);
    expect(eastLabel?.position.x).toBe(eastCenter);
  });
});
