from datetime import date
from unittest.mock import Mock

import pytest

from server.services import ask_player_lookup, nba_stats_client
from server.services.ask_basketball import AskResolutionError


DAY = date(2024, 1, 2)
PLAYER = {"id": 1628983, "full_name": "Shai Gilgeous-Alexander", "first_name": "Shai", "last_name": "Gilgeous-Alexander"}


def response(*rows):
    return Mock(get_normalized_dict=lambda: {"LeagueGameFinderResults": list(rows)})


def row(game_id="0022300462", player_id=1628983, game_date="2024-01-02"):
    return {"SEASON_ID": "22023", "PLAYER_ID": player_id, "PLAYER_NAME": "Shai Gilgeous-Alexander", "GAME_ID": game_id, "GAME_DATE": game_date, "PTS": 36}


def test_finds_historical_player_game_and_deduplicates(monkeypatch):
    monkeypatch.setattr(ask_player_lookup.players, "get_players", lambda: [PLAYER])
    fetch = Mock(return_value=response(row(), row()))
    monkeypatch.setattr(ask_player_lookup.nba_stats_client, "fetch_league_game_finder", fetch)

    assert ask_player_lookup.find_player_game_id("Shai Gilgeous-Alexander", DAY) == "0022300462"
    fetch.assert_called_once_with(
        player_or_team_abbreviation="P", player_id_nullable="1628983",
        date_from_nullable="01/02/2024", date_to_nullable="01/02/2024", league_id_nullable="00",
    )


def test_accepts_finder_date_format_and_unique_surname(monkeypatch):
    monkeypatch.setattr(ask_player_lookup.players, "get_players", lambda: [PLAYER])
    monkeypatch.setattr(ask_player_lookup.nba_stats_client, "fetch_league_game_finder", lambda **_: response(row(game_date="01/02/2024")))
    assert ask_player_lookup.find_player_game_id("Gilgeous-Alexander", DAY) == "0022300462"


@pytest.mark.parametrize("rows", [
    (),
    (row(game_date="2024-01-03"),),
    (row(player_id=2544),),
])
def test_no_matching_exact_date_player_is_not_found(monkeypatch, rows):
    monkeypatch.setattr(ask_player_lookup.players, "get_players", lambda: [PLAYER])
    monkeypatch.setattr(ask_player_lookup.nba_stats_client, "fetch_league_game_finder", lambda **_: response(*rows))
    with pytest.raises(AskResolutionError) as error:
        ask_player_lookup.find_player_game_id("Shai Gilgeous-Alexander", DAY)
    assert error.value.status == "not_found"


def test_multiple_games_need_clarification(monkeypatch):
    monkeypatch.setattr(ask_player_lookup.players, "get_players", lambda: [PLAYER])
    monkeypatch.setattr(ask_player_lookup.nba_stats_client, "fetch_league_game_finder", lambda **_: response(row("1"), row("2")))
    with pytest.raises(AskResolutionError) as error:
        ask_player_lookup.find_player_game_id("Shai Gilgeous-Alexander", DAY)
    assert error.value.status == "needs_clarification"


def test_unknown_player_does_not_call_provider(monkeypatch):
    monkeypatch.setattr(ask_player_lookup.players, "get_players", lambda: [PLAYER])
    fetch = Mock()
    monkeypatch.setattr(ask_player_lookup.nba_stats_client, "fetch_league_game_finder", fetch)
    with pytest.raises(AskResolutionError) as error:
        ask_player_lookup.find_player_game_id("Shai Gilgeous", DAY)
    assert error.value.status == "not_found"
    fetch.assert_not_called()


def test_ambiguous_first_or_last_name_needs_clarification(monkeypatch):
    monkeypatch.setattr(ask_player_lookup.players, "get_players", lambda: [PLAYER, {"id": 2, "full_name": "Shai Brown", "first_name": "Shai", "last_name": "Brown"}])
    with pytest.raises(AskResolutionError) as error:
        ask_player_lookup.find_player_game_id("Shai", DAY)
    assert error.value.status == "needs_clarification"


def test_malformed_provider_row_fails_closed(monkeypatch):
    monkeypatch.setattr(ask_player_lookup.players, "get_players", lambda: [PLAYER])
    monkeypatch.setattr(ask_player_lookup.nba_stats_client, "fetch_league_game_finder", lambda **_: response({"PLAYER_ID": 1628983, "GAME_ID": "bad", "GAME_DATE": "2024-01-02"}))
    with pytest.raises(nba_stats_client.UpstreamBadResponseError):
        ask_player_lookup.find_player_game_id("Shai Gilgeous-Alexander", DAY)
