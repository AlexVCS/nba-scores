#!/usr/bin/env python3
"""Build the combined exposed-case input for the 2026-10-06 calibration run.

Copies cases verbatim from exposed development fixtures into one file, because
scripts/ask/release.py reads one cases file that must cover all eight tool families.
No fixture or label is changed. The blind set (unseen-three-draft.json) is never opened:
the sources are an explicit list.

Order is priority order, so a spend-cap stop drops the least important cases:
the new stage 2 and 3 cases, the seven exposed unseen-three cases, the second unseen
set (the only one with field labels), then a content-blind sample of the first unseen
set (3 of every 5 cases per family, by position).

Left out for budget: dev.json and both `release-*-exposed.json` sets (eight dev.json and
thirteen release-two cases also name no tool family, which release.py requires), and the
other 40 cases of unseen-2026-09-29.json.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "server/tests/ask/fixtures/eval"
FULL = ["stage2-dev.json", "stage3-dev.json", "unseen-three-exposed-dev.json", "unseen-two-2026-09-29.json"]
SAMPLED = "unseen-2026-09-29.json"
FAMILIES = ("game_search", "boxscore_stat", "playoff_series", "postseason_summary")
OUT = Path(__file__).with_name("cases.json")


def load(name: str) -> list[dict]:
    assert "unseen-three-draft" not in name
    return json.loads((FIXTURES / name).read_text())["cases"]


def main() -> None:
    cases, sources = [], {}
    for name in FULL:
        rows = load(name)
        cases += rows
        sources[name] = {"cases": len(rows), "sha256": hashlib.sha256((FIXTURES / name).read_bytes()).hexdigest()}
    rows = load(SAMPLED)
    seen = dict.fromkeys(FAMILIES, 0)
    picked = []
    for row in rows:
        family = row["tags"][0]
        if seen[family] % 5 in (0, 2, 4):
            picked.append(row)
        seen[family] += 1
    cases += picked
    sources[SAMPLED] = {"cases": len(picked), "of": len(rows), "rule": "positions 0, 2, 4 of every 5 per family",
                        "sha256": hashlib.sha256((FIXTURES / SAMPLED).read_bytes()).hexdigest()}
    doc = {"comment": "Exposed development cases only, copied verbatim. Calibration input, not release evidence.",
           "sources": sources, "cases": cases}
    OUT.write_text(json.dumps(doc, indent=1) + "\n")
    print(json.dumps({"out": str(OUT.relative_to(ROOT)), "cases": len(cases), "sources": sources}, indent=1))


if __name__ == "__main__":
    main()
