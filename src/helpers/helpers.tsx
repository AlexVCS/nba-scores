// import { Player } from "@/routes/games/boxscore/Boxscore.jsx";

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

