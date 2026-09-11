import type { GameSummaryData, PlayoffBracketResponse } from "@/helpers/helpers";
import type {AskResponse} from "@/helpers/ask";

const getBaseUrl = () => import.meta.env.DEV
  ? import.meta.env.VITE_API_URL_DEV || `${window.location.protocol}//${window.location.hostname}:8000`
  : import.meta.env.VITE_API_URL_PROD;

export const askQuestion = async (question: string, signal?: AbortSignal): Promise<AskResponse> => {
  const response = await fetch(`${getBaseUrl()}/ask`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({question}),
    signal,
  });
  if (response.status === 429) throw new Error("Search has reached its request limit. Please try again later.");
  if (!response.ok) throw new Error("Search is unavailable right now. Please try again shortly.");
  return response.json();
};

export const getScores = async (dateParam: string) => {
  const url = dateParam 
    ? `${getBaseUrl()}/?date=${dateParam}` 
    : `${getBaseUrl()}/`;
  const response = await fetch(url);
  if (!response.ok) throw new Error("Scoreboard fetch failed");
  return response.json();
};

export const getBoxScores = async (gameId: string) => {
  const url = `${getBaseUrl()}/games/${gameId}/boxscore`;
  const response = await fetch(url);
  if (!response.ok) throw new Error("Boxscore fetch failed");
  return response.json();
};

export const getGameSummary = async (gameId: string): Promise<GameSummaryData> => {
  const url = `${getBaseUrl()}/gamesummary/${gameId}`;
  const response = await fetch(url);
  if (!response.ok) throw new Error("Game summary fetch failed");
  return response.json();
};

export interface GameDaysResponse {
  year: number;
  month: number;
  season: string;
  game_days: string[];
  total: number;
}

export const getGameDays = async (year: number, month: number): Promise<GameDaysResponse> => {
  const url = `${getBaseUrl()}/api/game-days?year=${year}&month=${month}`;
  const response = await fetch(url);
  if (!response.ok) throw new Error("Game days fetch failed");
  return response.json();
};

export const getPlayoffPicture = async (season: string): Promise<PlayoffBracketResponse> => {
  const url = `${getBaseUrl()}/playoffs/series?season=${season}`;
  const response = await fetch(url);
  if (!response.ok) throw new Error("Playoff picture fetch failed");
  return response.json();
};


export interface InactivePlayer {
  personId: number;
  firstName: string;
  familyName: string;
}

export interface InactivePlayersResponse {
  teams: Record<string, InactivePlayer[]>;
}

export const getInactivePlayers = async (
  gameId: string,
  signal?: AbortSignal,
): Promise<InactivePlayersResponse> => {
  const response = await fetch(`${getBaseUrl()}/games/${gameId}/inactive-players`, {signal});
  if (!response.ok) throw new Error("Inactive players fetch failed");
  return response.json();
};
