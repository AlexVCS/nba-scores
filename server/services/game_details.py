"""Matchup metadata without requiring player statistics or period scores."""

import copy
import logging
from datetime import date, datetime

from server.services import game_data, nba_stats_client
from server.services.game_summary import safe_int, parse_gamecode_team_tricodes
from server.services.nba_schedule import ScheduleLookupCooldownError, get_season_schedule
from server.services.scoreboard import get_scoreboard
from server.utils.boxscore_availability import is_valid_nba_game_id

logger = logging.getLogger(__name__)


def _game_date(value):
    if not value:
        return None
    text = str(value)
    if "/" in text:
        return datetime.strptime(text.split(" ")[0], "%m/%d/%Y").date().isoformat()
    return date.fromisoformat(text[:10]).isoformat()


def _schedule_game(game_id):
    year = int(game_id[3:5])
    year += 1900 if year >= 46 else 2000
    try:
        # Shares the calendar's season schedule; pregame pages wait for an
        # in-flight fetch rather than starting their own.
        schedule = get_season_schedule(
            f"{year}-{str(year + 1)[-2:]}",
            allow_completed_fallback=False,
            optional_lookup=True,
            wait=True,
        )
    except ScheduleLookupCooldownError as exc:
        # Report the cooldown as the upstream outage it stands for, so a game no
        # other source identifies stays retryable rather than "not found".
        raise nba_stats_client.UpstreamUnavailableError(
            "ScheduleLeagueV2", type(exc).__name__, 0, str(exc)
        ) from exc
    scheduled = schedule.games.get(game_id)
    # The schedule entry is shared across requests; hand out a mutable copy.
    return copy.deepcopy(dict(scheduled)) if scheduled else None


def _legacy_game(game_id):
    summary = game_data.get_summary_v2(game_id)
    rows = summary["game_summary"]
    if rows.empty:
        return None
    row = rows.iloc[0]
    teams = summary["line_score"]
    home_code, away_code = parse_gamecode_team_tricodes(row.get("GAMECODE"))

    def team(team_id, tricode):
        matches = teams[teams["TEAM_ID"] == team_id] if "TEAM_ID" in teams else teams
        info = matches.iloc[0] if not matches.empty else {}
        return {
            "teamId": safe_int(team_id),
            "teamTricode": info.get("TEAM_ABBREVIATION") or tricode,
            "teamCity": info.get("TEAM_CITY_NAME", ""),
            "teamName": info.get("TEAM_NAME") or info.get("TEAM_NICKNAME", ""),
        }

    return {
        "gameId": game_id,
        "gameDate": row.get("GAME_DATE_EST"),
        "gameStatus": safe_int(row.get("GAME_STATUS_ID")),
        "gameStatusText": row.get("GAME_STATUS_TEXT", ""),
        "homeTeam": team(row.get("HOME_TEAM_ID"), home_code),
        "awayTeam": team(row.get("VISITOR_TEAM_ID"), away_code),
    }


def fetch_game_details(game_id: str, game_date: str | None = None):
    if not is_valid_nba_game_id(game_id):
        raise ValueError("Invalid game ID")
    if game_date:
        game_date = _game_date(game_date)
    game = None
    error = None
    # A date hint avoids summary coverage limitations for early NBA/BAA games.
    if game_date:
        try:
            board = get_scoreboard(game_date)
            game = next((g for g in board["games"] if g.get("gameId") == game_id), None)
        except (nba_stats_client.UpstreamError, ValueError) as exc:
            error = exc
    if game is None:
        try:
            candidate = game_data.get_summary_v3(game_id)
            if candidate and candidate["homeTeam"].get("teamId"):
                game = candidate
        except (nba_stats_client.UpstreamError, ValueError) as exc:
            error = exc
    # The published schedule contains pregame venue and broadcaster information.
    # It can be hours old, so it only enriches fresher sources and stands in for
    # them alone while it still reports the game as scheduled.
    scheduled = None
    if game is None or safe_int(game.get("gameStatus")) == 1:
        try:
            scheduled = _schedule_game(game_id)
        except (nba_stats_client.UpstreamError, ValueError) as exc:
            error = exc
            logger.info("Schedule details unavailable for %s: %s", game_id, exc)
    if scheduled and (game is not None or safe_int(scheduled.get("gameStatus")) == 1):
        game = {**scheduled, **(game or {})}
    if game is None:
        try:
            game = _legacy_game(game_id)
        except (nba_stats_client.UpstreamError, ValueError) as exc:
            error = exc
        # A started or final schedule entry alone is not authoritative.
        if game and scheduled:
            game = {**scheduled, **game}
    if not game:
        if error:
            raise error
        raise ValueError("Game details unavailable")

    def team(side):
        source = game.get(side) or {}
        return {
            "teamId": safe_int(source.get("teamId")) or 0,
            "teamTricode": source.get("teamTricode") or "",
            "teamName": " ".join(str(source[key]) for key in ("teamCity", "teamName") if source.get(key)),
        }

    def arena_field(key):
        return game.get(key) or (game.get("arena") or {}).get(key) or None

    status = safe_int(game.get("gameStatus"))
    status_text = game.get("gameStatusText") or ""
    broadcasters = game.get("broadcasters") or {}
    channels = [
        entry.get("broadcasterDisplay")
        for kind in ("nationalBroadcasters", "nationalOttBroadcasters", "homeTvBroadcasters", "awayTvBroadcasters")
        for entry in broadcasters.get(kind, [])
        if entry.get("broadcasterDisplay")
    ]
    return {
        "gameId": game_id,
        "gameStatus": status,
        "gameStatusText": status_text,
        "gameTimeUTC": game.get("gameDateTimeUTC") or game.get("gameTimeUTC") or None,
        "gameDate": _game_date(game.get("gameDateEst") or game.get("gameEt") or game.get("gameDate")) or game_date,
        "homeTeam": team("homeTeam"),
        "awayTeam": team("awayTeam"),
        "venue": arena_field("arenaName"),
        "venueCity": arena_field("arenaCity"),
        "venueState": arena_field("arenaState"),
        "broadcast": ", ".join(dict.fromkeys(channels)) or None,
        "boxscoreAvailable": status in (2, 3) and not any(word in status_text.lower() for word in ("postpon", "cancel")),
    }
