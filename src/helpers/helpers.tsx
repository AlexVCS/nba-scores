import { Player } from "@/routes/games/boxscore/Boxscore.jsx";

export const formatPlayerNameLink = (player: Player) => {
 return `${player.personId}/${player.name
   .toLowerCase()
   .replace(/\.|'/g, "")
   .split(" ")
   .filter((letter: string) => letter !== ".")
   .join("-")}`;
}

export const placeholderTeamLogo = <img src="https://placehold.co/48x48?text=No+logo" alt="Placeholder team logo" />

export function formatMinutesPlayed(minutesString: string) {
  const minutes = parseInt(minutesString.match(/(\d+)M/)?.[1] || "0");
  return minutes < 10 ? minutes.toString() : minutes.toString();
}