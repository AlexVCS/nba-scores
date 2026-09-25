"""Read-only VideoDetails coverage probe. Run with the project's Python environment.

Writes request parameters and raw upstream evidence, never treats transport errors
as missing coverage. Does not implement the product's playlist API or a media proxy.
"""

import argparse
import importlib.metadata
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nba_api.stats.endpoints.boxscoretraditionalv3 import BoxScoreTraditionalV3
from nba_api.stats.endpoints.videodetails import VideoDetails
from nba_api.stats.endpoints.videodetailsasset import VideoDetailsAsset
from server.services.nba_stats_client import NBA_STATS_HEADERS

STATS = {
    "FGM": "fieldGoalsMade", "AST": "assists", "FGA": "fieldGoalsAttempted",
    "FG3M": "threePointersMade", "FG3A": "threePointersAttempted",
    "FTM": "freeThrowsMade", "FTA": "freeThrowsAttempted",
    "REB": "reboundsTotal", "OREB": "reboundsOffensive",
    "DREB": "reboundsDefensive", "STL": "steals", "BLK": "blocks",
    "TOV": "turnovers", "PTS": "points",
}

# Candidate IDs must resolve to a real boxscore before any playlist is requested.
SAMPLES = [
    ("0022500931", "2025-26", "regular", ["Regular Season"]),
    ("0042400407", "2024-25", "playoffs", ["Playoffs"]),
    ("0052400101", "2024-25", "play-in", ["PlayIn", "Playoffs", "Regular Season", "Play-In"]),
    ("0012400001", "2024-25", "preseason", ["Pre Season"]),
    ("0022300001", "2023-24", "regular", ["Regular Season"]),
    ("0022000001", "2020-21", "regular", ["Regular Season"]),
    ("0021500001", "2015-16", "regular", ["Regular Season"]),
    ("0021400001", "2014-15", "regular", ["Regular Season"]),
    ("0021300001", "2013-14", "regular", ["Regular Season"]),
    ("0021200001", "2012-13", "regular", ["Regular Season"]),
]


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def request(endpoint):
    started = time.monotonic()
    evidence = {"startedAt": timestamp(), "parameters": endpoint.parameters}
    try:
        endpoint.get_request()
        evidence["body"] = endpoint.get_dict()
        evidence["result"] = "json_response_requires_clip_validation"
    except Exception as error:
        evidence.update(result="retrieval_error", errorType=type(error).__name__, error=str(error))
    response = endpoint.nba_response
    if response is not None:
        evidence.update(httpStatus=response._status_code, url=response.get_url(),
                        rawBody=response.get_response())
    evidence["durationMs"] = round((time.monotonic() - started) * 1000)
    return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--endpoint", choices=["VideoDetails", "VideoDetailsAsset"], default="VideoDetails")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    report = {"startedAt": timestamp(), "nbaApiVersion": importlib.metadata.version("nba_api"),
              "python": platform.python_version(), "platform": platform.platform(),
              "endpoint": args.endpoint, "timeoutSeconds": 12, "mediaProxy": False, "samples": []}
    endpoint_class = VideoDetails if args.endpoint == "VideoDetails" else VideoDetailsAsset

    def save():
        (args.output / "retrieval.json").write_text(json.dumps(report, indent=2) + "\n")

    for game_id, season, game_type, season_types in SAMPLES:
        sample = {"gameId": game_id, "season": season, "gameType": game_type, "playlists": []}
        report["samples"].append(sample)
        box = request(BoxScoreTraditionalV3(game_id=game_id, headers=NBA_STATS_HEADERS,
                                           timeout=12, get_request=False))
        sample["boxscore"] = box
        game = box.get("body", {}).get("boxScoreTraditional", {})
        players = [(team["teamId"], player)
                   for side in ("homeTeam", "awayTeam")
                   if (team := game.get(side))
                   for player in team.get("players", [])]
        if game.get("gameId") != game_id or not players:
            sample["status"] = "boxscore_unavailable_no_playlist_test"
            print(game_id, sample["status"], flush=True)
            save()
            continue
        sample["matchup"] = f"{game['awayTeam']['teamTricode']} at {game['homeTeam']['teamTricode']}"
        stats = list(STATS) if game_id == "0022500931" else ["FGM", "AST"]
        for season_type in season_types:
            for stat in stats:
                # Use Harden for the primary FGM/AST pair, a positive-stat player
                # for other categories so a zero boxscore cannot explain emptiness.
                team_id, player = next(((tid, p) for tid, p in players
                                       if game_id == "0022500931" and stat in ("FGM", "AST")
                                       and p["personId"] == 201935),
                                      max(players, key=lambda pair: pair[1]["statistics"][STATS[stat]]))
                video = endpoint_class(team_id=team_id, player_id=player["personId"],
                                     context_measure_detailed=stat, season=season,
                                     season_type_all_star=season_type, game_id_nullable=game_id,
                                     headers=NBA_STATS_HEADERS, timeout=12, get_request=False)
                result = request(video)
                result.update(playerName=f"{player['firstName']} {player['familyName']}",
                              boxscoreValue=player["statistics"][STATS[stat]])
                sample["playlists"].append(result)
                print(game_id, sample["matchup"], season_type, stat, result["playerName"],
                      result.get("httpStatus"), result["result"], flush=True)
                save()
                time.sleep(0.3)
    report["finishedAt"] = timestamp()
    save()


if __name__ == "__main__":
    main()
