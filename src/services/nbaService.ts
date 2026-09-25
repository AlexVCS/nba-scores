import type { GameSummaryData, PlayoffBracketResponse } from "@/helpers/helpers";

const getBaseUrl = () => import.meta.env.DEV
  ? import.meta.env.VITE_API_URL_DEV || `${window.location.protocol}//${window.location.hostname}:8000`
  : import.meta.env.VITE_API_URL_PROD;

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
  if (response.status === 404) return {game: null};
  if (!response.ok) throw new Error("Boxscore fetch failed");
  return response.json();
};

export interface GameDetails {
  gameId: string;
  gameStatus: number | null;
  gameStatusText: string;
  gameTimeUTC: string | null;
  gameDate: string | null;
  homeTeam: {teamId: number; teamTricode: string; teamName: string};
  awayTeam: GameDetails["homeTeam"];
  venue: string | null;
  venueCity?: string | null;
  venueState?: string | null;
  broadcast: string | null;
  boxscoreAvailable: boolean;
}

export const getGameDetails = async (gameId: string, date: string, signal?: AbortSignal): Promise<GameDetails> => {
  const response = await fetch(`${getBaseUrl()}/games/${gameId}/details${date ? `?date=${date}` : ""}`, {signal});
  if (!response.ok) throw new Error("Game details fetch failed");
  return response.json();
};

export interface MatchupTeam {
  teamId: number;
  teamTricode: string;
  score: number;
}

export interface LastMatchup {
  gameId: string;
  gameDate: string;
  homeTeam: MatchupTeam;
  awayTeam: MatchupTeam;
}

export const getLastMatchups = async (teamId: number, opponentId: number, before: string, signal?: AbortSignal): Promise<{games: LastMatchup[]}> => {
  const params = new URLSearchParams({teamId: String(teamId), opponentId: String(opponentId), before});
  const response = await fetch(`${getBaseUrl()}/matchups?${params}`, {signal});
  if (!response.ok) throw new Error("Last matchups fetch failed");
  return response.json();
};

export const getGameSummary = async (gameId: string): Promise<GameSummaryData | null> => {
  const url = `${getBaseUrl()}/gamesummary/${gameId}`;
  const response = await fetch(url);
  if (response.status === 404) return null;
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

export interface RecentGameDaysResponse {
  before: string;
  game_days: string[];
  total: number;
}

export const getRecentGameDays = async (before: string): Promise<RecentGameDaysResponse> => {
  const params = new URLSearchParams({before});
  const url = `${getBaseUrl()}/api/game-days/recent?${params}`;
  const response = await fetch(url);
  if (!response.ok) throw new Error("Recent game days fetch failed");
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
