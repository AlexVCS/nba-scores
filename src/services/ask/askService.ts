import {
  ASK_MAX_QUESTION_LENGTH,
  ASK_SCHEMA_VERSION,
  type AskQuery,
  type AskResponse,
  type AskSuggestResponse,
} from "@/services/ask/types";

const getBaseUrl = () => import.meta.env.DEV
  ? import.meta.env.VITE_API_URL_DEV || `${window.location.protocol}//${window.location.hostname}:8000`
  : import.meta.env.VITE_API_URL_PROD;

/** Longest text the typeahead sends; longer input is a question, not a lookup. */
export const ASK_SUGGEST_MAX_LENGTH = 80;

/** Transport failure: no AskResponse came back. Budget and provider problems arrive as AskResponse outcomes. */
export class AskServiceError extends Error {
  status: number | null;

  constructor(message: string, status: number | null = null) {
    super(message);
    this.name = "AskServiceError";
    this.status = status;
  }
}

function isAskResponse(value: unknown): value is AskResponse {
  return typeof value === "object" && value !== null
    && (value as {schema_version?: unknown}).schema_version === ASK_SCHEMA_VERSION
    && typeof (value as {outcome?: unknown}).outcome === "string";
}

export async function postAsk(query: AskQuery, signal?: AbortSignal): Promise<AskResponse> {
  const body: AskQuery = {
    question: query.question.trim().slice(0, ASK_MAX_QUESTION_LENGTH),
    context: query.context ?? null,
    resolution: query.resolution ?? null,
  };

  let response: Response;
  try {
    response = await fetch(`${getBaseUrl()}/ask`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(body),
      signal,
    });
  } catch (error) {
    if (signal?.aborted) throw error;
    throw new AskServiceError("Ask request failed");
  }

  // Budget exhaustion and rate limits may use non-2xx statuses but still carry an AskResponse to render.
  const payload: unknown = await response.json().catch(() => null);
  if (isAskResponse(payload)) return payload;
  throw new AskServiceError("Ask request failed", response.status);
}

export async function getAskSuggestions(query: string, hidden: boolean, signal?: AbortSignal): Promise<AskSuggestResponse> {
  const params = new URLSearchParams({q: query.trim().slice(0, ASK_SUGGEST_MAX_LENGTH), hidden: String(hidden)});
  const response = await fetch(`${getBaseUrl()}/ask/suggest?${params}`, {signal});
  if (!response.ok) throw new Error("Ask suggestions fetch failed");
  return response.json();
}
