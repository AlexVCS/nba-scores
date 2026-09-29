"""Outcome-independent spoiler gates from a normalized request and published schedule.

Call this before resolving a request. A failed or dates-only schedule is treated
conservatively so a missing game cannot change whether the answer is gated.
"""

from __future__ import annotations

import datetime as dt

from server.ask.models.request import AskRequest, BoxscoreStatRequest, GameSearchRequest, PlayoffSeriesRequest
from server.ask.models.common import DateRange
from server.ask.models.response import SpoilerGate
from server.services import nba_schedule
from server.services import playoffs as playoffs_service
from server.utils.season import get_nba_season


HIDDEN_GAME_GATE = SpoilerGate(
    title="Results hidden",
    message="Whether these games were played may reveal a result. Reveal the answer when ready.",
)


def _published_date(game: dict) -> dt.date | None:
    raw = game.get("gameDateEst") or game.get("gameDate")
    if not raw:
        return None
    text = str(raw).split(" ")[0]
    try:
        return dt.datetime.strptime(text, "%m/%d/%Y").date() if "/" in text else dt.date.fromisoformat(text[:10])
    except ValueError:
        return None


def conditional_playoff_game(game_id: str, game_number: int | None, if_necessary: bool = False) -> bool:
    """Whether this game's existence can disclose series length.

    The minimum completed series has ``targetWins`` games. Unknown historical
    rounds and the 1954 round robin are guarded conservatively.
    """
    if not game_id.startswith("004"):
        return False
    if if_necessary or game_number is None:
        return True
    round_number = playoffs_service.infer_round_from_game_id(game_id)
    if round_number is None:
        return True
    playoff_year = int(game_id[3:5]) + (2001 if int(game_id[3:5]) < 46 else 1901)
    target = playoffs_service.get_target_wins(playoff_year, round_number, round_number == 4)
    return target is None or game_number > target


def _published_game_number(game_id: str, game: dict) -> int | None:
    text = str(game.get("seriesGameNumber") or "")
    if text.startswith("Game ") and text[5:].isdigit():
        return int(text[5:])
    # Modern IDs end in the numbered game; old IDs are too ambiguous to use.
    if playoffs_service.infer_round_from_game_id(game_id) is not None and game_id[-1:] in "1234567":
        return int(game_id[-1])
    return None


def request_spoiler_gate(request: AskRequest) -> SpoilerGate | None:
    """The same gate for answer and not_found, before any result lookup."""
    if isinstance(request, PlayoffSeriesRequest):
        return HIDDEN_GAME_GATE if request.teams else None
    if isinstance(request, BoxscoreStatRequest):
        selector = request.game
        if selector.season and selector.game_number:
            return HIDDEN_GAME_GATE
        if selector.date:
            return _game_search_gate(DateRange(start=selector.date, end=selector.date), True)
        return None
    if not isinstance(request, GameSearchRequest):
        return None

    return _game_search_gate(request.dates, bool(request.teams))


def _game_search_gate(dates: DateRange, named_teams: bool) -> SpoilerGate | None:

    seasons = set()
    for offset in range((dates.end - dates.start).days + 1):
        day = dates.start + dt.timedelta(days=offset)
        # The 2019-20 Finals ran into October 2020 after the bubble pause.
        seasons.add("2019-20" if dt.date(2020, 10, 1) <= day <= dt.date(2020, 10, 13)
                    else get_nba_season(day.year, day.month))
    for season in seasons:
        try:
            schedule = nba_schedule.get_season_schedule(season, allow_completed_fallback=False)
        except Exception:
            # A dates-only or missing schedule cannot prove absence safe.
            return HIDDEN_GAME_GATE
        if not schedule.is_schedule or not schedule.games:
            return HIDDEN_GAME_GATE
        for game_id, game in schedule.games.items():
            day = _published_date(game)
            if day is None:
                return HIDDEN_GAME_GATE
            if not dates.start <= day <= dates.end or not str(game_id).startswith(("004", "005")):
                continue
            # A named team's absence during postseason reveals elimination.
            # A published conditional game can also reveal series length.
            if named_teams or str(game_id).startswith("005") or conditional_playoff_game(str(game_id), _published_game_number(str(game_id), game), bool(game.get("ifNecessary"))):
                return HIDDEN_GAME_GATE
    return None
