// Shared types for all designs
export type GameData = {
  gameId: string;
  gameCode: string;
  gameStatus: number;
  gameLabel: string;
  gameSubLabel: string;
  gameTimeUTC: string;
  gameStatusText: string;
  ifNecessary: boolean;
  seriesGameNumber: string;
  seriesText: string;
  homeTeam: {
    teamName: string;
    teamTricode: string;
    teamId: number;
    score: number;
  };
  awayTeam: {
    teamName: string;
    teamTricode: string;
    teamId: number;
    score: number;
  };
};

export interface DesignWrapperProps {
  designNumber: number;
}
