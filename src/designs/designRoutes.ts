import type {DesignId} from "./types";
import {getDesignPreviewBasePath} from "./previewConfig";

const DESIGN_PREFIX = /^\/(original|design-[1-4])(?=\/|$)/;
const KNOWN_ROUTE = /^(?:\/$|\/games\/[^/]+\/boxscore\/?$|\/playoffs\/?$|\/playoffs\/\d{4}\/[^/]+\/?$)/;

export interface DesignLocation {
  pathname: string;
  search?: string;
  hash?: string;
}

export const detectDesignId = (pathname: string): DesignId => {
  const previewBasePath = getDesignPreviewBasePath(pathname);
  if (!previewBasePath) return "original";

  const previewPath = pathname.slice(previewBasePath.length) || "/";
  const match = previewPath.match(DESIGN_PREFIX);
  return match ? (match[1] as DesignId) : "original";
};

export const stripDesignPrefix = (pathname: string): string => {
  const previewBasePath = getDesignPreviewBasePath(pathname);
  const previewPath = previewBasePath
    ? pathname.slice(previewBasePath.length) || "/"
    : pathname;
  const stripped = previewPath.replace(DESIGN_PREFIX, "");
  return stripped.length === 0 ? "/" : stripped;
};

const currentPreviewBasePath = (): string => {
  const pathname = typeof window === "undefined" ? "" : window.location.pathname;
  const previewBasePath = getDesignPreviewBasePath(pathname);
  if (!previewBasePath) {
    throw new Error("Design links can only be built inside a preview route.");
  }
  return previewBasePath;
};

export const designPath = (designId: DesignId, path: string): string => {
  if (/^(?:https?:)?\/\//.test(path)) return path;

  const [pathAndSearch, hash = ""] = path.split("#", 2);
  const [pathname, search = ""] = pathAndSearch.split("?", 2);
  const normalizedPath = pathname.startsWith("/") ? pathname : `/${pathname}`;
  const unprefixedPath = stripDesignPrefix(normalizedPath);
  const prefix = `${currentPreviewBasePath()}/${designId}`;
  return `${prefix}${unprefixedPath}${search ? `?${search}` : ""}${hash ? `#${hash}` : ""}`;
};

export const buildDesignHref = (
  designId: DesignId,
  {pathname, search = "", hash = ""}: DesignLocation,
): string => {
  const unprefixedPath = stripDesignPrefix(pathname);
  const safePath = KNOWN_ROUTE.test(unprefixedPath) ? unprefixedPath : "/";
  const previewBasePath = getDesignPreviewBasePath(pathname);
  if (!previewBasePath) {
    throw new Error("Design links can only be built inside a preview route.");
  }
  const prefix = `${previewBasePath}/${designId}`;
  return `${prefix}${safePath}${search}${hash}`;
};
