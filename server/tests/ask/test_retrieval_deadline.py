"""One shared retrieval deadline across NBA attempts, backoff, fallback and cache waits (nba-scores-8ic).

Fake clocks advance only when a fake source "takes" time, so each budget is exact.
"""
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
import requests

from server.ask.models.request import GameSearchRequest
from server.ask.models.response import InterpreterInfo
from server.ask.present import interpretation
from server.ask.resolvers import EXECUTORS, resolve, seasons
from server.ask.resolvers.errors import NotFoundError, UnavailableError
from server.ask.cache import CacheValue
from server.services import basketball_reference, nba_stats_client
from server.tests.ask.test_season_tools import CONTEXT, nba_payload, row
from server.tests.ask.test_season_tools import request as season_request
from server.utils.deadline import Deadline, wait_timeout

BREF_HTML = (Path(__file__).parent / "fixtures/season-data/bref-jokic-2024.html").read_text()


class Clock:
    def __init__(self):
        self.now = 1000.0
        self.sleeps = []

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


@pytest.fixture
def clock():
    return Clock()


def budget(clock, seconds):
    return Deadline.after(seconds, clock=clock, sleep=clock.sleep)


@pytest.fixture(autouse=True)
def isolated_sources(monkeypatch):
    seasons._cache.clear()
    monkeypatch.setattr(basketball_reference, "_next_start", 0)
    monkeypatch.setattr(basketball_reference.requests, "get", lambda *a, **k: pytest.fail("Unexpected BRef network"))
    monkeypatch.setattr(seasons.playercareerstats, "PlayerCareerStats", lambda **k: pytest.fail("Unexpected NBA network"))
    monkeypatch.setattr(nba_stats_client.time, "sleep", lambda s: pytest.fail("Backoff must use the shared deadline"))
    yield
    seasons._cache.clear()


def nba_source(monkeypatch, clock, steps):
    """Each NBA attempt takes ``seconds`` (capped by its timeout) then times out, misses or answers."""
    calls = []

    def career(**kwargs):
        seconds, result = steps[len(calls)]
        calls.append(kwargs["timeout"])
        clock.now += min(seconds, kwargs["timeout"])
        if result == "timeout" or seconds > kwargs["timeout"]:
            raise requests.Timeout("slow NBA")
        rows = [row()] if result == "answer" else []
        return SimpleNamespace(get_dict=lambda: nba_payload(rows or [row(SEASON_ID="2022-23")]))
    monkeypatch.setattr(seasons.playercareerstats, "PlayerCareerStats", career)
    return calls


def test_slow_primary_skips_retry_and_fallback_that_cannot_fit(monkeypatch, clock):
    calls = nba_source(monkeypatch, clock, [(9, "timeout"), (9, "answer")])
    monkeypatch.setattr(seasons, "_bref_player", lambda *a, **k: pytest.fail("Fallback cannot fit"))
    deadline = budget(clock, 4.75)
    with pytest.raises(UnavailableError, match="season_deadline_exceeded"):
        seasons.player_season(season_request(), deadline)
    assert calls == [4] and clock.sleeps == []
    assert clock.now - 1000 <= 4.75


@pytest.mark.parametrize("seconds,retry_timeout", [(12, 4), (7, 2.25)])
def test_retry_that_fits_runs_with_capped_timeout(monkeypatch, clock, seconds, retry_timeout):
    calls = nba_source(monkeypatch, clock, [(9, "timeout"), (0.5, "answer")])
    output = seasons.player_season(season_request(), budget(clock, seconds))
    assert calls == [4, pytest.approx(retry_timeout)] and clock.sleeps == [0.75]
    assert output.sources[0].name == "nba_stats"


def test_primary_miss_without_time_for_fallback_is_unavailable_not_no_record(monkeypatch, clock):
    nba_source(monkeypatch, clock, [(3.5, "missing")])
    monkeypatch.setattr(seasons, "_bref_player", lambda *a, **k: pytest.fail("Fallback cannot fit"))
    with pytest.raises(UnavailableError, match="season_deadline_exceeded") as caught:
        seasons.player_season(season_request(), budget(clock, 5))
    assert not isinstance(caught.value, NotFoundError)


def test_fallback_that_fits_uses_remaining_budget_as_timeout(monkeypatch, clock):
    nba_source(monkeypatch, clock, [(3, "missing")])
    seen = []
    response = SimpleNamespace(text=BREF_HTML, status_code=200, raise_for_status=lambda: None)
    monkeypatch.setattr(basketball_reference.requests, "get", lambda *a, **k: seen.append(k["timeout"]) or response)
    output = seasons.player_season(season_request(), budget(clock, 6.5))
    assert output.sources[0].name == "basketball_reference"
    assert seen == [pytest.approx(3.5)]


def test_limiter_cooldown_fails_fast_inside_budget(monkeypatch, clock):
    nba_source(monkeypatch, clock, [(0.1, "missing")])
    monkeypatch.setattr(basketball_reference, "_next_start", time.monotonic() + 60)
    with pytest.raises(UnavailableError, match="season_sources_unavailable"):
        seasons.player_season(season_request(), budget(clock, 10))
    assert clock.now - 1000 == pytest.approx(0.1)


def test_limiter_refuses_start_that_cannot_fit_without_consuming_slot(clock):
    before = basketball_reference._next_start
    with pytest.raises(basketball_reference.FallbackDeadlineExceeded):
        basketball_reference.get("https://www.basketball-reference.com/leagues/NBA_2024.html",
                                 deadline=budget(clock, basketball_reference.MIN_START_SECONDS - 0.01))
    assert basketball_reference._next_start == before


def test_expired_deadline_makes_no_nba_attempt(clock):
    deadline = budget(clock, 0.5)
    with pytest.raises(nba_stats_client.UpstreamUnavailableError) as caught:
        nba_stats_client._run("PlayerCareerStats", lambda: pytest.fail("No attempt fits"), retries=1, deadline=deadline)
    assert caught.value.error_type == "DeadlineExceeded"


def test_joined_season_waits_are_bounded_by_remaining_budget(monkeypatch, clock):
    waits = []

    def joined(*args, **kwargs):
        waits.append(kwargs["wait_timeout"])
        return seasons._cache.__class__.get_or_load(seasons._cache, *args, **kwargs)
    monkeypatch.setattr(seasons._cache, "get_or_load", joined)
    monkeypatch.setattr(seasons, "_load", lambda *a, **k: (_ for _ in ()).throw(UnavailableError("stop")))
    with pytest.raises(UnavailableError):
        seasons.player_season(season_request(), budget(clock, 1.5))
    assert waits == [1.5]
    assert wait_timeout(None, 5) == 5 and wait_timeout(budget(clock, 9), 5) == 5 and wait_timeout(budget(clock, 2), None) == 2


def test_real_coalesced_season_load_releases_waiter_at_deadline():
    started, release = threading.Event(), threading.Event()
    key = season_request().model_dump_json()

    def slow_loader():
        started.set()
        release.wait(5)
        raise UnavailableError("leader gave up")
    leader = threading.Thread(target=lambda: pytest.raises(UnavailableError, seasons._season_cached, "player-season", key, slow_loader))
    leader.start()
    try:
        assert started.wait(2)
        began = time.monotonic()
        with pytest.raises(UnavailableError, match="season_load_in_progress"):
            seasons.player_season(season_request(), Deadline.after(0.2))
        assert time.monotonic() - began < 1.5
    finally:
        release.set()
        leader.join(5)


def test_answer_cache_waits_are_bounded_for_every_tool(tmp_path, monkeypatch, clock):
    from server.tests.ask.test_pipeline import output, pipeline
    from server.ask.eval import builders as b
    coordinator, _, _ = pipeline(tmp_path, b.lookup_result([]), output())
    waits = []

    def joined(namespace, key, loader, **kwargs):
        waits.append(kwargs["wait_timeout"])
        return SimpleNamespace(value=loader().value, hit=False)
    monkeypatch.setattr(coordinator.cache, "get_or_load", joined)
    received = []

    def fake_resolve(request, **kwargs):
        received.append(kwargs)
        raise UnavailableError("stop")
    monkeypatch.setattr("server.ask.pipeline.resolve", fake_resolve)
    info = InterpreterInfo(model_called=False)
    season = season_request()
    games = GameSearchRequest(dates={"start": "2026-09-29", "end": "2026-09-29"})
    for request, seconds in ((season, 2), (season, 30), (games, 3)):
        response = coordinator._execute("q", request, interpretation(None, None, CONTEXT, request), info, budget(clock, seconds))
        assert response.outcome == "unavailable" and response.notice.code == "service_unavailable"
    assert waits == [2, 5, 3]
    # The deadline reaches season tools only; other executors keep their signatures.
    assert [set(k) for k in received] == [{"deadline"}, {"deadline"}, set()]


def test_resolve_passes_deadline_only_to_deadline_executors(monkeypatch, clock):
    seen = {}
    monkeypatch.setitem(EXECUTORS, "player_season_stats", lambda request, **kwargs: seen.setdefault("season", kwargs))
    monkeypatch.setitem(EXECUTORS, "game_search", lambda request: seen.setdefault("games", "no kwargs"))
    deadline = budget(clock, 3)
    resolve(season_request(), deadline=deadline)
    resolve(GameSearchRequest(dates={"start": "2026-09-29", "end": "2026-09-29"}), deadline=deadline)
    assert seen == {"season": {"deadline": deadline}, "games": "no kwargs"}


def test_pipeline_retrieval_deadline_is_remaining_response_time(tmp_path):
    from server.tests.ask.test_pipeline import output, pipeline
    from server.ask.eval import builders as b
    coordinator, _, _ = pipeline(tmp_path, b.lookup_result([]), output())
    total = coordinator.config.deadline_seconds
    started = time.monotonic()
    deadline = coordinator._retrieval_deadline(started)
    # Retrieval ends with the response, less a small margin to build it; it is
    # not limited to the (at most five-second) reserve left after interpretation.
    assert deadline.expires_at == pytest.approx(started + total - min(0.25, total / 20))


def test_cached_answer_needs_no_budget(monkeypatch, clock):
    seasons._cache.get_or_load("player-season", season_request().model_dump_json(),
                               lambda: CacheValue(seasons.SeasonData((row(),), "nba_stats", "https://www.nba.com/stats/player/203999/traditional",
                                                                     seasons._now(), True), 60))
    output = seasons.player_season(season_request(), budget(clock, 0))
    assert output.result.games_played == 79


def test_stage3_tools_make_no_attempt_after_the_deadline(monkeypatch, clock):
    from server.ask.resolvers import career, leaders
    from server.tests.ask.test_career_tools import request as career_request
    from server.tests.ask.test_leader_tools import request as leaders_request
    monkeypatch.setattr(leaders.leagueleaders, "LeagueLeaders", lambda **k: pytest.fail("No attempt fits"))
    monkeypatch.setattr(career.playercareerstats, "PlayerCareerStats", lambda **k: pytest.fail("No attempt fits"))
    with pytest.raises(UnavailableError):
        leaders.season_leaders(leaders_request(aggregation="total"), deadline=budget(clock, 0.5))
    with pytest.raises(UnavailableError):
        career.career_stats(career_request(), deadline=budget(clock, 0.5))
