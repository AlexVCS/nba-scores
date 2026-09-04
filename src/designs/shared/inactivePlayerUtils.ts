import type {Player} from "@/helpers/helpers";
import type {DesignBoxscoreTeam, InactivePlayer} from "../hooks/useBoxscorePage";

export function isInactivePlayer(player: Player) {
  return player.status === "INACTIVE";
}

export function getInactivePlayers(team: DesignBoxscoreTeam): InactivePlayer[] {
  const inactivePlayers = [...(team.inactivePlayers ?? []), ...team.players.filter(isInactivePlayer)];
  const seenPlayerIds = new Set<number>();

  return inactivePlayers.filter((player) => {
    if (seenPlayerIds.has(player.personId)) return false;
    seenPlayerIds.add(player.personId);
    return true;
  });
}

export function getActiveBoxscorePlayers(players: Player[]) {
  return players.filter((player) => !isInactivePlayer(player));
}
