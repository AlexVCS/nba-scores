export const formatPlayerNameLink = (player) => {
 return `${player.personId}/${player.name
   .toLowerCase()
   .replace(/\.|'/g, "")
   .split(" ")
   .filter((letter: string) => letter !== ".")
   .join("-")}`;
}

export const placeholderTeamLogo = <img src="https://placehold.co/48x48?text=No+logo" alt="Placeholder team logo" />