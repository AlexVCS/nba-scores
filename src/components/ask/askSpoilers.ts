// Spoiler gate for Ask results. Components read protected values only through these helpers, so a hidden
// value never reaches the DOM or accessibility text.
import type {GameData} from "@/helpers/helpers";
import type {AskGameSpoilers, Guarded} from "@/services/ask/types";

/** Everything that answers the question: stats, winners, series, rounds, inferred participants. */
export const RESULT_GROUP = "result";
/** The final score of the game behind a single-stat answer, revealed separately. */
export const SCORE_GROUP = "score";

export function guarded<T>(value: Guarded<T>, revealed: boolean): T | undefined {
  return !value.spoiler || revealed ? value.value : undefined;
}

export function withoutSpoilers<T extends {spoiler: boolean}>(items: readonly T[], revealed: boolean): T[] {
  return items.filter(item => revealed || !item.spoiler);
}

/**
 * A copy of the scoreboard payload that is safe to hand to a game card while hidden: scores zeroed,
 * status text generic (no "Final/OT"), series and round labels dropped, and unknown keys removed.
 */
export function safeGame(game: GameData, spoilers: AskGameSpoilers, revealed: boolean): GameData {
  if (revealed) return game;
  const statusText = spoilers.status_text ? "Game" : game.gameStatusText;
  const team = (side: GameData["homeTeam"]) => ({
    teamName: side.teamName,
    teamTricode: side.teamTricode,
    teamId: side.teamId,
    score: spoilers.score ? 0 : side.score,
  });
  return {
    gameId: game.gameId,
    gameCode: game.gameCode,
    gameStatus: spoilers.status_text ? 1 : game.gameStatus,
    gameLabel: spoilers.labels ? "" : game.gameLabel,
    gameSubLabel: spoilers.labels ? "" : game.gameSubLabel,
    gameTimeUTC: game.gameTimeUTC,
    gameStatusText: statusText,
    ifNecessary: spoilers.labels ? false : game.ifNecessary,
    seriesGameNumber: spoilers.labels ? "" : game.seriesGameNumber,
    seriesText: spoilers.series_text ? "" : game.seriesText,
    boxscoreAvailable: game.boxscoreAvailable,
    homeTeam: team(game.homeTeam),
    awayTeam: team(game.awayTeam),
  };
}
