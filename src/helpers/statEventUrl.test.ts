import {describe, expect, it} from "vitest";
import contract from "../../docs/verification/stat-event-links-2026-09-29/contract.json";
import type {StatEventMeasure, StatEvents} from "./statEventUrl";
import {buildStatEventUrl, STAT_EVENT_MEASURE_NAMES, statEventLabel, statEventUrl} from "./statEventUrl";

interface FixtureUrl {
  teamId: number;
  personId?: number;
  measure: string;
  value: number;
  url: string;
}

interface GameFixture {
  gameId: string;
  statEvents: StatEvents | null;
  cells: Record<"player" | "team", {linked: string[]; unlinked: string[]}>;
  urls: Record<"player" | "team", FixtureUrl[]>;
}

// Every per-game fixture generated from NBA.com's own link component.
const gameFixtures = Object.entries(
  import.meta.glob<GameFixture>("../../docs/verification/stat-event-links-2026-09-29/games/*.json", {eager: true, import: "default"}),
);

const isMeasure = (cell: string): cell is StatEventMeasure => cell in STAT_EVENT_MEASURE_NAMES;

const statEvents = contract.statEvents as StatEvents;
const {gameId, urls} = contract;

describe("stat event URLs", () => {
  it("matches NBA.com's player link byte for byte", () => {
    const {teamId, personId, measure, url} = urls.player;
    expect(statEventUrl({statEvents, gameId, teamId, personId, measure: measure as StatEventMeasure, value: 1})).toBe(url);
  });

  it("uses each measure's own flag", () => {
    const {teamId, personId, measure, url} = urls.playerNonShot;
    expect(statEventUrl({statEvents, gameId, teamId, personId, measure: measure as StatEventMeasure, value: 4})).toBe(url);
  });

  it("omits PlayerID for team totals", () => {
    const {teamId, measure, url} = urls.team;
    const built = statEventUrl({statEvents, gameId, teamId, measure: measure as StatEventMeasure, value: 40});
    expect(built).toBe(url);
    expect(built).not.toContain("PlayerID");
  });

  it("keeps empty parameters, encodes spaces as %20 and sorts keys", () => {
    const url = buildStatEventUrl({
      statEvents: {...statEvents, seasonType: "Pre Season"}, gameId: "0011700001", teamId: 1, personId: 2, measure: "FGA", flag: 2,
    });
    expect(url).toContain("?CFID=&CFPARAMS=&ContextMeasure=FGA&");
    expect(url).toContain("SeasonType=Pre%20Season");
    expect(url).not.toContain("+");
    const keys = new URL(url).search.slice(1).split("&").map((pair) => pair.split("=")[0]);
    expect(keys).toEqual([...keys].sort());
  });

  it("keeps an empty SeasonType for the NBA Cup final", () => {
    const url = buildStatEventUrl({statEvents: {...statEvents, seasonType: ""}, gameId: "0062500001", teamId: 1, measure: "FGM", flag: 3});
    expect(url).toContain("&SeasonType=&");
  });

  it("returns null for zero values, unlisted measures and games without statEvents", () => {
    const base = {gameId, teamId: 1, personId: 2};
    expect(statEventUrl({...base, statEvents, measure: "FGM", value: 0})).toBeNull();
    expect(statEventUrl({...base, statEvents: {...statEvents, measures: {FGM: 2}}, measure: "AST", value: 5})).toBeNull();
    expect(statEventUrl({...base, statEvents: null, measure: "FGM", value: 5})).toBeNull();
  });

  it("labels links with a readable possessive and measure name", () => {
    expect(statEventLabel("Julian Champagnie", "FGM")).toBe("View Julian Champagnie's field goals made on NBA.com, opens in new tab");
    expect(statEventLabel("San Antonio Spurs", "FG3A")).toBe("View San Antonio Spurs' three-pointers attempted on NBA.com, opens in new tab");
    expect(statEventLabel("Test Player", "TOV")).toBe("View Test Player's turnovers on NBA.com, opens in new tab");
  });

  it("loads every per-game fixture", () => {
    expect(gameFixtures).toHaveLength(11);
  });

  describe.each(gameFixtures)("fixture %s", (_path, fixture) => {
    const {gameId, statEvents, cells, urls} = fixture;

    it.each([...urls.player, ...urls.team].map((entry) => [entry.measure, entry.personId ?? "team", entry] as const))(
      "builds %s for %s byte for byte",
      (_measure, _subject, {teamId, personId, measure, value, url}) => {
        expect(isMeasure(measure)).toBe(true);
        const options = {gameId, teamId, personId, measure: measure as StatEventMeasure};
        expect(statEventUrl({...options, statEvents, value})).toBe(url);
        const flag = statEvents?.measures[measure as StatEventMeasure];
        expect(flag).toBeDefined();
        expect(buildStatEventUrl({...options, statEvents: statEvents!, flag: flag!})).toBe(url);
      },
    );

    it("links exactly the fixture's linked measures and leaves unlinked cells plain", () => {
      for (const kind of ["player", "team"] as const) {
        const sample = urls[kind][0] ?? {teamId: 1610612737, personId: kind === "player" ? 1 : undefined};
        const {teamId, personId} = sample;
        for (const cell of cells[kind].linked) {
          expect(isMeasure(cell)).toBe(true);
          expect(statEventUrl({statEvents, gameId, teamId, personId, measure: cell as StatEventMeasure, value: 5})).not.toBeNull();
        }
        // Unlinked cells that are link-capable measures elsewhere must stay plain
        // here; the rest (MIN, PTS, FT, percentages...) have no builder at all.
        for (const cell of cells[kind].unlinked.filter(isMeasure)) {
          expect(statEventUrl({statEvents, gameId, teamId, personId, measure: cell, value: 5})).toBeNull();
        }
        expect(Object.keys(statEvents?.measures ?? {}).sort()).toEqual([...cells[kind].linked].sort());
      }
    });
  });
});
