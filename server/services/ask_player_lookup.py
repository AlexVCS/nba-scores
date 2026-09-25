"""Bounded historical player/date lookup for Ask player-stat requests."""
from __future__ import annotations

from datetime import date, datetime
import re
import unicodedata
from typing import Any

from nba_api.stats.static import players

from server.services import nba_stats_client
from server.services.ask_basketball import AskResolutionError


def _norm(value: str) -> str:
    text = "".join(
        char
        for char in unicodedata.normalize("NFKD", value.casefold())
        if not unicodedata.combining(char)
    )
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())


def _player_name(player: dict[str, Any]) -> str:
    return str(
        player.get("full_name")
        or player.get("fullName")
        or " ".join(filter(None, (player.get("first_name"), player.get("last_name"))))
        or " ".join(filter(None, (player.get("firstName"), player.get("lastName"))))
    )


def _resolve_player_id(player_name: str) -> str:
    requested = _norm(player_name)
    if not requested:
        raise AskResolutionError("not_found", "No matching player was found.")

    try:
        catalog = players.get_players()
    except Exception as error:
        raise _bad_response("Player catalog lookup failed", error) from error
    if not isinstance(catalog, list):
        raise _bad_response("Player catalog is not a list")

    valid_players = [item for item in catalog if isinstance(item, dict)]
    exact = [item for item in valid_players if _norm(_player_name(item)) == requested]
    candidates = exact
    if not candidates:
        candidates = [
            item
            for item in valid_players
            if requested in {
                _norm(str(item.get("first_name", ""))),
                _norm(str(item.get("last_name", ""))),
                _norm(str(item.get("firstName", ""))),
                _norm(str(item.get("lastName", ""))),
            }
        ]

    if not candidates:
        raise AskResolutionError("not_found", "No matching player was found.")
    if len(candidates) > 1:
        raise AskResolutionError(
            "needs_clarification", "Several players match that name. Please use the full name."
        )

    player_id = candidates[0].get("id", candidates[0].get("personId"))
    if isinstance(player_id, bool) or not re.fullmatch(r"\d+", str(player_id or "")):
        raise _bad_response("Player catalog row has an invalid player ID")
    return str(player_id)


def _bad_response(message: str, cause: Exception | None = None) -> nba_stats_client.UpstreamBadResponseError:
    return nba_stats_client.UpstreamBadResponseError(
        endpoint="LeagueGameFinder",
        error_type="UnexpectedSchema",
        duration_ms=0,
        message=message if cause is None else f"{message}: {cause}",
    )


def _row_date(value: Any) -> date:
    if not isinstance(value, str):
        raise ValueError("GAME_DATE is not a string")
    raw = value.strip()
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ValueError("GAME_DATE has an invalid format")


def find_player_game_id(player_name: str, game_date: date) -> str:
    """Return the unique game ID for ``player_name`` on exactly ``game_date``."""
    player_id = _resolve_player_id(player_name)
    requested_date = game_date.strftime("%m/%d/%Y")
    try:
        response = nba_stats_client.fetch_league_game_finder(
            player_or_team_abbreviation="P",
            player_id_nullable=player_id,
            date_from_nullable=requested_date,
            date_to_nullable=requested_date,
            league_id_nullable="00",
        )
        normalized = response.get_normalized_dict()
    except (nba_stats_client.UpstreamUnavailableError, nba_stats_client.UpstreamBadResponseError):
        raise
    except Exception as error:
        raise _bad_response("LeagueGameFinder request failed", error) from error

    if not isinstance(normalized, dict):
        raise _bad_response("LeagueGameFinder normalized response is not an object")
    rows = normalized.get("LeagueGameFinderResults")
    if not isinstance(rows, list):
        raise _bad_response("LeagueGameFinder response has no row list")

    game_ids: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise _bad_response("LeagueGameFinder row is not an object")
        row_player_id = row.get("PLAYER_ID")
        game_id = row.get("GAME_ID")
        if isinstance(row_player_id, bool) or not re.fullmatch(r"\d+", str(row_player_id or "")):
            raise _bad_response("LeagueGameFinder row has an invalid PLAYER_ID")
        if not isinstance(game_id, str) or not re.fullmatch(r"\d+", game_id):
            raise _bad_response("LeagueGameFinder row has an invalid GAME_ID")
        try:
            row_day = _row_date(row.get("GAME_DATE"))
        except ValueError as error:
            raise _bad_response(str(error)) from error
        if str(row_player_id) == player_id and row_day == game_date:
            game_ids.add(game_id)

    if not game_ids:
        raise AskResolutionError("not_found", "No game was found for that player on the requested date.")
    if len(game_ids) > 1:
        raise AskResolutionError("needs_clarification", "Several games match that player and date.")
    return next(iter(game_ids))
