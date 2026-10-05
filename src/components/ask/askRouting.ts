import {designPath} from "@/designs/designRoutes";
import type {AskAppRoute, AskClientContext} from "@/services/ask/types";

const DESIGN_PREFIX = /^\/(original|design-1)(?=\/|$)/;

/** Server links are design-agnostic app paths. Keep the user inside the design they are viewing. */
export function withDesignPrefix(href: string, pathname: string): string {
  if (!href.startsWith("/")) return href;
  const match = pathname.match(DESIGN_PREFIX);
  return match ? designPath(match[1] as "original" | "design-1", href) : href;
}

/** Page context sent with a question so "this game" or "these playoffs" can resolve. */
export function askClientContext(pathname: string, search: string): AskClientContext {
  const path = pathname.replace(DESIGN_PREFIX, "") || "/";
  const params = new URLSearchParams(search);
  const date = params.get("date");
  const viewDate = date && /^\d{4}-\d{2}-\d{2}$/.test(date) ? date : null;
  const boxscore = path.match(/^\/games\/(\d{10})\/boxscore/);
  const series = path.match(/^\/playoffs\/(\d{4})\//);
  const season = params.get("season");

  let route: AskAppRoute = "other";
  if (path === "/") route = "scores";
  else if (boxscore) route = "boxscore";
  else if (series) route = "series";
  else if (/^\/playoffs\/?$/.test(path)) route = "playoffs";

  const seriesYear = series ? Number(series[1]) : null;
  return {
    route,
    view_date: viewDate,
    game_id: boxscore?.[1] ?? null,
    playoff_season: season && /^\d{4}-\d{2}$/.test(season)
      ? season
      : seriesYear ? `${seriesYear - 1}-${String(seriesYear).slice(-2)}` : null,
  };
}
