// Contract fixtures for building the Ask UI without a backend.
// Validated against the pydantic models by server/tests/ask/test_contract_fixtures.py.
import type {AskResponse, AskSuggestResponse} from "@/services/ask/types";

const responseModules = import.meta.glob<AskResponse>("./responses/*.json", {eager: true, import: "default"});
const suggestModules = import.meta.glob<AskSuggestResponse>("./suggest/*.json", {eager: true, import: "default"});

const byName = <T>(modules: Record<string, T>): Record<string, T> =>
  Object.fromEntries(
    Object.entries(modules).map(([path, value]) => [path.replace(/^.*\/|\.json$/g, ""), value]),
  );

/** Keyed by file name, e.g. ASK_RESPONSE_FIXTURES["clarification-which-jalen"]. */
export const ASK_RESPONSE_FIXTURES: Record<string, AskResponse> = byName(responseModules);
export const ASK_SUGGEST_FIXTURES: Record<string, AskSuggestResponse> = byName(suggestModules);
