import pytest
from fastapi import HTTPException

from server import main
from server.services import game_summary
from server.services import playoffs
from server.utils.boxscore_availability import is_boxscore_available_metadata


class _FakeBoxScoreTraditional:
    def __init__(self, payload=None, error=None):
        self.payload = payload
        self.error = error

    def get_dict(self):
        if self.error:
            raise self.error
        return self.payload


def test_boxscore_metadata_available_for_started_supported_game():
    assert is_boxscore_available_metadata("0024600206", "2024-11-01", 2) is True


def test_boxscore_metadata_unavailable_for_scheduled_game():
    assert is_boxscore_available_metadata("0024600206", "2024-11-01", 1) is False


def test_boxscore_metadata_unavailable_for_invalid_game_id():
    assert is_boxscore_available_metadata("not-a-game", "2024-11-01", 2) is False


def test_boxscore_metadata_available_for_historical_started_game():
    assert is_boxscore_available_metadata("0024600206", "1996-10-31", 2) is True


class _FakeScoreboardV3:
    def __init__(self, *args, **kwargs):
        pass

    def get_dict(self):
        return {
            "scoreboard": {
                "games": [
                    {
                        "gameId": "0024600206",
                        "gameTimeUTC": "2024-11-01T23:00:00Z",
                        "gameStatus": 2,
                    },
                    {
                        "gameId": "0024600207",
                        "gameTimeUTC": "2024-11-01T23:30:00Z",
                        "gameStatus": 1,
                    },
                ],
            },
        }


def test_scoreboard_route_adds_boxscore_availability(monkeypatch):
    monkeypatch.setattr(main.scoreboardv3, "ScoreboardV3", _FakeScoreboardV3)

    result = main.get_v3_scoreboard(date="2024-11-01")

    assert result["games"][0]["boxscoreAvailable"] is True
    assert result["games"][1]["boxscoreAvailable"] is False


def test_playoff_normalization_adds_boxscore_availability():
    pandas = pytest.importorskip("pandas")
    rows = [
        {
            "GAME_ID": "0042300401",
            "GAME_DATE": "2024-06-06",
            "MATCHUP": "BOS vs. DAL",
            "TEAM_ID": 1610612738,
            "TEAM_ABBREVIATION": "BOS",
            "TEAM_NAME": "Celtics",
            "WL": "W",
            "PTS": 107,
        },
        {
            "GAME_ID": "0042300401",
            "GAME_DATE": "2024-06-06",
            "MATCHUP": "DAL @ BOS",
            "TEAM_ID": 1610612742,
            "TEAM_ABBREVIATION": "DAL",
            "TEAM_NAME": "Mavericks",
            "WL": "L",
            "PTS": 89,
        },
    ]

    result = playoffs.normalize_playoff_games(pandas.DataFrame(rows))

    assert result[0]["boxscoreAvailable"] is True


def test_existing_boxscore_endpoint_still_errors_on_upstream_failure(monkeypatch):
    def fake_boxscore(*args, **kwargs):
        return _FakeBoxScoreTraditional(error=RuntimeError("NBA endpoint failed"))

    monkeypatch.setattr(
        game_summary.boxscoretraditionalv3, "BoxScoreTraditionalV3", fake_boxscore
    )

    with pytest.raises(HTTPException) as exc:
        main.get_game_boxscore("0024600206")

    assert exc.value.status_code == 500
    assert "Failed to fetch boxscore" in exc.value.detail
