from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pandas as pd
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from server import main
from server.services import game_details as details, nba_schedule, scoreboard

GAME_ID = "0012600009"


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
    monkeypatch.setattr(details.nba_stats_client, "fetch_scoreboard_v3", lambda *_, **__: {"games": [game(status, text)]})
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
            "GAME_ID": "0024600001", "GAME_DATE_EST": "1946-11-01T00:00:00", "GAME_STATUS_ID": 3, "LIVE_PERIOD": 4,
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

    monkeypatch.setattr(nba_schedule._schedule_cooldowns, "_clock", lambda: now[0])
    monkeypatch.setattr(details.nba_stats_client, "fetch_schedule_league_v2", fail)
    with pytest.raises(details.nba_stats_client.UpstreamUnavailableError):
        details._schedule_game(GAME_ID)
    with pytest.raises(details.nba_stats_client.UpstreamUnavailableError) as cooling:
        details._schedule_game(GAME_ID)
    assert isinstance(cooling.value.__cause__, nba_schedule.ScheduleLookupCooldownError)
    assert calls == ["2026-27"]
    now[0] += 60
    with pytest.raises(details.nba_stats_client.UpstreamUnavailableError):
        details._schedule_game(GAME_ID)
    assert calls == ["2026-27", "2026-27"]


OTHER_GAME_ID = "0012600010"


@pytest.fixture
def details_sources(monkeypatch):
    """Upstream doubles for the scoreboard and season schedule with controllable clocks."""
    now = [1000.0]
    monkeypatch.setattr(scoreboard._scoreboard_cache, "_clock", lambda: now[0])
    monkeypatch.setattr(nba_schedule._schedule_cache, "_clock", lambda: now[0])
    sources = SimpleNamespace(now=now, statuses=[1], board_calls=[], schedule_calls=[])

    def fetch_board(game_date, **_):
        sources.board_calls.append(game_date)
        status = sources.statuses.pop(0) if len(sources.statuses) > 1 else sources.statuses[0]
        return {"games": [game(status, "Q1" if status == 2 else "7:00 pm ET"), {**game(), "gameId": OTHER_GAME_ID}]}

    def fetch_schedule(season, **_):
        sources.schedule_calls.append(season)
        games = [{**game(), "gameId": game_id, "arenaName": "Scotiabank Arena"} for game_id in (GAME_ID, OTHER_GAME_ID)]
        return endpoint({"leagueSchedule": {"gameDates": [{"gameDate": "10/04/2026 00:00:00", "games": games}]}})

    def no_player_stats(*_):
        raise AssertionError("details must not fetch player statistics")

    monkeypatch.setattr(details.nba_stats_client, "fetch_scoreboard_v3", fetch_board)
    monkeypatch.setattr(details.nba_stats_client, "fetch_schedule_league_v2", fetch_schedule)
    monkeypatch.setattr(details.nba_stats_client, "fetch_boxscore_traditional", no_player_stats)
    return sources


def test_games_on_one_date_share_scoreboard_and_schedule(details_sources):
    first = details.fetch_game_details(GAME_ID, "2026-10-04")
    second = details.fetch_game_details(OTHER_GAME_ID, "2026-10-04")
    assert (first["venue"], second["venue"]) == ("Scotiabank Arena", "Scotiabank Arena")
    assert details_sources.board_calls == ["2026-10-04"]
    assert details_sources.schedule_calls == ["2026-27"]


def test_polling_reuses_schedule_but_refreshes_expired_scoreboard(details_sources):
    details.fetch_game_details(GAME_ID, "2026-10-04")
    details_sources.now[0] += 60
    result = details.fetch_game_details(GAME_ID, "2026-10-04")
    assert result["venue"] == "Scotiabank Arena"
    assert details_sources.board_calls == ["2026-10-04", "2026-10-04"]
    assert details_sources.schedule_calls == ["2026-27"]


def test_scheduled_to_live_transition_is_not_masked_by_cached_schedule(details_sources):
    details_sources.statuses[:] = [1, 2]
    pregame = details.fetch_game_details(GAME_ID, "2026-10-04")
    assert (pregame["gameStatus"], pregame["boxscoreAvailable"]) == (1, False)

    details_sources.now[0] += scoreboard.SCHEDULED_TTL_SECONDS
    live = details.fetch_game_details(GAME_ID, "2026-10-04")
    assert (live["gameStatus"], live["gameStatusText"], live["boxscoreAvailable"]) == (2, "Q1", True)
    assert details_sources.schedule_calls == ["2026-27"]


def test_scores_route_and_details_share_todays_scoreboard(monkeypatch, details_sources):
    monkeypatch.setattr(main, "nba_today", lambda: date(2026, 10, 4))
    body = TestClient(main.app).get("/").json()
    assert body["games"][0]["boxscoreAvailable"] is False
    assert details.fetch_game_details(GAME_ID, "2026-10-04")["gameStatus"] == 1
    assert details_sources.board_calls == ["2026-10-04"]


def test_schedule_only_final_status_is_not_authoritative(monkeypatch):
    error = details.nba_stats_client.UpstreamUnavailableError("BoxScoreSummaryV3", "Timeout", 10)

    def unavailable(_):
        raise error

    monkeypatch.setattr(details.nba_stats_client, "fetch_boxscore_summary_v3", unavailable)
    monkeypatch.setattr(details.nba_stats_client, "fetch_boxscore_summary", unavailable)
    monkeypatch.setattr(details, "_schedule_game", lambda _: game(3, "Final"))
    with pytest.raises(details.nba_stats_client.UpstreamUnavailableError):
        details.fetch_game_details(GAME_ID)


@pytest.mark.parametrize(("status", "text"), [(2, "Q3 5:00"), (3, "Final")])
def test_schedule_only_started_status_without_summaries_is_unavailable(monkeypatch, status, text):
    monkeypatch.setattr(details.nba_stats_client, "fetch_boxscore_summary_v3", lambda _: endpoint({}))
    monkeypatch.setattr(details, "_legacy_game", lambda _: None)
    monkeypatch.setattr(details, "_schedule_game", lambda _: game(status, text))
    with pytest.raises(ValueError, match="Game details unavailable"):
        details.fetch_game_details(GAME_ID)
    response = TestClient(main.app).get(f"/games/{GAME_ID}/details")
    assert response.status_code == 404


def test_schedule_only_final_defers_to_legacy_status_and_keeps_enrichment(monkeypatch):
    monkeypatch.setattr(details.nba_stats_client, "fetch_boxscore_summary_v3", lambda _: endpoint({}))
    monkeypatch.setattr(details, "_schedule_game", lambda _: {**game(2, "Q4"), "arenaName": "Scotiabank Arena"})
    monkeypatch.setattr(details, "_legacy_game", lambda _: game(3, "Final"))
    result = details.fetch_game_details(GAME_ID)
    assert (result["gameStatus"], result["gameStatusText"]) == (3, "Final")
    assert result["venue"] == "Scotiabank Arena"


def test_schedule_only_pregame_fallback_is_preserved(monkeypatch):
    monkeypatch.setattr(details.nba_stats_client, "fetch_boxscore_summary_v3", lambda _: endpoint({}))
    monkeypatch.setattr(details, "_schedule_game", lambda _: {**game(), "arenaName": "Scotiabank Arena"})
    monkeypatch.setattr(details, "_legacy_game", Mock(side_effect=AssertionError("pregame schedule suffices")))
    result = details.fetch_game_details(GAME_ID)
    assert (result["gameStatus"], result["venue"]) == (1, "Scotiabank Arena")


def test_schedule_game_mutation_does_not_alter_cached_schedule(monkeypatch):
    scheduled = {**game(), "arena": {"arenaName": "Scotiabank Arena"}}
    monkeypatch.setattr(
        details.nba_stats_client,
        "fetch_schedule_league_v2",
        lambda *_, **__: endpoint({"leagueSchedule": {"gameDates": [{"games": [scheduled]}]}}),
    )
    first = details._schedule_game(GAME_ID)
    first["arena"]["arenaName"] = "Changed"
    first["gameStatus"] = 3
    second = details._schedule_game(GAME_ID)
    assert (second["arena"]["arenaName"], second["gameStatus"]) == ("Scotiabank Arena", 1)


def test_details_route_stays_unavailable_during_schedule_cooldown(monkeypatch):
    calls = []

    def fail(season, **kwargs):
        calls.append(season)
        raise details.nba_stats_client.UpstreamUnavailableError("ScheduleLeagueV2", "Timeout", 10)

    legacy = SimpleNamespace(game_summary=SimpleNamespace(get_data_frame=pd.DataFrame), line_score=SimpleNamespace(get_data_frame=pd.DataFrame))
    monkeypatch.setattr(details.nba_stats_client, "fetch_boxscore_summary_v3", lambda _: endpoint({}))
    monkeypatch.setattr(details.nba_stats_client, "fetch_boxscore_summary", lambda _: legacy)
    monkeypatch.setattr(details.nba_stats_client, "fetch_schedule_league_v2", fail)
    client = TestClient(main.app)
    responses = [client.get(f"/games/{GAME_ID}/details") for _ in range(2)]
    assert [response.status_code for response in responses] == [503, 503]
    assert responses[1].json()["detail"]["endpoint"] == "ScheduleLeagueV2"
    assert calls == ["2026-27"]


def test_summary_details_skip_enrichment_during_schedule_cooldown(monkeypatch):
    def fail(season, **kwargs):
        raise details.nba_stats_client.UpstreamUnavailableError("ScheduleLeagueV2", "Timeout", 10)

    monkeypatch.setattr(details.nba_stats_client, "fetch_boxscore_summary_v3", lambda _: endpoint({"boxScoreSummary": game()}))
    monkeypatch.setattr(details.nba_stats_client, "fetch_schedule_league_v2", fail)
    monkeypatch.setattr(details, "_legacy_game", Mock(side_effect=AssertionError("summary V3 suffices")))
    client = TestClient(main.app)
    assert client.get(f"/games/{GAME_ID}/details").status_code == 200
    monkeypatch.setattr(details.nba_stats_client, "fetch_schedule_league_v2", Mock(side_effect=AssertionError("cooling down")))
    response = client.get(f"/games/{GAME_ID}/details")
    assert response.status_code == 200
    body = response.json()
    assert (body["gameStatus"], body["homeTeam"]["teamTricode"]) == (1, "TOR")
    assert (body["venue"], body["broadcast"]) == (None, None)
