"""Career stats (docs/ask-stage3.md, ADR 0013). stats.nba only; no model I/O.

A named player's career line comes from PlayerCareerStats career-total rows, with
averages computed from exact totals. All-time leaders and a player's rank come from
AllTimeLeadersGrids (TopX 250), totals of counting statistics only. There is no
Basketball-Reference fallback for this family.
"""
from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass

from nba_api.stats.endpoints import alltimeleadersgrids, playercareerstats

from server.ask.cache import CacheValue
from server.ask.candidates.players import get_player_index
from server.ask.models.common import PlayerRef
from server.ask.models.request import CareerStatsRequest
from server.ask.models.response import (
    CAREER_LIST_SIZE, CareerLeaderRow, CareerStatsResult, SourceMetadata, StatValue, VerifiedLink,
)
from server.ask.resolvers import seasons
from server.ask.resolvers.errors import NotFoundError, UnavailableError
from server.ask.resolvers.leaders import CATEGORIES, RECORDED_FROM, cut_ties
from server.ask.resolvers.output import ResolverOutput
from server.services import nba_stats_client
from server.utils.ttl_cache import LoadInProgressError

logger = logging.getLogger(__name__)
TTL_SECONDS = 3600  # active careers change nightly
FIRST_RECORDED = {"rebounds": "1950-51", "minutes": "1951-52", "offensive_rebounds": "1973-74",
                  "defensive_rebounds": "1973-74", "steals": "1973-74", "blocks": "1973-74", "turnovers": "1977-78",
                  "three_pointers": "1979-80", "three_point_percentage": "1979-80"}


@dataclass(frozen=True)
class CareerData:
    rows: tuple[dict, ...]  # player line: one row; boards: every category's rows under "category"
    href: str
    fetched_at: dt.datetime
    complete: bool


def _cached(namespace, key, loader):
    try:
        return seasons._cache.get_or_load(namespace, key, lambda: CacheValue(_loaded(loader), TTL_SECONDS),
                                          wait_timeout=5).value
    except LoadInProgressError:
        raise UnavailableError("season_load_in_progress") from None


def _loaded(loader):
    # stats.nba only (ADR 0013): a malformed or failed response is unavailable, never cached.
    try:
        return loader()
    except NotFoundError:
        raise
    except Exception as exc:
        logger.info("ask_career_unavailable reason=%s", type(exc).__name__)
        raise UnavailableError("career_source_unavailable") from None


def _catalog_player(player_id):
    return get_player_index().players.get(player_id)


# -- a player's career line -------------------------------------------------------------------


def _career_row(request: CareerStatsRequest) -> CareerData:
    endpoint = nba_stats_client._run("PlayerCareerStats", lambda: playercareerstats.PlayerCareerStats(
        player_id=request.player.player_id, per_mode36="Totals", league_id_nullable="00",
        headers=nba_stats_client._headers(), timeout=4), retries=1)
    table = "CareerTotalsPostSeason" if request.season_type == "playoffs" else "CareerTotalsRegularSeason"
    rows = [r for r in seasons._dataset(endpoint.get_dict(), table) if str(r.get("LEAGUE_ID")) == "00"]
    if any(seasons._integer(r.get("PLAYER_ID")) != request.player.player_id for r in rows):
        raise ValueError("NBA player identity mismatch")
    if not rows:
        raise NotFoundError("no_record", "career_missing")
    if len(rows) != 1:
        raise ValueError("No unique NBA career row")
    catalog = _catalog_player(request.player.player_id)
    return CareerData(tuple(rows), f"https://www.nba.com/stats/player/{request.player.player_id}/career",
                      seasons._now(), bool(catalog and not catalog.active))


def _player_values(data: CareerData, request: CareerStatsRequest):
    row = dict(data.rows[0])
    games = seasons._integer(row.get("GP"))
    if games == 0:
        raise NotFoundError("no_record", "career_missing")
    catalog = _catalog_player(request.player.player_id)
    first, last = (catalog.from_year, catalog.to_year) if catalog and catalog.from_year else (None, None)
    keys = seasons.LINE if request.stat.stat == "stat_line" else (request.stat.stat,)
    notes, partial = [], set()
    for stat in keys:
        started = RECORDED_FROM.get(stat)
        if started is None or first is None or first >= started:
            continue
        if last is not None and last < started and not (catalog and catalog.active):
            # The whole career predates the statistic: the source value is not a record.
            for column in _columns(stat):
                row[column] = None
            continue
        partial.add(stat)
        notes.append(stat)
    values = []
    for stat in keys:
        value = seasons._value(row, stat, games, request.stat.aggregation)
        if stat in partial and request.stat.aggregation == "per_game" and not stat.endswith("percentage"):
            # Games before the statistic existed would dilute the average.
            value = StatValue(stat=stat, value=None, display="Unavailable")
        values.append(value)
    if request.stat.stat != "stat_line" and values[0].value is None and not partial:
        raise NotFoundError("no_record", "career_stat_missing")
    if not partial and not any(v.value is not None for v in values):
        raise NotFoundError("no_record", "career_stat_missing")
    note = None
    if notes:
        first_seasons = sorted({FIRST_RECORDED[s] for s in notes})
        note = (f"Some statistics were first recorded in {', '.join(first_seasons)}; career totals cover only "
                "seasons since then, and their per-game averages are unavailable.")
    elif any(v.value is None for v in values):
        note = "Some statistics are unavailable for this career; missing values are not zero."
    return games, values, note


def _columns(stat):
    if stat in seasons.COUNTS:
        return (seasons.COUNTS[stat],)
    if stat in seasons.SHOOTING:
        return seasons.SHOOTING[stat]
    return (seasons.PERCENTAGES[stat],)


# -- all-time lists ---------------------------------------------------------------------------


def _board(season_type: str) -> CareerData:
    phase = "Playoffs" if season_type == "playoffs" else "Regular Season"
    endpoint = nba_stats_client._run("AllTimeLeadersGrids", lambda: alltimeleadersgrids.AllTimeLeadersGrids(
        league_id="00", per_mode_simple="Totals", season_type=phase, topx=CAREER_LIST_SIZE,
        headers=nba_stats_client._headers(), timeout=4), retries=1)
    payload = endpoint.get_dict()
    echoed = payload.get("parameters") if isinstance(payload, dict) else None
    expected = {"LeagueID": "00", "SeasonType": phase, "PerMode": "Totals", "TopX": str(CAREER_LIST_SIZE)}
    if not isinstance(echoed, dict) or any(str(echoed.get(k)) != v for k, v in expected.items()):
        raise ValueError("NBA all-time parameters do not match the request")
    boards = []
    for stat in sorted({"points", "rebounds", "offensive_rebounds", "defensive_rebounds", "assists", "steals",
                        "blocks", "turnovers", "field_goals", "three_pointers", "free_throws"}):
        category = CATEGORIES[stat]
        rows = seasons._dataset(payload, f"{category}Leaders")
        parsed = []
        for raw in rows:
            player_id, name = seasons._integer(raw.get("PLAYER_ID")), raw.get("PLAYER_NAME")
            value = seasons._number(raw.get(category))
            if player_id < 1 or not isinstance(name, str) or not name.strip() or value is None or value < 0 \
                    or not float(value).is_integer() or raw.get("IS_ACTIVE_FLAG") not in ("Y", "N"):
                raise ValueError("Invalid all-time row")
            parsed.append({"category": stat, "rank": seasons._integer(raw.get(f"{category}_RANK")),
                           "player_id": player_id, "name": name.strip(), "value": value,
                           "active": raw["IS_ACTIVE_FLAG"] == "Y"})
        parsed.sort(key=lambda r: r["rank"])
        _check_ranks(parsed)
        boards.extend(parsed)
    href = f"https://www.nba.com/stats/alltime-leaders?SeasonType={phase.replace(' ', '%20')}"
    return CareerData(tuple(boards), href, seasons._now(), False)


def _check_ranks(rows):
    if not rows or rows[0]["rank"] != 1 or len({r["player_id"] for r in rows}) != len(rows):
        raise ValueError("Invalid all-time list")
    for i in range(1, len(rows)):
        tied = rows[i]["rank"] == rows[i - 1]["rank"]
        if not (tied or rows[i]["rank"] == i + 1) or rows[i]["value"] > rows[i - 1]["value"] \
                or (tied and rows[i]["value"] != rows[i - 1]["value"]):
            raise ValueError("All-time ranks are inconsistent with values")


def _leader_value(stat, value):
    return StatValue(stat=stat, value=value, display=f"{value:,.0f}")


def _board_note(request):
    first = FIRST_RECORDED.get(request.stat.stat)
    if first is None:
        return None
    return f"This statistic was first recorded in {first}; earlier seasons are not included."


# -- executor ---------------------------------------------------------------------------------


def career_stats(request: CareerStatsRequest):
    common = dict(view=request.view, season_type=request.season_type, stat=request.stat.stat,
                  aggregation=request.stat.aggregation, player=request.player)
    if request.view == "player_totals":
        data = _cached("career-player", f"{request.player.player_id}|{request.season_type}", lambda: _career_row(request))
        games, values, note = _player_values(data, request)
        result = CareerStatsResult(**common, games_played=games, values=values, coverage_note=note, as_of=data.fetched_at)
        return _output(result, data)
    data = _cached("career-board", request.season_type, lambda: _board(request.season_type))
    rows = [r for r in data.rows if r["category"] == request.stat.stat]
    if request.view == "leaders":
        ranked = [CareerLeaderRow(rank=r["rank"], player=PlayerRef(player_id=r["player_id"], name=r["name"]),
                                  active=r["active"], value=_leader_value(request.stat.stat, r["value"])) for r in rows]
        shown, omitted = cut_ties(ranked, request.limit)
        result = CareerStatsResult(**common, limit=request.limit, rows=shown, omitted_tie=omitted,
                                   coverage_note=_board_note(request), as_of=data.fetched_at)
        return _output(result, data)
    mine = [r for r in rows if r["player_id"] == request.player.player_id]
    rank = mine[0]["rank"] if mine else None
    tied = sum(1 for r in rows if r["rank"] == rank) if mine else 0
    result = CareerStatsResult(**common, rank=rank, tied_count=tied if tied > 1 else None, list_size=CAREER_LIST_SIZE,
                               values=[_leader_value(request.stat.stat, mine[0]["value"])] if mine else [],
                               coverage_note=_board_note(request), as_of=data.fetched_at)
    return _output(result, data)


def _output(result, data):
    link = VerifiedLink(kind="source", label="Source: NBA.com", href=data.href, external=True)
    return ResolverOutput(result, (link,), (SourceMetadata(name="nba_stats", label="NBA.com", fetched_at=data.fetched_at,
                                                           complete=data.complete),))
