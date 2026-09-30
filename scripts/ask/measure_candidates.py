"""Measure Ask candidate lookup (#200) against a labeled question file.

Usage (from the repo root):

    server/venv/bin/python scripts/ask/measure_candidates.py
    server/venv/bin/python scripts/ask/measure_candidates.py --questions path/to/labels.json --json
    server/venv/bin/python scripts/ask/measure_candidates.py --min-recall 0.95

The default file is the DEVELOPMENT set, which is used for tuning. Numbers
from it are not release numbers; run the unseen release set for those.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from server.ask.candidates.evaluation import DEV_SET, evaluate, format_report  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--questions", type=Path, default=DEV_SET)
    parser.add_argument("--repeats", type=int, default=5, help="lookups per question for latency")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--min-recall", type=float, default=None, help="exit 1 if overall recall is lower")
    args = parser.parse_args()

    report = evaluate(args.questions, repeats=args.repeats)
    print(json.dumps(report.as_dict(), indent=2) if args.json else format_report(report))
    if args.min_recall is not None and (report.recall() or 0) < args.min_recall:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
