const getBaseUrl = () => import.meta.env.DEV
  ? import.meta.env.VITE_API_URL_DEV
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
  if (!response.ok) throw new Error("Boxscore fetch failed");
  return response.json();
};

export const getGameSummary = async (gameId: string) => {
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