const EXPECTED_PREVIEW_TOKEN_HASH =
  "cfcc8fa8464d1544ba966069dff47f20fb1eca9d6cd4e657b5f2fc292c912b73";
const PREVIEW_BASE_PATTERN = /^(\/preview\/[^/]+)(?=\/|$)/;

export const DESIGN_PREVIEW_ROUTE_PATH = "/preview/:previewToken";

export const getDesignPreviewBasePath = (pathname: string): string | null =>
  pathname.match(PREVIEW_BASE_PATTERN)?.[1] ?? null;

const sha256 = async (value: string): Promise<string> => {
  const bytes = new TextEncoder().encode(value);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
};

export const isValidDesignPreviewToken = async (
  token: string,
  expectedHash = EXPECTED_PREVIEW_TOKEN_HASH,
): Promise<boolean> => {
  if (!/^[A-Za-z0-9_-]{32,}$/.test(token)) return false;
  return (await sha256(token)) === expectedHash;
};
