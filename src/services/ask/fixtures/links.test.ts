// Every internal link in the Ask fixtures must open a real page: the path must
// match a route in src/main.tsx, and series slugs must resolve through the same
// slug map SeriesDetail uses (src/utils/seriesSlug.ts).
import {describe, expect, it} from "vitest";
import {matchPath} from "react-router";
import mainSource from "@/main.tsx?raw";
import type {PlayoffBracketResponse, SeriesData} from "@/helpers/helpers";
import {buildPlayoffBracketModel} from "@/utils/playoffBracketModel";
import {buildSlugMap, yearToSeason} from "@/utils/seriesSlug";
import {ASK_RESPONSE_FIXTURES, ASK_SUGGEST_FIXTURES} from "@/services/ask/fixtures";

const ROUTES = [...mainSource.matchAll(/<Route path="(\/[^"]*)"/g)]
  .map(([, path]) => path)
  .filter(path => !path.startsWith("/original"));

function collectHrefs(node: unknown, out: string[] = []): string[] {
  if (Array.isArray(node)) node.forEach(child => collectHrefs(child, out));
  else if (node && typeof node === "object") {
    for (const [key, value] of Object.entries(node)) {
      if (key === "href" && typeof value === "string") out.push(value);
      else collectHrefs(value, out);
    }
  }
  return out;
}

// A modern 16-team bracket shaped like server/services/playoffs.py
// enrich_playoff_bracket_response output (bracketGroupId + bracketOrder).
function modernBracket(season: string): PlayoffBracketResponse {
  const series: SeriesData[] = [];
  let teamId = 1;
  const add = (round: number, group: string, order: number) => {
    const teams = [teamId++, teamId++].map(id => ({id, tricode: `T${id}`, name: `Team ${id}`}));
    series.push({
      seriesKey: `R${round}-${teams[0].id}-${teams[1].id}`,
      round,
      roundName: `Round ${round}`,
      bracketGroupId: group,
      bracketOrder: order,
      isFinals: round === 4,
      teams,
      wins: {},
      winnerTeamId: null,
      winnerTeamTricode: null,
      gameCount: 0,
      games: [],
    });
  };
  for (const [round, perConference] of [[1, 4], [2, 2], [3, 1]] as const) {
    for (const group of ["west-conference", "east-conference"]) {
      for (let order = 0; order < perConference; order++) add(round, group, order);
    }
  }
  add(4, "finals", 0);
  return {season, teamGameRowCount: 0, gameCount: 0, seriesCount: series.length, series};
}

const fixtures = {...ASK_RESPONSE_FIXTURES, ...ASK_SUGGEST_FIXTURES};
const internalLinks = Object.entries(fixtures).flatMap(([name, fixture]) =>
  collectHrefs(fixture).filter(href => href.startsWith("/")).map(href => [name, href] as const),
);

describe("Ask fixture links", () => {
  it("finds the app routes and some fixture links", () => {
    expect(ROUTES).toEqual(expect.arrayContaining(["/", "/playoffs", "/playoffs/:year/:seriesSlug", "/games/:gameId/boxscore"]));
    expect(internalLinks.some(([, href]) => /^\/playoffs\/\d{4}\//.test(href))).toBe(true);
  });

  it.each(internalLinks)("%s: %s opens a real page", (_name, href) => {
    const url = new URL(href, "https://app.test");
    const route = ROUTES.find(path => matchPath(path, url.pathname));
    expect(route, `no route for ${url.pathname}`).toBeDefined();

    const season = url.searchParams.get("season");
    if (season) expect(yearToSeason(String(Number(season.slice(0, 4)) + 1))).toBe(season);

    const params = matchPath("/playoffs/:year/:seriesSlug", url.pathname)?.params;
    if (params?.year && params.seriesSlug) {
      const slugs = buildSlugMap(buildPlayoffBracketModel(modernBracket(yearToSeason(params.year))).series);
      expect(slugs.has(params.seriesSlug), `unknown series slug ${params.seriesSlug}`).toBe(true);
    }
  });
});
