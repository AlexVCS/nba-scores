
export interface Player {
  status: string;
  notPlayingReason: string;
  order: number;
  personId: number;
  jerseyNum: string;
  position: string;
  starter: string;
  oncourt: string;
  played: string;
  statistics: PlayerStatistics;
  name: string;
  nameI: string;
  firstName: string;
  familyName: string;
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
 return `${player.personId}/${player.name
   .toLowerCase()
   .replace(/\.|'/g, "")
   .split(" ")
   .filter((letter: string) => letter !== ".")
   .join("-")}`;
}

export const placeholderTeamLogo = <img src="https://placehold.co/48x48?text=No+logo" alt="Placeholder team logo" />

export const placeholderPlayerHeadshot = <img src="https://placehold.co/48x48?text=No+headshot" alt="Placeholder player headshot" />

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
    window.localStorage.setItem(key, JSON.stringify(value))
  } catch (error) {
    console.log(error)
  }
}

export function getItem(key: string) {
  try {
    const item = window.localStorage.getItem(key)
    return item ? JSON.parse(item) : undefined
  } catch (error) {
    console.log(error)
  }
}

// export function toggleTheme(darkMode) {
//   const htmlElement = document.querySelector("html")
//   if(darkMode) {
//     htmlElement?.classList.add("dark");
//   }
//   htmlElement?.classList.remove("dark");
// }

