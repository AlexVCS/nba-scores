from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pandas as pd
import pytest
from fastapi import HTTPException

from server import main
from server.services import game_details as details

GAME_ID = "0012600009"


@pytest.fixture(autouse=True)
def clear_schedule_cache():
    details._schedule_cache.clear()
    details._schedule_failures.clear()
    yield
    details._schedule_cache.clear()
    details._schedule_failures.clear()


def game(status=1, status_text="7:00 pm ET"):
    return {
        "gameId": GAME_ID,
        "gameStatus": status,
        "gameStatusText": status_text,
        "gameTimeUTC": "2026-10-04T23:00:00Z",
        "homeTeam": {"teamId": 1610612761, "teamCity": "Toronto", "teamName": "Raptors", "teamTricode": "TOR", "score": 111},
        "awayTeam": {"teamId": 1610612748, "teamName": "Heat", "teamTricode": "MIA", "score": 100},
        "period": 5,
    }


def endpoint(payload):
    return SimpleNamespace(get_dict=lambda: payload)


def test_direct_upcoming_lookup_includes_schedule_details_without_stats(monkeypatch):
    monkeypatch.setattr(details.nba_stats_client, "fetch_boxscore_summary_v3", lambda _: endpoint({"boxScoreSummary": game()}))
    scheduled = {**game(), "arenaName": "Scotiabank Arena", "broadcasters": {"nationalBroadcasters": [{"broadcasterDisplay": "ESPN"}, {"broadcasterDisplay": "ESPN"}]}}

    def schedule(season, **kwargs):
        assert season == "2026-27"
        return endpoint({"leagueSchedule": {"gameDates": [{"gameDate": "10/04/2026 00:00:00", "games": [scheduled]}]}})

    monkeypatch.setattr(details.nba_stats_client, "fetch_schedule_league_v2", schedule)
    result = details.fetch_game_details(GAME_ID)
    assert result["gameDate"] == "2026-10-04"
    assert result["venue"] == "Scotiabank Arena"
    assert result["broadcast"] == "ESPN"
    assert result["homeTeam"] == {"teamId": 1610612761, "teamTricode": "TOR", "teamName": "Toronto Raptors"}
    assert result["boxscoreAvailable"] is False
    assert "score" not in result["homeTeam"]
    assert "period" not in result


@pytest.mark.parametrize("arena_fields,expected", [
    ({"arenaName": "Fiserv Forum", "arenaCity": "Milwaukee", "arenaState": "WI"}, ("Fiserv Forum", "Milwaukee", "WI")),
    ({"arena": {"arenaName": "Fiserv Forum", "arenaCity": "Milwaukee", "arenaState": "WI"}}, ("Fiserv Forum", "Milwaukee", "WI")),
    ({"arenaName": "Fiserv Forum", "arenaCity": "", "arena": {"arenaCity": "Milwaukee"}}, ("Fiserv Forum", "Milwaukee", None)),
    ({}, (None, None, None)),
])
def test_venue_city_and_state(monkeypatch, arena_fields, expected):
    monkeypatch.setattr(details.nba_stats_client, "fetch_boxscore_summary_v3", lambda _: endpoint({"boxScoreSummary": game()}))
    monkeypatch.setattr(details, "_schedule_game", lambda _: {**game(), **arena_fields})
    result = details.fetch_game_details(GAME_ID)
    assert (result["venue"], result["venueCity"], result["venueState"]) == expected


@pytest.mark.parametrize("status,text,available", [(2, "Q2", True), (3, "Final/OT", True), (1, "TBD", False), (2, "Postponed", False), (3, "Cancelled", False)])
def test_date_hint_and_lifecycle(monkeypatch, status, text, available):
    monkeypatch.setattr(details.nba_stats_client, "fetch_scoreboard_v3", lambda _: {"games": [game(status, text)]})
    monkeypatch.setattr(details, "_schedule_game", lambda _: None)
    result = details.fetch_game_details(GAME_ID, "2026-10-04")
    assert result["gameStatusText"] == text
    assert result["boxscoreAvailable"] is available
    assert result["gameDate"] == "2026-10-04"


def test_empty_summary_falls_back_to_published_schedule(monkeypatch):
    monkeypatch.setattr(details.nba_stats_client, "fetch_boxscore_summary_v3", lambda _: endpoint({"boxScoreSummary": None}))
    monkeypatch.setattr(details, "_schedule_game", lambda _: game())
    assert details.fetch_game_details(GAME_ID)["awayTeam"]["teamTricode"] == "MIA"


def test_legacy_direct_link_works_without_player_stats(monkeypatch):
    monkeypatch.setattr(details.nba_stats_client, "fetch_boxscore_summary_v3", lambda _: endpoint({}))
    monkeypatch.setattr(details, "_schedule_game", lambda _: None)
    summary = SimpleNamespace(
        game_summary=SimpleNamespace(get_data_frame=lambda: pd.DataFrame([{
            "GAME_DATE_EST": "1946-11-01T00:00:00", "GAME_STATUS_ID": 3,
            "GAME_STATUS_TEXT": "Final", "HOME_TEAM_ID": 1, "VISITOR_TEAM_ID": 2,
            "GAMECODE": "19461101/NYKHUS",
        }])),
        line_score=SimpleNamespace(get_data_frame=lambda: pd.DataFrame()),
    )
    monkeypatch.setattr(details.nba_stats_client, "fetch_boxscore_summary", lambda _: summary)
    result = details.fetch_game_details("0024600001")
    assert result["gameDate"] == "1946-11-01"
    assert result["homeTeam"]["teamTricode"] == "HUS"
    assert result["awayTeam"]["teamTricode"] == "NYK"
    assert result["gameTimeUTC"] is None
    assert result["venue"] is None
    assert result["venueCity"] is None
    assert result["venueState"] is None


def test_invalid_game_is_not_requested_upstream():
    with pytest.raises(HTTPException) as exc:
        main.get_game_details("invalid", date=None)
    assert exc.value.status_code == 404


def test_details_upstream_failure_is_retryable(monkeypatch):
    error = details.nba_stats_client.UpstreamUnavailableError("ScoreboardV3", "Timeout", 100)

    def fail(*args):
        raise error

    monkeypatch.setattr(main, "fetch_game_details", fail)
    with pytest.raises(HTTPException) as exc:
        main.get_game_details(GAME_ID, date=None)
    assert exc.value.status_code == 503


def test_schedule_is_fetched_once_per_season(monkeypatch):
    calls = []

    def schedule(season, **kwargs):
        calls.append(season)
        return endpoint({"leagueSchedule": {"gameDates": [{"gameDate": "10/04/2026 00:00:00", "games": [{**game(), "arenaName": "Scotiabank Arena"}]}]}})

    monkeypatch.setattr(details.nba_stats_client, "fetch_schedule_league_v2", schedule)
    assert details._schedule_game(GAME_ID)["arenaName"] == "Scotiabank Arena"
    assert details._schedule_game(GAME_ID)["gameDate"] == "10/04/2026 00:00:00"
    assert details._schedule_game("0012600010") is None
    assert calls == ["2026-27"]


def test_concurrent_schedule_requests_share_one_fetch(monkeypatch):
    entered, release, second_started = Event(), Event(), Event()
    calls = []

    def schedule(season, **kwargs):
        calls.append(season)
        entered.set()
        assert release.wait(2)
        return endpoint({"leagueSchedule": {"gameDates": [{"games": [game()]}]}})

    def second_lookup():
        second_started.set()
        return details._schedule_game(GAME_ID)

    monkeypatch.setattr(details.nba_stats_client, "fetch_schedule_league_v2", schedule)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(details._schedule_game, GAME_ID)
        try:
            assert entered.wait(2)
            second = pool.submit(second_lookup)
            assert second_started.wait(2)
        finally:
            release.set()
        assert first.result() == second.result()
    assert calls == ["2026-27"]


def test_schedule_failure_cools_down_then_retries(monkeypatch):
    calls = []
    now = [100.0]

    def fail(season, **kwargs):
        calls.append(season)
        raise details.nba_stats_client.UpstreamUnavailableError("ScheduleLeagueV2", "Timeout", 10)

    monkeypatch.setattr(details.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(details.nba_stats_client, "fetch_schedule_league_v2", fail)
    with pytest.raises(details.nba_stats_client.UpstreamUnavailableError):
        details._schedule_game(GAME_ID)
    assert details._schedule_game(GAME_ID) is None
    assert calls == ["2026-27"]
    now[0] += 60
    with pytest.raises(details.nba_stats_client.UpstreamUnavailableError):
        details._schedule_game(GAME_ID)
    assert calls == ["2026-27", "2026-27"]
