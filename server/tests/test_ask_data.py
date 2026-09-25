from datetime import date
from unittest.mock import Mock

import pytest

from server.services import ask_data, nba_stats_client
from server.models.ask_response import AskResponse
from server.services.ask_basketball import ResolvedRequest


def req(intent="game_search", **kw):
    base = dict(intent=intent, operation="list", start_date=date(2024, 1, 1), end_date=date(2024, 1, 1), team_ids=(1,), season="2023-24")
    base.update(kw)
    return ResolvedRequest(**base)


def board(*games): return {"games": list(games)}
def game(gid="001", status=3, date_value="2024-01-01"): return {
    "gameId": gid, "gameCode": "20240101/LALBOS", "gameStatus": status,
    "gameLabel": "", "gameSubLabel": "", "gameTimeUTC": "2024-01-02T00:30:00Z",
    "gameStatusText": "Final" if status == 3 else "7:30 pm ET",
    "ifNecessary": False, "seriesGameNumber": "", "seriesText": "",
    "boxscoreAvailable": status == 3, "gameDate": date_value,
    "homeTeam": {"teamId": 1, "teamName": "Celtics", "teamTricode": "BOS", "score": 100},
    "awayTeam": {"teamId": 2, "teamName": "Lakers", "teamTricode": "LAL", "score": 90},
}


def test_game_search_uses_requested_date_for_link(monkeypatch):
    source = game()
    monkeypatch.setattr(ask_data.nba_stats_client, "fetch_scoreboard_v3", lambda _: board(source))
    response, complete = ask_data.retrieve_answer(req())
    assert response["status"] == "ok" and complete
    assert response["items"][0]["links"][0]["path"] == "/games/001/boxscore?date=2024-01-01"
    assert response["items"][0]["context"] == "Jan 1, 2024"
    assert [team["id"] for team in response["items"][0]["teams"]] == [2, 1]
    assert response["items"][0]["game"] == source
    assert response["items"][0]["game"]["gameStatus"] == 3
    assert response["items"][0]["game"]["homeTeam"]["score"] == 100
    assert response["items"][0]["game"]["awayTeam"]["score"] == 90
    assert response["items"][0]["game"]["boxscoreAvailable"] is True
    validated = AskResponse.model_validate(response).model_dump()["items"][0]["game"]
    assert validated == source


def test_game_search_empty_is_not_found(monkeypatch):
    monkeypatch.setattr(ask_data.nba_stats_client, "fetch_scoreboard_v3", lambda _: board())
    assert ask_data.retrieve_answer(req())[0]["status"] == "not_found"


def test_game_search_outage_is_unavailable(monkeypatch):
    monkeypatch.setattr(ask_data.nba_stats_client, "fetch_scoreboard_v3", Mock(side_effect=nba_stats_client.UpstreamUnavailableError("x", "Timeout", 1)))
    assert ask_data.retrieve_answer(req())[0]["status"] == "unavailable"


def test_boxscore_ambiguous_games_clarifies(monkeypatch):
    monkeypatch.setattr(ask_data.nba_stats_client, "fetch_scoreboard_v3", lambda _: board(game("001"), game("002")))
    assert ask_data.retrieve_answer(req("boxscore_stats", season=None, statistics=("points",)))[0]["status"] == "needs_clarification"


def test_boxscore_value_error_is_not_found(monkeypatch):
    monkeypatch.setattr(ask_data.nba_stats_client, "fetch_scoreboard_v3", lambda _: board(game()))
    monkeypatch.setattr(ask_data, "fetch_boxscoretraditional", Mock(side_effect=ValueError("missing")))
    assert ask_data.retrieve_answer(req("boxscore_stats", season=None, statistics=("points",)))[0]["status"] == "not_found"


def test_boxscore_upstream_is_unavailable(monkeypatch):
    monkeypatch.setattr(ask_data.nba_stats_client, "fetch_scoreboard_v3", lambda _: board(game()))
    monkeypatch.setattr(ask_data, "fetch_boxscoretraditional", Mock(side_effect=nba_stats_client.UpstreamUnavailableError("x", "Timeout", 1)))
    assert ask_data.retrieve_answer(req("boxscore_stats", season=None, statistics=("points",)))[0]["status"] == "unavailable"


def test_playoff_boxscore_game_number_fetches_selected_id_and_returns_points(monkeypatch):
    payload = playoff_payload()
    payload["series"][0]["games"] = [{"gameId": "002", "date": "2024-05-01"}, {"gameId": "001", "date": "2024-04-25"}]
    monkeypatch.setattr(ask_data, "get_playoff_games_and_series", lambda _: payload)
    fetched = []
    monkeypatch.setattr(ask_data, "fetch_boxscoretraditional", lambda game_id: fetched.append(game_id) or {"homeTeam": {"teamId": 1, "teamName": "Boston Celtics", "players": [{"firstName": "A", "familyName": "Player", "statistics": {"points": 42}}]}, "awayTeam": {"teamId": 2, "players": []}})
    response, _ = ask_data.retrieve_answer(req("boxscore_stats", start_date=None, end_date=None, game_number=1, statistics=("points",)))
    assert fetched == ["001"]
    assert response["items"][0]["fields"][0]["value"] == 42


def test_scheduled_game_hides_scores(monkeypatch):
    source = game(status=1)
    source.pop("boxscoreAvailable")
    monkeypatch.setattr(ask_data.nba_stats_client, "fetch_scoreboard_v3", lambda _: board(source))
    response, _ = ask_data.retrieve_answer(req())
    assert all(field["label"] not in {"Away score", "Home score"} for field in response["items"][0]["fields"])
    assert response["items"][0]["game"]["boxscoreAvailable"] is False


def test_completed_game_uses_shared_boxscore_availability_metadata(monkeypatch):
    source = game(gid="0022300462")
    source.pop("boxscoreAvailable")
    monkeypatch.setattr(ask_data.nba_stats_client, "fetch_scoreboard_v3", lambda _: board(source))
    response, _ = ask_data.retrieve_answer(req())
    assert response["items"][0]["game"]["boxscoreAvailable"] is True


def playoff_payload():
    s = {"round": 4, "roundName": "NBA Finals", "isFinals": True, "teams": [{"id": 1}, {"id": 2}], "games": [{"gameId": "004", "date": "2024-06-01", "homeTeam": {"id":1,"name":"Boston"}, "awayTeam": {"id":2,"name":"Los Angeles"}, "winnerTeamId":1}], "wins": {"1": 1, "2": 0}, "winnerTeamId": 1}
    return {"series": [s], "games": s["games"]}


def test_playoff_uses_combined_payload_and_link(monkeypatch):
    monkeypatch.setattr(ask_data, "get_playoff_games_and_series", lambda _: playoff_payload())
    response, complete = ask_data.retrieve_answer(req("playoff_series", start_date=None, end_date=None, team_ids=(1,), round_mention="finals"))
    assert response["status"] == "ok" and response["items"][0]["links"][0]["path"] == "/playoffs/2024/the-finals"
    assert complete is False


def test_playoff_game_number_selects_single_game(monkeypatch):
    monkeypatch.setattr(ask_data, "get_playoff_games_and_series", lambda _: playoff_payload())
    monkeypatch.setattr(ask_data, "fetch_boxscoretraditional", lambda _: {"homeTeam":{"teamId":1,"teamName":"Boston","statistics":{"points":100}},"awayTeam":{}})
    response, _ = ask_data.retrieve_answer(req("boxscore_stats", operation="team_stats", statistics=("points",), start_date=None, end_date=None, team_ids=(1,), game_number=1, round_mention="finals"))
    assert response["items"][0]["links"][0]["path"].startswith("/games/004/boxscore")


def test_playoff_game_number_out_of_range(monkeypatch):
    monkeypatch.setattr(ask_data, "get_playoff_games_and_series", lambda _: playoff_payload())
    response, _ = ask_data.retrieve_answer(req("boxscore_stats", operation="team_stats", statistics=("points",), start_date=None, end_date=None, team_ids=(1,), game_number=2, round_mention="finals"))
    assert response["status"] == "not_found"


def test_postseason_summary_never_marks_complete(monkeypatch):
    monkeypatch.setattr(ask_data, "get_playoff_games_and_series", lambda _: playoff_payload())
    response, complete = ask_data.retrieve_answer(req("postseason_summary", start_date=None, end_date=None, team_ids=(1,)))
    assert response["status"] == "ok" and complete is False


def test_no_bracket_metadata_uses_safe_bracket_link(monkeypatch):
    payload = playoff_payload(); payload["series"][0].pop("isFinals")
    monkeypatch.setattr(ask_data, "get_playoff_games_and_series", lambda _: payload)
    response, _ = ask_data.retrieve_answer(req("playoff_series", start_date=None, end_date=None, team_ids=(1,), round_mention="finals"))
    assert response["status"] == "ok"



def test_player_date_lookup_selects_one_game_without_a_team(monkeypatch):
    from server.services import ask_player_lookup
    monkeypatch.setattr(ask_data.nba_stats_client, "fetch_scoreboard_v3", lambda _: board(game("001"), game("002")))
    lookup = Mock(return_value="002")
    monkeypatch.setattr(ask_player_lookup, "find_player_game_id", lookup)
    fetch = Mock(return_value={"homeTeam": {"teamId": 1, "players": [{"firstName": "Shai", "familyName": "Gilgeous-Alexander", "statistics": {"points": 36}}]}, "awayTeam": {"teamId": 2}})
    monkeypatch.setattr(ask_data, "fetch_boxscoretraditional", fetch)
    response, complete = ask_data.retrieve_answer(req("boxscore_stats", operation="player_stats", season=None, team_ids=(), player_name="Shai Gilgeous-Alexander", statistics=("points",)))
    lookup.assert_called_once_with("Shai Gilgeous-Alexander", date(2024, 1, 1))
    fetch.assert_called_once_with("002")
    assert response["status"] == "ok" and complete
    item = response["items"][0]
    assert item["fields"][0] == {"label": "Points", "value": 36, "spoiler": True}
    assert item["context"] == "Jan 1, 2024"
    assert item["links"][0]["path"] == "/games/002/boxscore?date=2024-01-01"


def test_player_game_must_appear_on_requested_date_scoreboard(monkeypatch):
    from server.services import ask_player_lookup
    monkeypatch.setattr(ask_data.nba_stats_client, "fetch_scoreboard_v3", lambda _: board(game("001")))
    monkeypatch.setattr(ask_player_lookup, "find_player_game_id", lambda *_: "002")
    monkeypatch.setattr(ask_data, "fetch_boxscoretraditional", lambda *_: pytest.fail("Fetched an unverified game"))
    response, _ = ask_data.retrieve_answer(req("boxscore_stats", operation="player_stats", season=None, team_ids=(), player_name="Shai Gilgeous-Alexander", statistics=("points",)))
    assert response["status"] == "not_found"
