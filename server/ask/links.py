"""Verified navigation links for Ask results.

Every builder validates its inputs and returns a contract ``VerifiedLink``
(whose own validator enforces the internal-path allowlist). Paths are
design-agnostic; the UI adds the active design prefix. They match routes
registered in src/main.tsx:

* ``/?date=YYYY-MM-DD``: scores page (``useScoresPage`` reads ``date``)
* ``/games/:gameId/boxscore?date=YYYY-MM-DD``: boxscore, as GameCard builds it
* ``/playoffs?season=YYYY-YY``: bracket (``PlayoffYearPicker`` reads ``season``)
* ``/playoffs/:year/:seriesSlug``: series page, with the slug that
  ``buildSeriesSlug`` (src/utils/seriesSlug.ts) derives from the same
  playoffs payload, so ``findSeriesBySlug`` resolves it

No link ever carries ``revealed=true``.
"""

from __future__ import annotations

import datetime as dt
import re

from server.ask.models.response import VerifiedLink
from server.utils.boxscore_availability import is_valid_nba_game_id

# Mirrors ROUND_SLUGS in src/utils/seriesSlug.ts.
_ROUND_SLUGS = {1: "first-round", 2: "semifinal", 3: "final"}
_SEASON = re.compile(r"\d{4}-\d{2}")


def season_to_year(season: str) -> int:
    """The calendar year a season's playoffs are played in ("2023-24" -> 2024)."""
    if not _SEASON.fullmatch(season):
        raise ValueError(f"Invalid season {season!r}")
    return int(season[:4]) + 1


def scores_link(day: dt.date, label: str | None = None) -> VerifiedLink:
    return VerifiedLink(kind="scores_date", label=label or "Open scores", href=f"/?date={day.isoformat()}")


def boxscore_link(game_id: str, day: dt.date | None) -> VerifiedLink:
    if not is_valid_nba_game_id(game_id):
        raise ValueError(f"Invalid game ID {game_id!r}")
    suffix = f"?date={day.isoformat()}" if day else ""
    return VerifiedLink(kind="boxscore", label="Open boxscore", href=f"/games/{game_id}/boxscore{suffix}")


def bracket_link(season: str) -> VerifiedLink:
    return VerifiedLink(
        kind="playoff_bracket",
        label=f"Open {season_to_year(season)} bracket",
        href=f"/playoffs?season={season}",
    )


def _slugify(value: str) -> str:
    return re.sub(r"^-|-$", "", re.sub(r"[^a-z0-9]+", "-", value.lower()))


def series_slug(series: dict) -> str | None:
    """The canonical slug the frontend derives for one playoffs-payload series.

    None when the payload lacks what the frontend needs, so no link is built.
    """
    round_number = series.get("round")
    if series.get("isFinals") or round_number == 4:
        return "the-finals"
    group = series.get("bracketGroupId")
    order = series.get("bracketOrder")
    if (
        not group
        or isinstance(round_number, bool)
        or not isinstance(round_number, int)
        or isinstance(order, bool)
        or not isinstance(order, int)
    ):
        return None
    round_slug = _ROUND_SLUGS.get(round_number, f"round-{round_number}")
    return f"{_slugify(str(group))}-{round_slug}-{order + 1}"


def series_href(season: str, series: dict) -> str | None:
    slug = series_slug(series)
    return None if slug is None else f"/playoffs/{season_to_year(season)}/{slug}"


def series_link(season: str, series: dict) -> VerifiedLink | None:
    # Slugs name the bracket position ("east-conference-final-1", "the-finals"),
    # never the teams, so the link itself reveals nothing.
    href = series_href(season, series)
    return None if href is None else VerifiedLink(kind="playoff_series", label="Open series", href=href)
