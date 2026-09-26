import pytest

from server.services import nba_schedule, scoreboard


@pytest.fixture(autouse=True)
def clear_shared_caches():
    scoreboard._scoreboard_cache.clear()
    nba_schedule._schedule_cache.clear()
    nba_schedule._schedule_cooldowns.clear()
    yield
    scoreboard._scoreboard_cache.clear()
    nba_schedule._schedule_cache.clear()
    nba_schedule._schedule_cooldowns.clear()
