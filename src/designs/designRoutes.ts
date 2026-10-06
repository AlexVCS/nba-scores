// Prefixes from when the designs were previewed side by side; links that still carry one resolve to the same page.
const LEGACY_DESIGN_PREFIX = /^\/(original|design-1)(?=\/|$)/;

export const stripDesignPrefix = (pathname: string): string => {
  const stripped = pathname.replace(LEGACY_DESIGN_PREFIX, "");
  return stripped.length === 0 ? "/" : stripped;
};

export const designPath = (_designId: "design-1", path: string): string => {
  if (/^(?:https?:)?\/\//.test(path)) return path;

  const [pathAndSearch, hash = ""] = path.split("#", 2);
  const [pathname, search = ""] = pathAndSearch.split("?", 2);
  const normalizedPath = pathname.startsWith("/") ? pathname : `/${pathname}`;
  return `${stripDesignPrefix(normalizedPath)}${search ? `?${search}` : ""}${hash ? `#${hash}` : ""}`;
};
