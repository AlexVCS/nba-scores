import {getItem, setItem} from "@/helpers/helpers";
import {ASK_MAX_QUESTION_LENGTH} from "@/services/ask/types";

export const ASK_RECENT_STORAGE_KEY = "nba-scorez:ask:recent:v1";
export const ASK_RECENT_LIMIT = 6;

/**
 * Only the question text and when it was asked. Answers are never stored, and callers must not add
 * questions that came from spoiler-flagged suggestions or options.
 */
export interface AskRecentSearch {
  question: string;
  askedAt: string;
}

function isRecent(value: unknown): value is AskRecentSearch {
  if (typeof value !== "object" || value === null) return false;
  const entry = value as Record<string, unknown>;
  return typeof entry.question === "string" && entry.question.trim() !== "" && typeof entry.askedAt === "string";
}

export function readRecentSearches(): AskRecentSearch[] {
  const stored: unknown = getItem(ASK_RECENT_STORAGE_KEY);
  if (!Array.isArray(stored)) return [];
  return stored
    .filter(isRecent)
    .map(({question, askedAt}) => ({question: question.slice(0, ASK_MAX_QUESTION_LENGTH), askedAt}))
    .slice(0, ASK_RECENT_LIMIT);
}

export function addRecentSearch(question: string, askedAt: Date = new Date()): AskRecentSearch[] {
  const trimmed = question.trim().slice(0, ASK_MAX_QUESTION_LENGTH);
  if (!trimmed) return readRecentSearches();
  const normalized = trimmed.toLowerCase();
  const next = [
    {question: trimmed, askedAt: askedAt.toISOString()},
    ...readRecentSearches().filter(entry => entry.question.toLowerCase() !== normalized),
  ].slice(0, ASK_RECENT_LIMIT);
  setItem(ASK_RECENT_STORAGE_KEY, next);
  return next;
}

export function clearRecentSearches(): AskRecentSearch[] {
  setItem(ASK_RECENT_STORAGE_KEY, []);
  return [];
}
