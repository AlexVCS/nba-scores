// Ask shows every answer it was asked for (ADR 0006). The global results preference still governs what
// Ask shows without being asked: suggestions, clarification options, and follow-up links. Those carry
// `spoiler: true` when they would reveal a result, and are left out of the DOM entirely while results are hidden.

export function withoutSpoilers<T extends {spoiler: boolean}>(items: readonly T[], showSpoilers: boolean): T[] {
  return items.filter(item => showSpoilers || !item.spoiler);
}
