"""Recent head-to-head results between two teams for pregame previews."""

import time
from datetime import date

from server.services import nba_stats_client
from server.services.game_summary import safe_int

CACHE_TTL_SECONDS = 3600
# Regular season, playoffs, play-in and NBA Cup final; preseason and All-Star are skipped.
COUNTED_SEASON_PREFIXES = ("2", "4", "5", "6")
_cache: dict[tuple[int, int], tuple[float, list[dict]]] = {}


def _head_to_head(team_id: int, opponent_id: int) -> list[dict]:
    key = (team_id, opponent_id)
    cached = _cache.get(key)
    if cached and time.monotonic() - cached[0] < CACHE_TTL_SECONDS:
        return cached[1]
    frame = nba_stats_client.fetch_league_game_finder(
        player_or_team_abbreviation="T",
        team_id_nullable=str(team_id),
        vs_team_id_nullable=str(opponent_id),
        league_id_nullable="00",
    ).get_data_frames()[0]
    games = []
    for row in frame.to_dict("records"):
        matchup = str(row.get("MATCHUP") or "")
        if not str(row.get("SEASON_ID") or "").startswith(COUNTED_SEASON_PREFIXES):
            continue
        if " @ " in matchup:
            is_home = False
        elif " vs. " in matchup:
            is_home = True
        else:
            continue
        points = safe_int(row.get("PTS"))
        margin = row.get("PLUS_MINUS")
        if points is None or margin is None or margin != margin:
            continue
        team = {"teamId": team_id, "teamTricode": matchup.split(" ")[0], "score": points}
        opponent = {"teamId": opponent_id, "teamTricode": matchup.split(" ")[-1], "score": points - int(margin)}
        games.append({
            "gameId": str(row.get("GAME_ID")),
            "gameDate": str(row.get("GAME_DATE"))[:10],
            "homeTeam": team if is_home else opponent,
            "awayTeam": opponent if is_home else team,
        })
    games.sort(key=lambda game: game["gameDate"], reverse=True)
    _cache[key] = (time.monotonic(), games)
    return games


def fetch_last_matchups(team_id: int, opponent_id: int, before: date, limit: int = 4) -> dict:
    if team_id <= 0 or opponent_id <= 0 or team_id == opponent_id:
        raise ValueError("Two different team IDs are required")
    games = [game for game in _head_to_head(team_id, opponent_id) if game["gameDate"] < before.isoformat()]
    return {"games": games[:limit]}
