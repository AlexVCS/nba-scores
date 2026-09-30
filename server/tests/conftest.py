import pytest

from server.services import game_data, game_summary, nba_schedule, scoreboard


@pytest.fixture(autouse=True)
def clear_shared_caches():
    caches = (
        game_data._boxscore_cache,
        game_data._summary_v3_cache,
        game_data._summary_v2_cache,
        game_summary.BREF_LINE_SCORE_CACHE,
    )
    for cache in caches:
        cache.clear()
    scoreboard._scoreboard_cache.clear()
    nba_schedule._schedule_cache.clear()
    nba_schedule._schedule_cooldowns.clear()
    yield
    for cache in caches:
        cache.clear()
    scoreboard._scoreboard_cache.clear()
    nba_schedule._schedule_cache.clear()
    nba_schedule._schedule_cooldowns.clear()
