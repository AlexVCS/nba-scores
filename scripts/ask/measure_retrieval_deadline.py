"""Measure Ask season retrieval against one shared deadline (nba-scores-8ic).

Runs the season tools directly, without an interpreter or any LLM provider,
under a retrieval ``Deadline`` and records each NBA attempt and
Basketball-Reference fetch: its capped timeout, duration and error. Every
record states whether retrieval finished inside the budget.

Usage (from the repo root):

    # Offline: simulated slow sources, no network. Checks the budget decisions.
    server/venv/bin/python scripts/ask/measure_retrieval_deadline.py --simulate --nba-latency 5
    server/venv/bin/python scripts/ask/measure_retrieval_deadline.py --simulate --nba-latency 1 --nba-miss

    # On the production host: real NBA/BRef requests. Run from that host, with
    # the deployed deadline, and keep the output with the deployment record.
    server/venv/bin/python scripts/ask/measure_retrieval_deadline.py --live --budget 4.75 --repeats 3

``--budget`` is the retrieval time left after interpretation. The worst case with
the default 20 s deadline is 5 s interpretation reserve less a 0.25 s response
margin, so 4.75 s. Live runs space cases by the BRef start interval
so the process-wide limiter does not distort later cases. Caches are cleared
before each case. Simulated numbers are not host measurements.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import requests  # noqa: E402

from server.ask.models.request import PlayerSeasonStatsRequest, TeamRecordsRequest  # noqa: E402
from server.ask.resolvers import seasons  # noqa: E402
from server.ask.resolvers.errors import ResolverError  # noqa: E402
from server.services import basketball_reference  # noqa: E402
from server.utils.deadline import Deadline  # noqa: E402

BREF_FIXTURE = Path(__file__).resolve().parents[2] / "server/tests/ask/fixtures/season-data/bref-jokic-2024.html"
JOKIC = {"player_id": 203999, "name": "Nikola Jokic"}
CASES = {
    "player-2023-24": lambda: seasons.player_season,
    "standings-2023-24": lambda: seasons.team_records,
}


def requests_for(name):
    if name.startswith("player"):
        return PlayerSeasonStatsRequest(player=JOKIC, season="2023-24", stat={"stat": "rebounds", "aggregation": "per_game"})
    return TeamRecordsRequest(season="2023-24")


def instrument(steps, simulate=None):
    """Wrap the NBA endpoints and BRef transport so each call is timed."""
    def timed(source, call):
        def wrapper(*args, **kwargs):
            started = time.monotonic()
            step = {"source": source, "timeout_s": round(kwargs.get("timeout", 0), 3)}
            try:
                return call(*args, **kwargs)
            except Exception as exc:
                step["error"] = type(exc).__name__
                raise
            finally:
                step["duration_s"] = round(time.monotonic() - started, 3)
                steps.append(step)
        return wrapper

    if simulate:
        def nba(**kwargs):
            time.sleep(min(simulate.nba_latency, kwargs["timeout"]))
            if simulate.nba_latency > kwargs["timeout"]:
                raise requests.Timeout("simulated slow NBA")
            payload = {"resultSets": [{"name": "SeasonTotalsRegularSeason", "headers": ["SEASON_ID"], "rowSet": []}]}
            return SimpleNamespace(get_dict=lambda: payload)

        def bref(url, **kwargs):
            time.sleep(min(simulate.bref_latency, kwargs["timeout"]))
            if simulate.bref_latency > kwargs["timeout"]:
                raise requests.Timeout("simulated slow BRef")
            return SimpleNamespace(text=BREF_FIXTURE.read_text(), status_code=200, raise_for_status=lambda: None)
        seasons.playercareerstats.PlayerCareerStats = timed("nba", nba)
        basketball_reference.requests.get = timed("bref", bref)
        return
    for module, name in ((seasons.playercareerstats, "PlayerCareerStats"), (seasons.leaguestandings, "LeagueStandings"),
                         (seasons.teamyearbyyearstats, "TeamYearByYearStats")):
        setattr(module, name, timed("nba", getattr(module, name)))
    basketball_reference.requests.get = timed("bref", basketball_reference.requests.get)


def measure(name, budget, steps):
    seasons._cache.clear()
    steps.clear()
    deadline = Deadline.after(budget)
    started = time.monotonic()
    try:
        output = CASES[name]()(requests_for(name), deadline)
        outcome = f"answer:{output.sources[0].name}"
    except ResolverError as error:
        outcome = f"{type(error).__name__}:{error.reason}"
    elapsed = time.monotonic() - started
    return {"case": name, "budget_s": budget, "elapsed_s": round(elapsed, 3), "within_budget": elapsed <= budget,
            "outcome": outcome, "steps": list(steps)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--simulate", action="store_true", help="offline fake sources (no network)")
    mode.add_argument("--live", action="store_true", help="real NBA/BRef requests; run on the production host")
    parser.add_argument("--budget", type=float, default=4.75, help="retrieval seconds left after interpretation")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--case", choices=sorted(CASES), action="append")
    parser.add_argument("--nba-latency", type=float, default=5.0, help="simulated seconds per NBA attempt")
    parser.add_argument("--nba-miss", action="store_true", help="simulated NBA answers without the row (forces fallback)")
    parser.add_argument("--bref-latency", type=float, default=0.5, help="simulated seconds per BRef fetch")
    args = parser.parse_args()

    if args.simulate and args.nba_miss is False and args.nba_latency <= seasons.NBA_TIMEOUT_SECONDS:
        parser.error("--simulate needs --nba-latency above the NBA timeout or --nba-miss (it has no NBA row)")
    steps: list[dict] = []
    instrument(steps, args if args.simulate else None)
    cases = args.case or (["player-2023-24"] if args.simulate else sorted(CASES))
    failures = 0
    for repeat in range(args.repeats):
        for index, name in enumerate(cases):
            if args.live and (repeat or index):
                time.sleep(basketball_reference.INTERVAL_SECONDS + 0.5)
            record = measure(name, args.budget, steps)
            record["mode"] = "simulate" if args.simulate else "live"
            failures += not record["within_budget"]
            print(json.dumps(record))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
