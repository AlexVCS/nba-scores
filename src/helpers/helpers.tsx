export const formatPlayerNameLink = (player) => {
 return `${player.personId}/${player.name
   .toLowerCase()
   .replace(/\./g, "")
   .split(" ")
   .filter((letter: string) => letter !== ".")
   .join("-")}`;
} 