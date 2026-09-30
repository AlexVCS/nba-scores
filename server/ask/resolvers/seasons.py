"""Season tools. One NBA fetch first, one cached BRef fallback; no model I/O.

NBA player career rows are season totals. Use the provider aggregate (TEAM_ID=0)
for traded players, never a sum of rounded stint averages. Team records use the
team history endpoint; league/conference standings use LeagueStandings. No values
are combined across sources. Missing fields remain missing, never zero.

An optional ``Deadline`` is the time left in the Ask response. It is shared by
the NBA attempt, its retry and backoff, the fallback, and joined-cache waits.
A step that cannot fit is skipped, and the tool reports unavailable, never a
no-record answer. Without a deadline, the stage 2 behavior is unchanged.
"""
from __future__ import annotations

import datetime as dt
import logging
import math
from dataclasses import dataclass

from bs4 import BeautifulSoup, Comment
from nba_api.stats.endpoints import playercareerstats, leaguestandings, teamyearbyyearstats

from server.ask.cache import AskCache, CacheValue
from server.ask.candidates.players import get_player_index
from server.ask.candidates.teams import load_records
from server.ask.candidates.text import name_key
from server.ask.models.common import TeamRef
from server.ask.models.request import PlayerSeasonStatsRequest, TeamRecordsRequest
from server.ask.models.response import PlayerSeasonStatsResult, TeamRecordsResult, TeamRecordRow, SourceMetadata, StatValue, VerifiedLink
from server.ask.resolvers.errors import NotFoundError, UnavailableError, UnsupportedError
from server.ask.resolvers.output import ResolverOutput
from server.services import nba_stats_client, basketball_reference
from server.utils.deadline import Deadline, wait_timeout
from server.utils.ttl_cache import LoadInProgressError

logger = logging.getLogger(__name__)
_cache = AskCache(max_entries=128, version="season-1")
NBA_TIMEOUT_SECONDS = 4
JOIN_WAIT_SECONDS = 5
# The fallback starts only if a Basketball-Reference request can still start.
FALLBACK_MIN_SECONDS = basketball_reference.MIN_START_SECONDS
COUNTS = {"points": "PTS", "rebounds": "REB", "offensive_rebounds": "OREB", "defensive_rebounds": "DREB",
          "assists": "AST", "steals": "STL", "blocks": "BLK", "turnovers": "TOV", "fouls": "PF", "minutes": "MIN"}
SHOOTING = {"field_goals": ("FGM", "FGA"), "three_pointers": ("FG3M", "FG3A"), "free_throws": ("FTM", "FTA")}
PERCENTAGES = {"field_goal_percentage": "FG_PCT", "three_point_percentage": "FG3_PCT", "free_throw_percentage": "FT_PCT"}
LINE = ("points", "rebounds", "assists", "steals", "blocks", "turnovers", "minutes", "field_goals", "three_pointers", "free_throws")
BREF_STATS = {"PTS": ("pts",), "REB": ("trb",), "OREB": ("orb",), "DREB": ("drb",), "AST": ("ast",), "STL": ("stl",),
              "BLK": ("blk",), "TOV": ("tov",), "PF": ("pf",), "MIN": ("mp",), "FGM": ("fg",), "FGA": ("fga",),
              "FG3M": ("fg3",), "FG3A": ("fg3a",), "FTM": ("ft",), "FTA": ("fta",),
              "FG_PCT": ("fg_pct",), "FG3_PCT": ("fg3_pct",), "FT_PCT": ("ft_pct",)}


@dataclass(frozen=True)
class SeasonData:
    rows: tuple[dict, ...]
    source: str
    href: str
    fetched_at: dt.datetime
    complete: bool


def _now():
    return dt.datetime.now(dt.timezone.utc)


def _complete(season):
    # Deliberately conservative: cache a season long only after the following
    # November. This includes unusual late playoffs (2020) and stat corrections.
    return _now().date() >= dt.date(int(season[:4]) + 1, 11, 1)


def _number(value):
    if isinstance(value, bool) or value is None or value == "":
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (ValueError, TypeError):
        return None


def _integer(value):
    number = _number(value)
    if number is None or number < 0 or not number.is_integer():
        raise ValueError("Expected a nonnegative integer")
    return int(number)


def _dataset(payload, name):
    sets = payload.get("resultSets", []) if isinstance(payload, dict) else []
    matches = [s for s in sets if s.get("name") == name]
    if len(matches) != 1:
        raise ValueError("Missing NBA result set")
    table = matches[0]
    headers = table.get("headers", [])
    if not headers or len(headers) != len(set(headers)):
        raise ValueError("Invalid NBA headers")
    rows = table.get("rowSet")
    if not isinstance(rows, list) or any(not isinstance(r, list) or len(r) != len(headers) for r in rows):
        raise ValueError("Invalid NBA rows")
    return [dict(zip(headers, row)) for row in rows]


def _team(team_id, season, source_name=None):
    records = [r for r in load_records() if r.team_id == team_id and r.in_use(int(season[:4]))]
    if len(records) != 1:
        raise ValueError("Unverified historical team identity")
    r = records[0]
    allowed_names = {name_key(r.full_name)}
    if r.full_name == "Los Angeles Clippers":
        allowed_names.add(name_key("LA Clippers"))
    if source_name and name_key(source_name) not in allowed_names:
        raise ValueError("Team name does not match historical franchise")
    return TeamRef(team_id=r.team_id, tricode=r.abbreviation, name=r.full_name)


def _html_tables(html):
    soup = BeautifulSoup(html, "html.parser")
    for comment in soup.find_all(string=lambda value: isinstance(value, Comment)):
        if "<table" in comment:
            comment.replace_with(BeautifulSoup(str(comment), "html.parser"))
    return soup


def _heading(soup, season):
    heading = soup.find("h1")
    text = heading.get_text(" ", strip=True) if heading else ""
    if season not in text or not any(league in text for league in ("NBA", "BAA")):
        raise ValueError("BRef season/league heading mismatch")


def _cells(row):
    return {cell.get("data-stat"): cell.get_text(" ", strip=True) for cell in row.find_all(["th", "td"]) if cell.get("data-stat")}


def _timeout(deadline, seconds=NBA_TIMEOUT_SECONDS):
    return seconds if deadline is None else max(0.001, deadline.cap(seconds))


def _bref_player(request, deadline: Deadline | None = None):
    year = int(request.season[:4]) + 1
    league = "BAA" if year < 1950 else "NBA"
    href = f"https://www.basketball-reference.com/leagues/{league}_{year}_totals.html"
    soup = _html_tables(_html(href, request.season, deadline))
    _heading(soup, request.season)
    table_ids = {"totals_stats_post", "playoffs_totals"} if request.season_type == "playoffs" else {"totals_stats", "totals"}
    tables = [t for t in soup.find_all("table") if t.get("id") in table_ids]
    if len(tables) != 1:
        raise ValueError("BRef totals table missing or ambiguous")
    # Name-only cross-source matching is allowed only when the NBA catalog
    # independently proves one full-name identity in the requested season.
    index = get_player_index()
    identities = [p.player_id for p in index.players.values() if name_key(p.full_name) == name_key(request.player.name)
                  and p.from_year is not None and p.from_year <= year - 1 <= (year - 1 if p.active else p.to_year or p.from_year)]
    if identities != [request.player.player_id]:
        raise ValueError("BRef player identity cannot be verified")
    found = []
    player_links = set()
    for tr in tables[0].select("tbody tr"):
        cells = _cells(tr)
        name = cells.get("name_display", cells.get("player", "")).rstrip("*")
        if name_key(name) != name_key(request.player.name):
            continue
        anchor = tr.select_one('[data-stat="name_display"] a') or tr.select_one('[data-stat="player"] a')
        if anchor is None or not str(anchor.get("href", "")).startswith("/players/"):
            raise ValueError("BRef player link missing")
        player_links.add(anchor["href"])
        team_cell = tr.select_one('[data-stat="team_id"]') or tr.select_one('[data-stat="team_name_abbr"]')
        team_code = team_cell.get_text(strip=True) if team_cell else ""
        if request.team:
            anchor_team = team_cell.find("a") if team_cell else None
            if anchor_team is None:
                continue
            # Team page ending year and historical tricode are independently verified.
            from server.services.game_summary import to_bref_team_code
            tricode = _team(request.team.team_id, request.season).tricode
            code = {"PHX": "PHO", "BKN": "BRK", **({"CHA": "CHO"} if year >= 2015 else {})}.get(tricode, to_bref_team_code(tricode))
            if anchor_team.get("href") != f"/teams/{code}/{year}.html":
                continue
        found.append((team_code, {"GP": cells.get("games", cells.get("g")), **{key: next((cells[k] for k in names if k in cells), None)
                                                         for key, names in BREF_STATS.items()}}))
    if len(player_links) > 1:
        raise ValueError("Duplicate BRef player names")
    aggregates = [row for code, row in found if code == "TOT" or code.endswith("TM")]
    rows = aggregates if not request.team and aggregates else [row for _, row in found]
    if not rows:
        raise NotFoundError("no_record", "season_player_missing")
    if len(rows) != 1:
        raise ValueError("No unique BRef season aggregate")
    return SeasonData(tuple(rows), "basketball_reference", href, _now(), _complete(request.season))


def _html(href, season, deadline: Deadline | None = None):
    return _cache.get_or_load("bref-html", href, lambda: CacheValue(
        basketball_reference.get(href, deadline=deadline).text, 30),
        wait_timeout=wait_timeout(deadline, JOIN_WAIT_SECONDS)).value


def _nba_player(request, deadline: Deadline | None = None):
    endpoint = nba_stats_client._run("PlayerCareerStats", lambda: playercareerstats.PlayerCareerStats(
        player_id=request.player.player_id, per_mode36="Totals", league_id_nullable="00",
        headers=nba_stats_client._headers(), timeout=_timeout(deadline)), retries=1, deadline=deadline)
    table = "SeasonTotalsPostSeason" if request.season_type == "playoffs" else "SeasonTotalsRegularSeason"
    rows = _dataset(endpoint.get_dict(), table)
    matching = [r for r in rows if r.get("SEASON_ID") == request.season and str(r.get("LEAGUE_ID")) == "00"]
    if any(_integer(r.get("PLAYER_ID")) != request.player.player_id for r in matching):
        raise ValueError("NBA player identity mismatch")
    if request.team:
        matching = [r for r in matching if _integer(r.get("TEAM_ID")) == request.team.team_id]
    else:
        aggregate = [r for r in matching if _integer(r.get("TEAM_ID")) == 0]
        matching = aggregate or matching
    if not matching:
        raise NotFoundError("no_record", "season_player_missing")
    if len(matching) != 1:
        raise ValueError("No unique NBA season aggregate")
    return SeasonData(tuple(matching), "nba_stats", f"https://www.nba.com/stats/player/{request.player.player_id}/traditional?Season={request.season}&SeasonType={'Playoffs' if request.season_type == 'playoffs' else 'Regular%20Season'}", _now(), _complete(request.season))


def _valid_player(data, request):
    row = data.rows[0]
    games = _integer(row.get("GP"))
    if games == 0:
        raise NotFoundError("no_record", "season_player_missing")
    row = dict(row)
    start = int(request.season[:4])
    for cutoff, fields in ((1950, ("REB",)), (1951, ("MIN",)), (1973, ("STL", "BLK", "OREB", "DREB")), (1977, ("TOV",)), (1979, ("FG3M", "FG3A", "FG3_PCT"))):
        if start < cutoff:
            for field in fields:
                row[field] = None
    keys = LINE if request.stat.stat == "stat_line" else (request.stat.stat,)
    values = [_value(row, key, games, request.stat.aggregation) for key in keys]
    if any(v.value is None for v in values) and request.stat.stat != "stat_line":
        raise NotFoundError("no_record", "season_stat_missing")
    if not any(v.value is not None for v in values):
        raise NotFoundError("no_record", "season_stat_missing")
    return games, values


def _value(row, stat, games, aggregation):
    divisor = games if aggregation == "per_game" else 1
    def display(n):
        if n is None:
            return "Unavailable"
        return f"{n:.1f}" if aggregation == "per_game" else f"{n:g}"
    if stat in COUNTS:
        n = _number(row.get(COUNTS[stat]))
        n = n / divisor if n is not None and n >= 0 else None
        return StatValue(stat=stat, value=n, display=display(n))
    if stat in SHOOTING:
        made, attempted = [_number(row.get(k)) for k in SHOOTING[stat]]
        if made is None or attempted is None or not 0 <= made <= attempted:
            return StatValue(stat=stat, value=None, display="Unavailable")
        return StatValue(stat=stat, value=made / divisor, display=f"{display(made / divisor)}/{display(attempted / divisor)}",
                         made=int(made), attempted=int(attempted))
    if stat in PERCENTAGES:
        n = _number(row.get(PERCENTAGES[stat]))
        shooting = {"field_goal_percentage": "field_goals", "three_point_percentage": "three_pointers", "free_throw_percentage": "free_throws"}[stat]
        made, attempts = [_number(row.get(k)) for k in SHOOTING[shooting]]
        valid_attempts = made is not None and attempts is not None and attempts > 0 and 0 <= made <= attempts
        n = n if n is not None and 0 <= n <= 1 and valid_attempts else None
        return StatValue(stat=stat, value=n, display=f"{n * 100:.1f}%" if n is not None else "Unavailable")
    raise UnsupportedError("other", "unsupported_season_stat")


def _load(primary, fallback, validate, deadline: Deadline | None = None):
    # Validate BEFORE caching or returning, so a missing fact triggers fallback,
    # and a malformed response never becomes a long-lived successful cache entry.
    try:
        data = primary()
        validate(data)
        _source_link(data)
        return data
    except UnsupportedError:
        raise
    except Exception as exc:
        logger.info("ask_season_fallback reason=%s", type(exc).__name__)
        primary_missing = isinstance(exc, NotFoundError)
    if deadline is not None and not deadline.fits(FALLBACK_MIN_SECONDS):
        # A primary miss is not proof of absence; without fallback it is unavailable.
        logger.info("ask_season_fallback_skipped remaining_ms=%s", int(deadline.remaining() * 1000))
        raise UnavailableError("season_deadline_exceeded")
    try:
        data = fallback()
        validate(data)
        _source_link(data)
        return data
    except NotFoundError:
        if primary_missing:
            raise
        raise UnavailableError("season_sources_unavailable") from None
    except UnsupportedError:
        raise
    except Exception:
        raise UnavailableError("season_sources_unavailable") from None


def player_season(request: PlayerSeasonStatsRequest, deadline: Deadline | None = None):
    if request.stat.stat == "plus_minus":
        raise UnsupportedError("other", "unsupported_season_stat")
    # These facts were not recorded league-wide; another source cannot fill them.
    start = int(request.season[:4])
    if ((start < 1950 and request.stat.stat == "rebounds")
            or (start < 1951 and request.stat.stat == "minutes")
            or (start < 1977 and request.stat.stat == "turnovers")
            or (start < 1973 and request.stat.stat in {"steals", "blocks", "offensive_rebounds", "defensive_rebounds"})
            or (start < 1979 and request.stat.stat in {"three_pointers", "three_point_percentage"})):
        raise NotFoundError("no_record", "season_stat_not_recorded")
    data = _season_cached("player-season", request.model_dump_json(), lambda: _cached(
        _load(lambda: _nba_player(request, deadline), lambda: _bref_player(request, deadline),
              lambda d: _valid_player(d, request), deadline)), deadline).value
    games, values = _valid_player(data, request)
    missing = any(v.value is None for v in values)
    result = PlayerSeasonStatsResult(player=request.player, season=request.season, season_type=request.season_type,
                                    aggregation=request.stat.aggregation, team=request.team, games_played=games, values=values,
                                    coverage_note="Some statistics are unavailable for this season; missing values are not zero." if missing else None,
                                    as_of=data.fetched_at)
    return _output(result, data)


def _record(team, wins, losses, conference=None, rank=None):
    w, l = _integer(wins), _integer(losses)
    return TeamRecordRow(team=team, wins=w, losses=l, win_percentage=w / (w + l) if w + l else 0,
                         conference=conference, conference_rank=_integer(rank) if rank and _number(rank) and _number(rank) > 0 else None)


def _nba_records(request, deadline: Deadline | None = None):
    if request.team and request.standings_scope == "league":
        endpoint = nba_stats_client._run("TeamYearByYearStats", lambda: teamyearbyyearstats.TeamYearByYearStats(
            team_id=request.team.team_id, league_id="00", season_type_all_star="Regular Season",
            headers=nba_stats_client._headers(), timeout=_timeout(deadline)), retries=1, deadline=deadline)
        rows = [r for r in _dataset(endpoint.get_dict(), "TeamStats") if r.get("YEAR") == request.season]
        parsed = []
        for row in rows:
            if _integer(row.get("TEAM_ID")) != request.team.team_id:
                raise ValueError("NBA team identity mismatch")
            name = f"{row.get('TEAM_CITY', '')} {row.get('TEAM_NAME', '')}".strip()
            parsed.append(_record(_team(request.team.team_id, request.season, name), row.get("WINS"), row.get("LOSSES"), rank=row.get("CONF_RANK")))
    else:
        endpoint = nba_stats_client._run("LeagueStandings", lambda: leaguestandings.LeagueStandings(
            season=request.season, season_type="Regular Season", league_id="00",
            headers=nba_stats_client._headers(), timeout=_timeout(deadline)), retries=1, deadline=deadline)
        rows = _dataset(endpoint.get_dict(), "Standings")
        parsed = []
        expected_id = "2" + request.season[:4]
        for row in rows:
            if str(row.get("SeasonID")) != expected_id or str(row.get("LeagueID")) != "00":
                raise ValueError("NBA standings season/league mismatch")
            conf = {"East": "east", "West": "west", "Eastern": "east", "Western": "west"}.get(row.get("Conference"))
            if conf is None:
                raise ValueError("Unknown NBA conference")
            name = f"{row.get('TeamCity', '')} {row.get('TeamName', '')}".strip()
            parsed.append(_record(_team(_integer(row.get("TeamID")), request.season, name), row.get("WINS"), row.get("LOSSES"), conf, row.get("PlayoffRank")))
    if not parsed:
        raise NotFoundError("no_record", "season_records_missing")
    return SeasonData(tuple(r.model_dump() for r in parsed), "nba_stats",
                      f"https://www.nba.com/stats/teams/traditional?Season={request.season}&SeasonType=Regular%20Season", _now(), _complete(request.season))


def _bref_records(request, deadline: Deadline | None = None):
    year = int(request.season[:4]) + 1
    league = "BAA" if year < 1950 else "NBA"
    href = f"https://www.basketball-reference.com/leagues/{league}_{year}.html"
    soup = _html_tables(_html(href, request.season, deadline))
    _heading(soup, request.season)
    tables = []
    for side, conf in (("E", "east"), ("W", "west")):
        table = soup.find("table", id=f"confs_standings_{side}") or soup.find("table", id=f"divs_standings_{side}")
        if table:
            tables.append((table, conf))
    if not tables:
        table = soup.find("table", id="standings")
        if table:
            tables.append((table, None))
    if not tables:
        raise ValueError("BRef standings table missing")
    records = load_records()
    parsed = []
    for table, conf in tables:
        for tr in table.select("tbody tr"):
            cells = _cells(tr)
            name = cells.get("team_name", "").rstrip("*")
            if "wins" not in cells or "losses" not in cells:
                continue  # division separator or repeated header
            candidates = [r for r in records if r.in_use(year - 1) and name_key(r.full_name) == name_key(name)]
            if len(candidates) != 1:
                raise ValueError("Unverified BRef team")
            r = candidates[0]
            parsed.append(_record(_team(r.team_id, request.season, name), cells["wins"], cells["losses"], conf))
    if not parsed:
        raise NotFoundError("no_record", "season_records_missing")
    return SeasonData(tuple(r.model_dump() for r in parsed), "basketball_reference", href, _now(), _complete(request.season))


def _valid_records(data, request):
    rows = [TeamRecordRow.model_validate(row) for row in data.rows]
    if len({r.team.team_id for r in rows}) != len(rows):
        raise ValueError("Duplicate standings teams")
    if request.team:
        rows = [r for r in rows if r.team.team_id == request.team.team_id]
    else:
        expected = {r.team_id for r in load_records() if r.in_use(int(request.season[:4]))}
        if {r.team.team_id for r in rows} != expected:
            raise ValueError("Incomplete league standings")
    if request.standings_scope != "league":
        if any(r.conference is None for r in rows):
            raise UnsupportedError("other", "conference_unavailable")
        rows = [r for r in rows if r.conference == request.standings_scope]
    if not rows:
        raise NotFoundError("no_record", "season_records_missing")
    if request.team and len(rows) != 1:
        raise ValueError("No unique team record")
    # Conference tiebreak ranks are source facts. League rows are ordered by
    # percentage with equal percentages alphabetically; we never invent a rank.
    if request.standings_scope == "league":
        return sorted(rows, key=lambda r: (-r.win_percentage, r.team.name))
    return sorted(rows, key=lambda r: (r.conference_rank or 999, -r.win_percentage, r.team.name))


def team_records(request: TeamRecordsRequest, deadline: Deadline | None = None):
    data = _season_cached("team-records", request.model_dump_json(), lambda: _cached(
        _load(lambda: _nba_records(request, deadline), lambda: _bref_records(request, deadline),
              lambda d: _valid_records(d, request), deadline)), deadline).value
    result = TeamRecordsResult(season=request.season, team=request.team, standings_scope=request.standings_scope,
                               rows=_valid_records(data, request), as_of=data.fetched_at)
    return _output(result, data)


def _season_cached(namespace, key, loader, deadline: Deadline | None = None):
    try:
        return _cache.get_or_load(namespace, key, loader, wait_timeout=wait_timeout(deadline, JOIN_WAIT_SECONDS))
    except LoadInProgressError:
        raise UnavailableError("season_load_in_progress") from None


def _cached(data):
    return CacheValue(data, 86400 if data.complete else 30)


def _source_link(data):
    label = "Basketball-Reference" if data.source == "basketball_reference" else "NBA.com"
    return VerifiedLink(kind="source", label=f"Source: {label}", href=data.href, external=True)


def _output(result, data):
    label = "Basketball-Reference" if data.source == "basketball_reference" else "NBA.com"
    return ResolverOutput(result, (_source_link(data),),
                          (SourceMetadata(name=data.source, label=label, fetched_at=data.fetched_at, complete=data.complete),))
