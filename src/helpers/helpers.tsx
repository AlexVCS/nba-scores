export type Team = {
  teamName: string;
  teamTricode: string;
  players: Player[];
  score: number;
};

export type PlayerStatus = {
  personId: string;
  name: string;
  status: "ACTIVE" | "INACTIVE";
  notPlayingReason?: string;
  statistics: PlayerStatistics;
};

export interface Player {
  personId: number;
  firstName: string;
  familyName: string;
  nameI: string;
  playerSlug: string;
  position: string;
  comment: string;
  jerseyNum: string;
  statistics: {
    minutes: string;
    fieldGoalsMade: number;
    fieldGoalsAttempted: number;
    fieldGoalsPercentage: number;
    threePointersMade: number;
    threePointersAttempted: number;
    threePointersPercentage: number;
    freeThrowsMade: number;
    freeThrowsAttempted: number;
    freeThrowsPercentage: number;
    reboundsOffensive: number;
    reboundsDefensive: number;
    reboundsTotal: number;
    assists: number;
    steals: number;
    blocks: number;
    turnovers: number;
    foulsPersonal: number;
    points: number;
    plusMinusPoints: number;
  };
}
export interface PlayerStatistics {
  assists: number;
  blocks: number;
  blocksReceived: number;
  fieldGoalsAttempted: number;
  fieldGoalsMade: number;
  fieldGoalsPercentage: number;
  foulsOffensive: number;
  foulsDrawn: number;
  foulsPersonal: number;
  foulsTechnical: number;
  freeThrowsAttempted: number;
  freeThrowsMade: number;
  freeThrowsPercentage: number;
  minus: number;
  minutes: string;
  minutesCalculated: string;
  plus: number;
  plusMinusPoints: number;
  points: number;
  pointsFastBreak: number;
  pointsInThePaint: number;
  pointsSecondChance: number;
  reboundsDefensive: number;
  reboundsOffensive: number;
  reboundsTotal: number;
  steals: number;
  threePointersAttempted: number;
  threePointersMade: number;
  threePointersPercentage: number;
  turnovers: number;
  twoPointersAttempted: number;
  twoPointersMade: number;
  twoPointersPercentage: number;
}

export const formatPlayerNameLink = (player: Player) => {
  return `${player.personId}/${player.nameI
    .toLowerCase()
    .replace(/\.|'/g, "")
    .split(" ")
    .filter((letter: string) => letter !== ".")
    .join("-")}`;
};

export const placeholderTeamLogoUrl = "https://cdn.nba.com/logos/nba/fallback.svg";

export const placeholderPlayerHeadshot = "https://placehold.co/48x48?text=No+headshot";

export function formatMinutesPlayed(minutesString: string) {
  const minutes = parseInt(minutesString.match(/(\d+)M/)?.[1] || "0");
  return minutes < 10 ? minutes.toString() : minutes.toString();
}

export const firstNameInitial = (playerName: string): string => {
  const nameParts = playerName.split(" ");
  if (nameParts.length >= 2) {
    const firstName = nameParts[0];
    const lastName = nameParts.slice(1).join(" ");
    return `${firstName[0]}. ${lastName}`;
  }
  return playerName;
};

export function setItem(key: string, value: unknown) {
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch (error) {
    console.log(error);
  }
}

export function getItem(key: string) {
  try {
    const item = window.localStorage.getItem(key);
    return item ? JSON.parse(item) : undefined;
  } catch (error) {
    console.log(error);
  }
}

export const COLORS: Record<string, Record<string, string>> = {
  text: {
    light: "hsl(0deg, 0%, 10%)", // white
    dark: "hsl(0deg, 0%, 100%)", // near-black
  },
  background: {
    light: "hsl(0deg, 0%, 100%)", // white
    dark: "hsl(250deg, 70%, 7%)", // navy navy blue
  },
  primary: {
    light: "hsl(340deg, 100%, 40%)", // Pinkish-red
    dark: "hsl(50deg, 100%, 50%)", // Yellow
  },
  secondary: {
    light: "hsl(250deg, 100%, 50%)", // Purplish-blue
    dark: "hsl(190deg, 100%, 40%)", // Cyan
  },
  // Grays, scaling from least-noticeable to most-noticeable
  gray300: {
    light: "hsl(0deg, 0%, 70%)",
    dark: "hsl(0deg, 0%, 30%)",
  },
  gray500: {
    light: "hsl(0deg, 0%, 50%)",
    dark: "hsl(0deg, 0%, 50%)",
  },
  gray700: {
    light: "hsl(0deg, 0%, 30%)",
    dark: "hsl(0deg, 0%, 70%)",
  },
};

export const COLOR_MODE_KEY = "color-mode";
export const INITIAL_COLOR_MODE_CSS_PROP = "--initial-color-mode";
