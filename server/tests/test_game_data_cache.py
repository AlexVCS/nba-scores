import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Event
from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from server import main
from server.services import game_data, game_details, game_summary, nba_stats_client
from server.services.game_data import GameMetadata
from server.utils.season import NBA_TIMEZONE

GAME_ID = "0022500100"
OTHER_GAME_ID = "0022500101"
HOME, AWAY = 1610612761, 1610612748
NOW = datetime(2026, 1, 20, 21, 0, tzinfo=NBA_TIMEZONE)
TIPOFF = datetime(2026, 1, 20, 19, 0, tzinfo=NBA_TIMEZONE)
STATUS_TEXT = {1: "7:00 pm ET", 2: "Q2 5:00", 3: "Final"}


def summary(status=3, tipoff=TIPOFF, game_id=GAME_ID):
    def team(team_id, tricode, score):
        periods = [{"period": period, "score": score // 4} for period in range(1, 5)]
        return {"teamId": team_id, "teamTricode": tricode, "teamCity": "City", "teamName": tricode, "score": score, "periods": periods}

    return {
        "gameId": game_id,
        "gameCode": f"{tipoff:%Y%m%d}/MIATOR",
        "gameStatus": status,
        "gameStatusText": STATUS_TEXT[status],
        "gameTimeUTC": tipoff.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "gameEt": tipoff.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "period": 4,
        "homeTeam": team(HOME, "TOR", 100),
        "awayTeam": team(AWAY, "MIA", 96),
    }


def endpoint(game):
    return SimpleNamespace(get_dict=lambda: {"boxScoreSummary": game})


def legacy(status=3, game_date="1946-11-01T00:00:00"):
    rows = [{"GAME_DATE_EST": game_date, "GAME_STATUS_ID": status, "GAME_STATUS_TEXT": "Final", "GAMECODE": "19461101/MIATOR",
             "HOME_TEAM_ID": HOME, "VISITOR_TEAM_ID": AWAY, "LIVE_PERIOD": 4}]
    line_score = [
        {"TEAM_ID": team_id, "TEAM_ABBREVIATION": tricode, "TEAM_CITY_NAME": "City", "TEAM_NICKNAME": tricode, "PTS": pts,
         **{f"PTS_QTR{q}": pts // 4 for q in range(1, 5)}}
        for team_id, tricode, pts in ((HOME, "TOR", 100), (AWAY, "MIA", 96))
    ]
    return SimpleNamespace(
        game_summary=SimpleNamespace(get_data_frame=lambda: pd.DataFrame(rows)),
        line_score=SimpleNamespace(get_data_frame=lambda: pd.DataFrame(line_score)),
    )


def boxscore(game_id=GAME_ID):
    return {"boxScoreTraditional": {
        "gameId": game_id,
        "homeTeamId": HOME,
        "awayTeamId": AWAY,
        "homeTeam": {"teamId": HOME, "players": [{"personId": 1, "comment": ""}, {"personId": 2, "comment": "DNP - Coach's Decision"}]},
        "awayTeam": {"teamId": AWAY, "players": [{"personId": 3, "comment": ""}]},
    }}


@pytest.fixture
def clock(monkeypatch):
    now = [1000.0]
    for cache in (game_data._boxscore_cache, game_data._summary_v3_cache, game_data._summary_v2_cache):
        monkeypatch.setattr(cache, "_clock", lambda: now[0])
    monkeypatch.setattr(game_data, "nba_now", lambda: NOW + timedelta(seconds=now[0] - 1000))
    return now


@pytest.fixture
def upstream(monkeypatch, clock):
    """Upstream doubles; repair and schedule lookups fail loudly unless a test opts in."""
    sources = SimpleNamespace(
        v3=Mock(side_effect=lambda game_id, **_: endpoint(summary(game_id=game_id))),
        v2=Mock(side_effect=lambda game_id, **_: legacy()),
        box=Mock(side_effect=lambda game_id: boxscore(game_id)),
        bref=Mock(side_effect=AssertionError("metadata must not request linescore repair")),
    )
    monkeypatch.setattr(nba_stats_client, "fetch_boxscore_summary_v3", sources.v3)
    monkeypatch.setattr(nba_stats_client, "fetch_boxscore_summary", sources.v2)
    monkeypatch.setattr(nba_stats_client, "fetch_boxscore_traditional", sources.box)
    monkeypatch.setattr(game_summary, "fetch_bref_line_score", sources.bref)
    monkeypatch.setattr(game_details, "_schedule_game", lambda _: None)
    return sources


def unavailable(endpoint_name="BoxScoreSummaryV3"):
    return nba_stats_client.UpstreamUnavailableError(endpoint_name, "ReadTimeout", 10)


# Freshness policy

@pytest.mark.parametrize("metadata, expected", [
    (GameMetadata(1, "", "2026-01-20", TIPOFF), game_data.ACTIVE_TTL_SECONDS),
    (GameMetadata(2, "", "2026-01-20", TIPOFF), game_data.ACTIVE_TTL_SECONDS),
    (GameMetadata(1, "", "2025-01-20", NOW - timedelta(days=365)), game_data.ACTIVE_TTL_SECONDS),
    (GameMetadata(3, "", "2026-01-20", TIPOFF), game_data.RECENT_FINAL_TTL_SECONDS),
    (GameMetadata(3, "", "2026-01-17", NOW - timedelta(hours=71, minutes=59)), game_data.RECENT_FINAL_TTL_SECONDS),
    (GameMetadata(3, "", "2026-01-17", NOW - timedelta(hours=72)), game_data.SETTLED_TTL_SECONDS),
    (GameMetadata(3, "", "2026-01-21", NOW + timedelta(hours=1)), game_data.UNKNOWN_TTL_SECONDS),
    (GameMetadata(3, "", "2026-01-20", None), game_data.RECENT_FINAL_TTL_SECONDS),
    (GameMetadata(3, "", "2026-01-17", None), game_data.RECENT_FINAL_TTL_SECONDS),
    (GameMetadata(3, "", "2026-01-16", None), game_data.SETTLED_TTL_SECONDS),
    (GameMetadata(3, "", "1946-11-01", None), game_data.SETTLED_TTL_SECONDS),
    (GameMetadata(3, "", "2026-01-21", None), game_data.UNKNOWN_TTL_SECONDS),
    (GameMetadata(3, "", None, None), game_data.UNKNOWN_TTL_SECONDS),
    (GameMetadata(None, "", "1946-11-01", None), game_data.UNKNOWN_TTL_SECONDS),
    (GameMetadata(7, "", "1946-11-01", None), game_data.UNKNOWN_TTL_SECONDS),
    (None, game_data.UNKNOWN_TTL_SECONDS),
], ids=[
    "scheduled", "live", "stale_scheduled", "final_tonight", "final_within_72h", "final_at_72h",
    "final_before_tipoff", "date_only_today", "date_only_within_72h_of_day_end", "date_only_older",
    "date_only_history", "date_only_future", "final_without_date", "missing_status", "unknown_status", "missing_metadata",
])
def test_lifetime_is_chosen_from_authoritative_metadata(metadata, expected):
    assert game_data.metadata_ttl(metadata, NOW) == expected


def test_v3_metadata_keeps_authoritative_date_and_utc_tipoff():
    metadata = game_data.v3_metadata(summary())
    assert metadata == GameMetadata(3, "Final", "2026-01-20", datetime(2026, 1, 21, 0, 0, tzinfo=timezone.utc))
    assert metadata.datetime_utc.utcoffset() == timedelta(0)
    assert game_data.v3_metadata({"gameCode": "19961101/CHIBOS", "gameStatus": "3"}).game_date == "1996-11-01"
    assert game_data.v3_metadata({"gameStatus": "Final"}) == GameMetadata(None, "", None, None)


# Summary retrieval shared by the summary route and game details

def test_summary_route_and_details_share_one_v3_fetch(upstream):
    client = TestClient(main.app)
    first = client.get(f"/gamesummary/{GAME_ID}")
    second = client.get(f"/gamesummary/{GAME_ID}")
    details = client.get(f"/games/{GAME_ID}/details")

    assert first.status_code == second.status_code == details.status_code == 200
    assert first.json() == second.json()
    assert first.json()["periodScoreSource"] == "nba"
    assert details.json()["gameStatusText"] == "Final"
    upstream.v3.assert_called_once_with(GAME_ID)
    upstream.v2.assert_not_called()


def test_v2_fallback_is_shared_by_summary_route_and_legacy_details(upstream):
    upstream.v3.side_effect = unavailable()
    summary_body = TestClient(main.app).get(f"/gamesummary/{GAME_ID}").json()
    details = game_details.fetch_game_details(GAME_ID)

    assert summary_body["homeTeam"]["periods"][0] == {"period": 1, "score": "25"}
    assert (details["gameDate"], details["homeTeam"]["teamTricode"]) == ("1946-11-01", "TOR")
    upstream.v2.assert_called_once_with(GAME_ID)
    # Failures are never cached, so each caller retried V3 before falling back.
    assert upstream.v3.call_count == 2


def test_concurrent_summary_route_and_details_share_one_in_flight_fetch(upstream):
    entered, release = Event(), Event()

    def slow(game_id, **_):
        entered.set()
        assert release.wait(2)
        return endpoint(summary(1))

    upstream.v3.side_effect = slow
    with ThreadPoolExecutor(max_workers=3) as pool:
        route = pool.submit(game_summary.fetch_game_summary, GAME_ID)
        assert entered.wait(2)
        followers = [pool.submit(game_details.fetch_game_details, GAME_ID) for _ in range(2)]
        time.sleep(0.05)
        release.set()
        assert route.result(2)["gameStatusText"] == "7:00 pm ET"
        assert [f.result(2)["gameStatus"] for f in followers] == [1, 1]
    assert upstream.v3.call_count == 1
    assert game_data._summary_v3_cache._flights == {}


def test_different_games_load_independently(upstream):
    first_entered, second_entered = Event(), Event()

    def fetch(game_id, **_):
        if game_id == GAME_ID:
            first_entered.set()
            # Completes only once the other game's load has started alongside it.
            assert second_entered.wait(2)
        else:
            second_entered.set()
        return endpoint(summary(game_id=game_id))

    upstream.v3.side_effect = fetch
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(game_data.get_summary_v3, GAME_ID)
        assert first_entered.wait(2)
        second = pool.submit(game_data.get_summary_v3, OTHER_GAME_ID)
        assert (first.result(2)["gameId"], second.result(2)["gameId"]) == (GAME_ID, OTHER_GAME_ID)


def test_details_never_request_player_stats_or_linescore_repair(upstream):
    # Invalid NBA periods would trigger repair in the summary view, never in details.
    broken = summary()
    broken["homeTeam"]["periods"] = []
    upstream.v3.side_effect = lambda *_, **__: endpoint(broken)
    assert game_details.fetch_game_details(GAME_ID)["gameStatus"] == 3

    upstream.v3.side_effect = unavailable()
    game_data._summary_v3_cache.clear()
    assert game_details.fetch_game_details(GAME_ID)["gameStatus"] == 3
    upstream.box.assert_not_called()
    upstream.bref.assert_not_called()


def test_summary_status_transitions_refresh_after_short_lifetimes(upstream, clock):
    upstream.v3.side_effect = [endpoint(summary(1)), endpoint(summary(2)), endpoint(summary(3))]
    assert game_summary.fetch_game_summary(GAME_ID)["gameStatusText"] == "7:00 pm ET"
    assert game_data._summary_v3_cache.expires_in(GAME_ID) == game_data.ACTIVE_TTL_SECONDS

    clock[0] += game_data.ACTIVE_TTL_SECONDS
    assert game_summary.fetch_game_summary(GAME_ID)["gameStatusText"] == "Q2 5:00"
    # A live entry stays live for its remaining lifetime; reads never renew it.
    clock[0] += game_data.ACTIVE_TTL_SECONDS - 1
    assert game_summary.fetch_game_summary(GAME_ID)["gameStatusText"] == "Q2 5:00"
    assert game_data._summary_v3_cache.expires_in(GAME_ID) == 1

    clock[0] += 1
    assert game_summary.fetch_game_summary(GAME_ID)["gameStatusText"] == "Final"
    assert game_data._summary_v3_cache.expires_in(GAME_ID) == game_data.RECENT_FINAL_TTL_SECONDS
    assert upstream.v3.call_count == 3


def test_unusable_and_failed_summaries_are_not_cached(upstream):
    upstream.v3.side_effect = [endpoint(None), endpoint({**summary(), "gameId": OTHER_GAME_ID}), unavailable(), endpoint(summary())]
    for _ in range(3):
        game_details.fetch_game_details(GAME_ID)
    assert len(game_data._summary_v3_cache) == 0
    assert game_data._summary_v3_cache._flights == {}
    assert game_data.get_summary_v3(GAME_ID)["gameStatus"] == 3
    assert len(game_data._summary_v3_cache) == 1


def test_v2_without_a_game_row_or_frames_is_not_cached(upstream):
    empty = SimpleNamespace(game_summary=SimpleNamespace(get_data_frame=pd.DataFrame), line_score=SimpleNamespace(get_data_frame=pd.DataFrame))
    missing = SimpleNamespace(game_summary=SimpleNamespace(get_data_frame=lambda: None), line_score=SimpleNamespace(get_data_frame=pd.DataFrame))
    upstream.v2.side_effect = [empty, missing, legacy()]
    assert game_data.get_summary_v2(GAME_ID)["game_summary"].empty
    with pytest.raises(nba_stats_client.UpstreamBadResponseError):
        game_data.get_summary_v2(GAME_ID)
    assert len(game_data._summary_v2_cache) == 0
    assert not game_data.get_summary_v2(GAME_ID)["game_summary"].empty
    assert game_data._summary_v2_cache.expires_in(GAME_ID) == game_data.SETTLED_TTL_SECONDS


def test_summary_mutations_do_not_alter_cached_entries(upstream):
    first = game_data.get_summary_v3(GAME_ID)
    first["gameStatus"] = 1
    first["homeTeam"]["teamId"] = 0
    frames = game_data.get_summary_v2(GAME_ID)
    frames["game_summary"].loc[0, "GAME_STATUS_ID"] = 1
    frames["line_score"] = None
    assert game_data.get_summary_v3(GAME_ID) == summary()
    cached = game_data.get_summary_v2(GAME_ID)
    assert (cached["game_summary"].loc[0, "GAME_STATUS_ID"], len(cached["line_score"])) == (3, 2)
    assert game_data._summary_v2_cache.get(GAME_ID) is not None and upstream.v2.call_count == 1


# Boxscores and their insertion-time lifetimes

def test_boxscore_route_reuses_entry_until_expiry(upstream, clock):
    client = TestClient(main.app)
    first = client.get(f"/games/{GAME_ID}/boxscore")
    clock[0] += game_data.RECENT_FINAL_TTL_SECONDS - 1
    second = client.get(f"/games/{GAME_ID}/boxscore")

    assert first.status_code == second.status_code == 200
    assert first.json() == second.json() == {"game": boxscore()["boxScoreTraditional"]}
    assert upstream.box.call_count == 1
    assert game_data._boxscore_cache.expires_in(GAME_ID) == 1
    clock[0] += 1
    client.get(f"/games/{GAME_ID}/boxscore")
    assert upstream.box.call_count == 2


@pytest.mark.parametrize("game, expected", [
    (summary(1), game_data.ACTIVE_TTL_SECONDS),
    (summary(2), game_data.ACTIVE_TTL_SECONDS),
    (summary(3), game_data.RECENT_FINAL_TTL_SECONDS),
    (summary(3, tipoff=NOW - timedelta(days=4)), game_data.SETTLED_TTL_SECONDS),
    ({**summary(3), "gameStatus": None}, game_data.UNKNOWN_TTL_SECONDS),
    (None, game_data.UNKNOWN_TTL_SECONDS),
], ids=["scheduled", "live", "recent_final", "older_final", "missing_status", "no_summary"])
def test_boxscore_lifetime_follows_metadata_fetched_during_refresh(upstream, game, expected):
    upstream.v3.side_effect = lambda *_, **__: endpoint(game)
    game_data.get_boxscore(GAME_ID)
    assert game_data._boxscore_cache.expires_in(GAME_ID) == expected
    # The lifetime lookup uses a short, single-attempt policy.
    upstream.v3.assert_called_once_with(GAME_ID, timeout=2, retries=0)


def test_failed_lifetime_lookup_keeps_boxscore_short_without_failing_it(upstream):
    upstream.v3.side_effect = unavailable()
    assert TestClient(main.app).get(f"/games/{GAME_ID}/boxscore").status_code == 200
    assert game_data._boxscore_cache.expires_in(GAME_ID) == game_data.UNKNOWN_TTL_SECONDS


def test_earlier_summary_cache_hit_cannot_promote_a_boxscore(upstream):
    game_summary.fetch_game_summary(GAME_ID)
    assert game_data._summary_v3_cache.expires_in(GAME_ID) == game_data.RECENT_FINAL_TTL_SECONDS
    upstream.v3.side_effect = unavailable()
    game_data.get_boxscore(GAME_ID)
    assert game_data._boxscore_cache.expires_in(GAME_ID) == game_data.UNKNOWN_TTL_SECONDS
    assert upstream.v3.call_count == 2


def test_live_to_final_transition_promotes_only_after_a_fresh_final(upstream, clock):
    upstream.v3.side_effect = [endpoint(summary(2)), endpoint(summary(3))]
    game_data.get_boxscore(GAME_ID)
    assert game_data._boxscore_cache.expires_in(GAME_ID) == game_data.ACTIVE_TTL_SECONDS
    clock[0] += game_data.ACTIVE_TTL_SECONDS - 1
    game_data.get_boxscore(GAME_ID)
    assert upstream.box.call_count == 1

    clock[0] += 1
    game_data.get_boxscore(GAME_ID)
    assert game_data._boxscore_cache.expires_in(GAME_ID) == game_data.RECENT_FINAL_TTL_SECONDS
    assert upstream.box.call_count == 2


def test_lifetime_metadata_is_fetched_before_the_boxscore(upstream):
    order = []
    upstream.v3.side_effect = lambda *_, **__: order.append("summary") or endpoint(summary())
    upstream.box.side_effect = lambda game_id: order.append("boxscore") or boxscore(game_id)
    game_data.get_boxscore(GAME_ID)
    assert order == ["summary", "boxscore"]


def test_boxscore_joining_an_in_flight_summary_uses_it_for_promotion(upstream):
    entered, release = Event(), Event()

    def slow(game_id, **kwargs):
        entered.set()
        assert release.wait(2)
        return endpoint(summary())

    upstream.v3.side_effect = slow
    with ThreadPoolExecutor(max_workers=2) as pool:
        route = pool.submit(game_summary.fetch_game_summary, GAME_ID)
        assert entered.wait(2)
        box = pool.submit(game_data.get_boxscore, GAME_ID)
        time.sleep(0.05)
        release.set()
        route.result(2)
        box.result(2)
    upstream.v3.assert_called_once_with(GAME_ID)
    assert game_data._boxscore_cache.expires_in(GAME_ID) == game_data.RECENT_FINAL_TTL_SECONDS


def test_strict_summary_retries_after_a_failed_lifetime_lookup(upstream):
    entered, release = Event(), Event()

    def fetch(game_id, **kwargs):
        if kwargs:
            entered.set()
            assert release.wait(2)
            raise unavailable()
        return endpoint(summary())

    upstream.v3.side_effect = fetch
    with ThreadPoolExecutor(max_workers=2) as pool:
        box = pool.submit(game_data.get_boxscore, GAME_ID)
        assert entered.wait(2)
        route = pool.submit(game_summary.fetch_game_summary, GAME_ID)
        time.sleep(0.05)
        release.set()
        assert box.result(2)["gameId"] == GAME_ID
        assert route.result(2)["gameStatusText"] == "Final"
    assert [c.kwargs for c in upstream.v3.call_args_list] == [{"timeout": 2, "retries": 0}, {}]
    assert game_data._boxscore_cache.expires_in(GAME_ID) == game_data.UNKNOWN_TTL_SECONDS


def test_boxscore_failures_are_not_cached_and_retry(upstream):
    upstream.box.side_effect = [unavailable("BoxScoreTraditionalV3"), {"boxScoreTraditional": None}, boxscore()]
    client = TestClient(main.app)
    assert client.get(f"/games/{GAME_ID}/boxscore").status_code == 503
    assert client.get(f"/games/{GAME_ID}/boxscore").status_code == 404
    assert len(game_data._boxscore_cache) == 0
    assert game_data._boxscore_cache._flights == {}
    assert client.get(f"/games/{GAME_ID}/boxscore").status_code == 200
    assert len(game_data._boxscore_cache) == 1


def test_invalid_game_ids_bypass_the_caches(upstream):
    assert game_data.get_boxscore("123")["gameId"] == "123"
    upstream.v3.assert_not_called()
    assert len(game_data._boxscore_cache) == 0


def test_caches_are_bounded_and_evict_oldest_entries(upstream):
    caches = (game_data._boxscore_cache, game_data._summary_v3_cache, game_data._summary_v2_cache)
    assert [cache.max_entries for cache in caches] == [256, 256, 256]
    game_ids = [f"00225{index:05d}" for index in range(257)]
    for game_id in game_ids:
        game_data.get_boxscore(game_id)
        game_data.get_summary_v2(game_id)
    assert [len(cache) for cache in caches] == [256, 256, 256]
    assert all(cache._flights == {} for cache in caches)
    assert all(cache.get(game_ids[0]) is None and cache.get(game_ids[-1]) for cache in caches)


# Game context

def test_context_reports_metadata_and_boxscore_membership(upstream):
    context = game_data.get_game_context(GAME_ID)
    assert context == {
        "gameId": GAME_ID,
        "gameStatus": 3,
        "gameStatusText": "Final",
        "gameDate": "2026-01-20",
        "gameDatetimeUtc": datetime(2026, 1, 21, 0, 0, tzinfo=timezone.utc),
        # Membership includes DNP entries.
        "homeTeam": {"teamId": HOME, "playerIds": [1, 2]},
        "awayTeam": {"teamId": AWAY, "playerIds": [3]},
    }
    assert context["gameDatetimeUtc"].tzinfo is not None


def test_boxscore_route_and_context_share_boxscore_and_summary_fetches(upstream):
    TestClient(main.app).get(f"/games/{GAME_ID}/boxscore")
    game_data.get_game_context(GAME_ID)
    game_data.get_game_context(GAME_ID)
    assert upstream.box.call_count == 1
    assert upstream.v3.call_count == 1


def test_concurrent_boxscore_route_and_context_share_one_boxscore_fetch(upstream):
    entered, release = Event(), Event()

    def slow(game_id):
        entered.set()
        assert release.wait(2)
        return boxscore(game_id)

    upstream.box.side_effect = slow
    with ThreadPoolExecutor(max_workers=2) as pool:
        route = pool.submit(main.get_game_boxscore, GAME_ID)
        assert entered.wait(2)
        context = pool.submit(game_data.get_game_context, GAME_ID)
        time.sleep(0.05)
        release.set()
        assert route.result(2)["game"]["gameId"] == GAME_ID
        assert context.result(2)["homeTeam"]["playerIds"] == [1, 2]
    assert upstream.box.call_count == 1


def test_date_only_history_context_has_no_invented_tipoff(upstream):
    upstream.v3.side_effect = lambda *_, **__: endpoint(None)
    context = game_data.get_game_context(GAME_ID)
    assert (context["gameStatus"], context["gameDate"], context["gameDatetimeUtc"]) == (3, "1946-11-01", None)
    assert game_data._summary_v2_cache.expires_in(GAME_ID) == game_data.SETTLED_TTL_SECONDS
    # Only freshly fetched V3 metadata may promote the boxscore.
    assert game_data._boxscore_cache.expires_in(GAME_ID) == game_data.UNKNOWN_TTL_SECONDS
    upstream.bref.assert_not_called()


def test_context_metadata_is_nullable_when_summaries_lack_it(upstream):
    upstream.v3.side_effect = lambda *_, **__: endpoint(None)
    upstream.v2.side_effect = lambda *_, **__: SimpleNamespace(
        game_summary=SimpleNamespace(get_data_frame=pd.DataFrame), line_score=SimpleNamespace(get_data_frame=pd.DataFrame))
    context = game_data.get_game_context(GAME_ID)
    assert (context["gameStatus"], context["gameStatusText"], context["gameDate"], context["gameDatetimeUtc"]) == (None, "", None, None)


def test_context_propagates_boxscore_and_summary_errors(upstream):
    with pytest.raises(ValueError):
        game_data.get_game_context("invalid")
    upstream.v3.side_effect = unavailable()
    upstream.v2.side_effect = unavailable("BoxScoreSummaryV2")
    with pytest.raises(nba_stats_client.UpstreamUnavailableError):
        game_data.get_game_context(GAME_ID)
    upstream.box.side_effect = unavailable("BoxScoreTraditionalV3")
    game_data._boxscore_cache.clear()
    with pytest.raises(nba_stats_client.UpstreamUnavailableError) as error:
        game_data.get_game_context(GAME_ID)
    assert error.value.endpoint == "BoxScoreTraditionalV3"


def test_context_and_route_mutations_do_not_leak(upstream):
    context = game_data.get_game_context(GAME_ID)
    context["homeTeam"]["playerIds"].append(99)
    game_data.get_boxscore(GAME_ID)["homeTeam"]["players"].clear()
    assert game_data.get_game_context(GAME_ID)["homeTeam"]["playerIds"] == [1, 2]
    assert main.get_game_boxscore(GAME_ID) == {"game": boxscore()["boxScoreTraditional"]}
