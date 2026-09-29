"""Whether a request's outcome could reveal a result, from the question and published schedule.

Answers are never hidden (ADR 0006). This predicate only decides whether a
clarification must be asked before any result lookup, so that the choices, or
the decision to offer them, cannot depend on which games were played. A failed
or dates-only schedule is treated conservatively.
"""

from __future__ import annotations

import datetime as dt

from server.ask.models.request import BoxscoreStatRequest
from server.services import nba_schedule
from server.utils.season import get_nba_season


def _published_date(game: dict) -> dt.date | None:
    raw = game.get("gameDateEst") or game.get("gameDate")
    if not raw:
        return None
    text = str(raw).split(" ")[0]
    try:
        return dt.datetime.strptime(text, "%m/%d/%Y").date() if "/" in text else dt.date.fromisoformat(text[:10])
    except ValueError:
        return None


def outcome_may_reveal_result(request: BoxscoreStatRequest) -> bool:
    """True when some possible outcome of a single-game request would reveal a
    result, decided before any result lookup and never from the outcome."""
    selector = request.game
    if selector.season and selector.game_number:
        return True
    if selector.date:
        return _postseason_on(selector.date)
    return False


def _postseason_on(day: dt.date) -> bool:
    """Whether a postseason game is, or may be, published on ``day``."""
    # The 2019-20 Finals ran into October 2020 after the bubble pause.
    season = "2019-20" if dt.date(2020, 10, 1) <= day <= dt.date(2020, 10, 13) else get_nba_season(day.year, day.month)
    try:
        schedule = nba_schedule.get_season_schedule(season, allow_completed_fallback=False)
    except Exception:
        # A dates-only or missing schedule cannot prove absence safe.
        return True
    if not schedule.is_schedule or not schedule.games:
        return True
    for game_id, game in schedule.games.items():
        published = _published_date(game)
        if published is None:
            return True
        if published == day and str(game_id).startswith(("004", "005")):
            return True
    return False
