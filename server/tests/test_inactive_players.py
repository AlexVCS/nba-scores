from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd
import pytest
from fastapi import HTTPException
from requests.exceptions import Timeout

from server import main
from server.services import game_summary, nba_stats_client


def test_boxscore_does_not_request_inactive_players(monkeypatch):
    game = {"gameId": "123", "homeTeam": {"teamId": 1}, "awayTeam": {"teamId": 2}}
    monkeypatch.setattr(nba_stats_client, "fetch_boxscore_traditional",
                        lambda _: {"boxScoreTraditional": game})
    optional = Mock(side_effect=AssertionError("Optional lookup must not run"))
    monkeypatch.setattr(nba_stats_client, "fetch_boxscore_summary", optional)
    assert main.get_game_boxscore("123") == {"game": game}
    optional.assert_not_called()


def test_inactive_players_are_grouped_and_normalized(monkeypatch):
    frame = pd.DataFrame([
        {"TEAM_ID": 2, "PLAYER_ID": 20, "FIRST_NAME": " Away ", "LAST_NAME": "Player"},
        {"TEAM_ID": 1, "PLAYER_ID": 10, "FIRST_NAME": "Home", "LAST_NAME": "Player"},
        {"TEAM_ID": 1, "PLAYER_ID": None},
    ])
    fetch = Mock(return_value=SimpleNamespace(
        inactive_players=SimpleNamespace(get_data_frame=lambda: frame)))
    monkeypatch.setattr(nba_stats_client, "fetch_boxscore_summary", fetch)
    result = main.get_game_inactive_players("123")
    fetch.assert_called_once_with("123", timeout=2, retries=0)
    assert result["teams"]["2"][0]["firstName"] == "Away"
    assert [p["personId"] for p in result["teams"]["1"]] == [10]


@pytest.mark.parametrize("frame,expected_status", [(pd.DataFrame(), None), (None, 502)])
def test_empty_is_distinct_from_unavailable(monkeypatch, frame, expected_status):
    monkeypatch.setattr(nba_stats_client, "fetch_boxscore_summary", lambda *a, **k:
                        SimpleNamespace(inactive_players=SimpleNamespace(
                            get_data_frame=lambda: frame)))
    if expected_status:
        with pytest.raises(HTTPException) as error:
            main.get_game_inactive_players("123")
        assert error.value.status_code == expected_status
    else:
        assert main.get_game_inactive_players("123") == {"teams": {}}


@pytest.mark.parametrize("optional,attempts,timeout", [(True, 1, 2), (False, 3, 10)])
def test_optional_policy_preserves_default_retries(monkeypatch, optional, attempts, timeout):
    upstream = Mock(side_effect=Timeout("offline"))
    sleep = Mock()
    monkeypatch.setattr(nba_stats_client.boxscoresummaryv2, "BoxScoreSummaryV2", upstream)
    monkeypatch.setattr(nba_stats_client.time, "sleep", sleep)
    if optional:
        with pytest.raises(HTTPException) as error:
            main.get_game_inactive_players("123")
        assert error.value.status_code == 503
    else:
        with pytest.raises(nba_stats_client.UpstreamUnavailableError):
            nba_stats_client.fetch_boxscore_summary("123")
    assert upstream.call_count == attempts
    assert upstream.call_args.kwargs["timeout"] == timeout
    assert sleep.call_count == attempts - 1
