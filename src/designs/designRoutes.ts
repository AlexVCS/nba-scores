import type {DesignId} from "./types";

const DESIGN_PREFIX = /^\/(original|design-1)(?=\/|$)/;
const KNOWN_ROUTE = /^(?:\/$|\/games\/[^/]+\/boxscore\/?$|\/playoffs\/?$|\/playoffs\/\d{4}\/[^/]+\/?$)/;

export interface DesignLocation {
  pathname: string;
  search?: string;
  hash?: string;
}

export const detectDesignId = (pathname: string): DesignId => {
  const match = pathname.match(DESIGN_PREFIX);
  return match ? (match[1] as DesignId) : "original";
};

export const stripDesignPrefix = (pathname: string): string => {
  const stripped = pathname.replace(DESIGN_PREFIX, "");
  return stripped.length === 0 ? "/" : stripped;
};

export const designPath = (designId: DesignId, path: string): string => {
  if (/^(?:https?:)?\/\//.test(path)) return path;

  const [pathAndSearch, hash = ""] = path.split("#", 2);
  const [pathname, search = ""] = pathAndSearch.split("?", 2);
  const normalizedPath = pathname.startsWith("/") ? pathname : `/${pathname}`;
  const unprefixedPath = stripDesignPrefix(normalizedPath);
  const prefix = `/${designId}`;
  return `${prefix}${unprefixedPath === "/" ? "" : unprefixedPath}${search ? `?${search}` : ""}${hash ? `#${hash}` : ""}`;
};

export const buildDesignHref = (
  designId: DesignId,
  {pathname, search = "", hash = ""}: DesignLocation,
): string => {
  const unprefixedPath = stripDesignPrefix(pathname);
  const safePath = KNOWN_ROUTE.test(unprefixedPath) ? unprefixedPath : "/";
  return designPath(designId, `${safePath}${search}${hash}`);
};
