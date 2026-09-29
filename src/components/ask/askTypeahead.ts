// Pure typeahead grouping. Data comes from GET /ask/suggest (no model call) and the live input text.
import {getDefaultPlayoffSeason} from "@/helpers/helpers";
import type {AskSuggestGame, AskSuggestResponse} from "@/services/ask/types";

export type AskActionKind = "recent" | "example" | "game" | "bracket" | "ask";

export interface AskAction {
  id: string;
  kind: AskActionKind;
  label: string;
  detail?: string;
  meta?: string;
  /** Design-agnostic app path for direct matches; the UI adds the design prefix. */
  href?: string;
  /** Question to run for Ask rows, recents, and examples. */
  question?: string;
}

export interface AskActionGroup {
  id: string;
  label: string;
  actions: AskAction[];
}

export const askOptionId = (listboxId: string, actionId: string) => `${listboxId}-${actionId}`;

export const TYPEAHEAD_GAME_LIMIT = 4;
export const TYPEAHEAD_QUESTION_LIMIT = 3;
const SHORT_QUERY_WORDS = 3;
const QUESTION_START = /^(who|whom|what|when|where|which|why|how|did|does|do|was|were|is|are|can|could|show|list|tell|find)\b/;
const PLAYOFF_KEYWORD = /\b(playoffs?|postseason|bracket|finals?|series|first round)\b/;

export function normalizeAskQuery(query: string): string {
  return query.toLowerCase().replace(/[^\p{L}\p{N}\s@-]/gu, " ").replace(/\s+/g, " ").trim();
}

export function isQuestionShaped(query: string): boolean {
  const normalized = normalizeAskQuery(query);
  if (!normalized) return false;
  if (query.trim().endsWith("?")) return true;
  if (QUESTION_START.test(normalized)) return true;
  return normalized.split(" ").length > SHORT_QUERY_WORDS;
}

/** Postseason and play-in ids reveal qualification, so they never appear while results are hidden. */
export function isPostseasonGameId(gameId: string): boolean {
  return /^00[45]/.test(gameId);
}

function formatDate(date: string): string {
  const parsed = new Date(`${date}T12:00:00`);
  if (Number.isNaN(parsed.getTime())) return date;
  return parsed.toLocaleDateString("en-US", {weekday: "short", month: "short", day: "numeric", year: "numeric"});
}

function gameAction(game: AskSuggestGame): AskAction {
  return {
    id: `game-${game.game_id}`,
    kind: "game",
    label: `${game.away.tricode} @ ${game.home.tricode}`,
    detail: formatDate(game.date),
    meta: "Boxscore",
    href: game.href,
  };
}

export function askAction(question: string, id = "ask-typed"): AskAction {
  return {id, kind: "ask", label: question, question};
}

interface BuildTypeaheadOptions {
  query: string;
  suggest: AskSuggestResponse | undefined;
  resultsHidden: boolean;
  now?: Date;
}

export function buildTypeaheadGroups({query, suggest, resultsHidden, now = new Date()}: BuildTypeaheadOptions): AskActionGroup[] {
  const trimmed = query.trim();
  if (!trimmed) return [];

  // The server already filters with hidden=true; filter again so a stale or permissive response cannot leak.
  const games = (suggest?.games ?? [])
    .filter(game => !resultsHidden || !isPostseasonGameId(game.game_id))
    .slice(0, TYPEAHEAD_GAME_LIMIT)
    .map(gameAction);
  const hasEntity = games.length > 0 || (suggest?.entities.length ?? 0) > 0;
  const shortEntity = hasEntity && !isQuestionShaped(trimmed);

  // Only a generic bracket link: a team-specific series row would reveal qualification or opponents.
  const season = getDefaultPlayoffSeason(now);
  const bracket: AskAction[] = PLAYOFF_KEYWORD.test(normalizeAskQuery(trimmed))
    ? [{id: `bracket-${season}`, kind: "bracket", label: `${season} playoff bracket`, meta: "Bracket", href: `/playoffs?season=${season}`}]
    : [];

  const typed = normalizeAskQuery(trimmed);
  const questions = (suggest?.questions ?? [])
    .filter(suggestion => !resultsHidden || !suggestion.spoiler)
    .filter(suggestion => normalizeAskQuery(suggestion.question) !== typed)
    .slice(0, TYPEAHEAD_QUESTION_LIMIT)
    .map((suggestion, index) => askAction(suggestion.question, `ask-suggested-${index}`));

  const groups: AskActionGroup[] = [
    {id: "games", label: "Games", actions: games},
    {id: "playoffs", label: "Playoffs", actions: bracket},
    {id: "ask", label: "Ask", actions: [askAction(trimmed), ...questions]},
  ];
  // Short entity queries ("knicks") put direct game matches first; question-shaped text puts Ask first.
  const ordered = shortEntity ? groups : [groups[2], groups[0], groups[1]];
  return ordered.filter(group => group.actions.length > 0);
}
