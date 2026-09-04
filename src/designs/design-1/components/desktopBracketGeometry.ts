interface BracketPosition {
  roundIndex: number;
  order: number;
}

export function bracketRow(roundIndex: number, order: number) {
  const branchSpan = 2 ** roundIndex;
  return Math.min(7, Math.max(1, order * branchSpan * 2 + branchSpan));
}

/** Historical bye layouts can place neighbors on consecutive, not alternate, tracks. */
export function bracketRowSeparation(columns: BracketPosition[][]) {
  let separation = 2;
  for (const column of columns) {
    const rows = column.map(slot => bracketRow(slot.roundIndex, slot.order)).sort((a, b) => a - b);
    for (let index = 1; index < rows.length; index += 1) {
      separation = Math.min(separation, Math.max(1, rows[index] - rows[index - 1]));
    }
  }
  return separation;
}
