# Early BAA bracket experiment

This compact, asymmetric layout applies only to the 1946-47 and 1947-48 seasons in the Hardwood preview. It extends the existing design system. The original masthead and all other playoff formats keep their existing presentation.

`src/utils/baaBracketTopology.ts` recognizes five distinct series by stage and bracket group. Division winners play one semifinal; two quarterfinals feed the other semifinal; both semifinals feed the Finals. Connections never consult winners, scores, or participant identities. An incomplete or unsupported shape falls back to the existing bracket renderer.

`src/hooks/useBaaBracketReveal.ts` follows those series dependencies. The division-winner semifinal and both quarterfinals have known participants from the start, with results hidden. The other semifinal matchup unlocks after both quarterfinal results are revealed. The Finals matchup unlocks after both semifinal results are revealed. Hiding a series also hides its dependent results. Changing seasons resets the reveal state; showing all results exposes every series.

`src/designs/design-1/components/BaaPlayoffBracket.tsx` presents full historical team names and the existing historical logos through `BracketSeriesCard`. The format note and Show/Hide All Results control use the same centered presentation as the other brackets. Locked matchups explain which preceding series to reveal. Buttons retain keyboard focus styling and announce reveal changes through a live status region.

The scoped `hw-baa` rules in `src/designs/design-1/hardwood.css` use three stage columns on wide screens, with connector lines and the division-winner semifinal entering above the other semifinal. At widths below 900px, cards stack in one column, connector lines disappear, and semifinal labels explain advancement to the Finals. Existing Hardwood colors, typography, and card styling remain the visual reference in `DESIGN.md`.

To undo the experiment, run this from the project directory:

```sh
python3 .git/codex-backups/historical-bracket-20260904/undo.py
```

The undo script restores prior file contents and refuses to overwrite files with later edits. Its backup lives locally under `.git`.
