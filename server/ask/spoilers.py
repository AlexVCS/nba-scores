"""Spoiler helpers for Ask results.

The server always sends values; protected ones are wrapped in ``Guarded``
(or carry ``spoiler: true``) so the UI can leave them out of the DOM while
results are hidden. Rules applied by the resolvers:

* scores, overtime, statistics, leaders, series wins, winners, series status
  and length, records, finishes and advancement are always protected;
* entities the user named are echoed unprotected; participants Python
  inferred from results (an opponent, a Finals team) are protected;
* an absent value is still protected when its absence reveals progress,
  such as an undecided champion or a final score that is not yet available.
"""

from __future__ import annotations

from typing import TypeVar

from server.ask.models.common import Guarded
from server.ask.models.response import GameSpoilers

T = TypeVar("T")


def guard(value: T, spoiler: bool = True) -> Guarded[T]:
    return Guarded[T](value=value, spoiler=spoiler)


def open_value(value: T) -> Guarded[T]:
    """An unprotected value (for fields that do not apply to this scope)."""
    return Guarded[T](value=value, spoiler=False)


def game_spoilers(status: int | None) -> GameSpoilers:
    # A scheduled game's status text is its tipoff time; once started it
    # reveals progress or overtime ("Final/OT"). Series text such as
    # "BOS leads 3-2" is protected even before tipoff.
    return GameSpoilers(score=True, status_text=status != 1, series_text=True)
