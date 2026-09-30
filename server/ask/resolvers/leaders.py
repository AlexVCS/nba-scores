"""Season leaders (docs/ask-stage3.md, ADR 0012). No model I/O.

stats.nba LeagueLeaders is primary and applies the NBA's qualification itself:
PerGame mode for per-game boards, Totals mode (with made-shot minimums) for
percentages. Basketball-Reference is a fallback for totals boards only, ranked
from its season totals table. One source per answer; ties share a rank and a tie
group is never split.
"""
from __future__ import annotations

from nba_api.stats.endpoints import leagueleaders

from server.ask.candidates.players import get_player_index
from server.ask.candidates.teams import load_records
from server.ask.candidates.text import name_key
from server.ask.models.common import LEADER_PERCENTAGES, MAX_LEADER_LIMIT, PlayerRef, TeamRef
from server.ask.models.request import SeasonLeadersRequest
from server.ask.models.response import MAX_LEADER_ROWS, OmittedTie, SeasonLeaderRow, SeasonLeadersResult, StatValue
from server.ask.resolvers import seasons
from server.ask.resolvers.errors import NotFoundError, UnsupportedError
from server.services import nba_stats_client

CATEGORIES = {
    "points": "PTS", "rebounds": "REB", "offensive_rebounds": "OREB", "defensive_rebounds": "DREB",
    "assists": "AST", "steals": "STL", "blocks": "BLK", "turnovers": "TOV", "minutes": "MIN",
    "field_goals": "FGM", "three_pointers": "FG3M", "free_throws": "FTM",
    "field_goal_percentage": "FG_PCT", "three_point_percentage": "FG3_PCT", "free_throw_percentage": "FT_PCT",
}
# Made/attempted columns shown beside a percentage or a made-shot total.
SHOTS = {"FGM": ("FGM", "FGA"), "FG3M": ("FG3M", "FG3A"), "FTM": ("FTM", "FTA"),
         "FG_PCT": ("FGM", "FGA"), "FG3_PCT": ("FG3M", "FG3A"), "FT_PCT": ("FTM", "FTA")}
# First season (start year) each statistic was recorded league-wide (Stage 2 cutoffs).
RECORDED_FROM = {"rebounds": 1950, "minutes": 1951, "offensive_rebounds": 1973, "defensive_rebounds": 1973,
                 "steals": 1973, "blocks": 1973, "turnovers": 1977, "three_pointers": 1979,
                 "three_point_percentage": 1979}
ALL_PLAYERS_NOTE = "All players who appeared; season totals have no minimum."
PER_GAME_NOTE = "Qualified players only, using NBA.com's per-game minimum for this season."
PERCENT_NOTE = "Qualified shooters only, using NBA.com's made-shot minimum for this season."
TITLE_ERA_NOTE = ("Before 1969-70 the NBA awarded statistical titles on season totals, so the "
                  "title holder can differ from the per-game leader shown.")


class FallbackNotAllowed(ValueError):
    """Per-game and percentage boards have no fallback (ADR 0012)."""


def _mode(request: SeasonLeadersRequest) -> str:
    # The endpoint rejects PerGame percentages; Totals applies the made-shot minimum.
    if request.stat.stat in LEADER_PERCENTAGES or request.stat.aggregation == "total":
        return "Totals"
    return "PerGame"


def _season_type(request: SeasonLeadersRequest) -> str:
    return "Playoffs" if request.season_type == "playoffs" else "Regular Season"


def _nba_href(request):
    season_type = _season_type(request).replace(" ", "%20")
    return (f"https://www.nba.com/stats/leaders?Season={request.season}&SeasonType={season_type}"
            f"&PerMode={_mode(request)}&StatCategory={CATEGORIES[request.stat.stat]}")


def _table(payload):
    tables = payload.get("resultSets") if isinstance(payload, dict) else None
    if tables is None and isinstance(payload, dict) and isinstance(payload.get("resultSet"), dict):
        tables = [payload["resultSet"]]
    matches = [t for t in tables or [] if isinstance(t, dict) and t.get("name") == "LeagueLeaders"]
    if len(matches) != 1:
        raise ValueError("Missing NBA leaders result set")
    headers, rows = matches[0].get("headers") or [], matches[0].get("rowSet")
    if not headers or len(headers) != len(set(headers)):
        raise ValueError("Invalid NBA headers")
    if not isinstance(rows, list) or any(not isinstance(r, list) or len(r) != len(headers) for r in rows):
        raise ValueError("Invalid NBA rows")
    return [dict(zip(headers, row)) for row in rows]


def _nba_board(request: SeasonLeadersRequest) -> seasons.SeasonData:
    category, mode, season_type = CATEGORIES[request.stat.stat], _mode(request), _season_type(request)
    endpoint = nba_stats_client._run("LeagueLeaders", lambda: leagueleaders.LeagueLeaders(
        league_id="00", per_mode48=mode, scope="S", season=request.season, season_type_all_star=season_type,
        stat_category_abbreviation=category, headers=nba_stats_client._headers(), timeout=4), retries=1)
    payload = endpoint.get_dict()
    echoed = payload.get("parameters") if isinstance(payload, dict) else None
    expected = {"LeagueID": "00", "PerMode": mode, "StatCategory": category, "Season": request.season,
                "SeasonType": season_type}
    if not isinstance(echoed, dict) or any(echoed.get(k) != v for k, v in expected.items()):
        raise ValueError("NBA leaders parameters do not match the request")
    rows = []
    for raw in _table(payload):
        player_id, games = seasons._integer(raw.get("PLAYER_ID")), seasons._integer(raw.get("GP"))
        name = raw.get("PLAYER")
        if player_id < 1 or games < 1 or not isinstance(name, str) or not name.strip():
            raise ValueError("Invalid NBA leader identity")
        made, attempted = SHOTS.get(category, (None, None))
        rows.append({"rank": seasons._integer(raw.get("RANK")), "player_id": player_id, "name": name.strip(),
                     "team_id": seasons._number(raw.get("TEAM_ID")), "multiple_teams": False, "games": games,
                     "value": seasons._number(raw.get(category)),
                     "made": seasons._number(raw.get(made)) if made else None,
                     "attempted": seasons._number(raw.get(attempted)) if attempted else None})
    if not rows:
        raise NotFoundError("no_record", "season_leaders_missing")
    rows.sort(key=lambda r: r["rank"])
    rows = _top(rows)
    for row in rows:
        row["team"] = _nba_team(row.pop("team_id"), request.season)
    return seasons.SeasonData(tuple(rows), "nba_stats", _nba_href(request), seasons._now(),
                              seasons._complete(request.season))


def _top(rows):
    """Keep every row that any top N (N <= 25) could show, ties included."""
    return [r for r in rows if r["rank"] <= MAX_LEADER_LIMIT]


def _nba_team(team_id, season):
    """The row's franchise that season. Franchises outside the catalog (defunct
    early teams) are left blank; a known franchise out of its era is an error."""
    if not team_id:
        return None
    if int(team_id) not in {r.team_id for r in load_records()}:
        return None
    return seasons._team(int(team_id), season).model_dump()


def _bref_team(code, season):
    from server.services.game_summary import to_bref_team_code
    start = int(season[:4])
    matches = []
    for record in load_records():
        if not record.in_use(start):
            continue
        codes = {record.abbreviation, to_bref_team_code(record.abbreviation),
                 {"PHX": "PHO", "BKN": "BRK", **({"CHA": "CHO"} if start >= 2014 else {})}.get(record.abbreviation, "")}
        if code in codes:
            matches.append(record.team_id)
    if not matches:
        return None  # a franchise outside the catalog (defunct early team): left blank
    if len(set(matches)) != 1:
        raise ValueError("Unverified BRef team code")
    return seasons._team(matches[0], season).model_dump()


def _catalog_identity(name, season):
    start = int(season[:4])
    index = get_player_index()
    ids = [p.player_id for p in index.players.values() if name_key(p.full_name) == name_key(name)
           and p.from_year is not None and p.from_year <= start <= (start if p.active else p.to_year or p.from_year)]
    if len(ids) != 1:
        raise ValueError("BRef leader identity cannot be verified")
    return ids[0]


def _bref_board(request: SeasonLeadersRequest) -> seasons.SeasonData:
    if _mode(request) != "Totals" or request.stat.stat in LEADER_PERCENTAGES:
        raise FallbackNotAllowed("No verified fallback qualification for this board")
    year = int(request.season[:4]) + 1
    league = "BAA" if year < 1950 else "NBA"
    href = f"https://www.basketball-reference.com/leagues/{league}_{year}_totals.html"
    soup = seasons._html_tables(seasons._html(href, request.season))
    seasons._heading(soup, request.season)
    table_ids = {"totals_stats_post", "playoffs_totals"} if request.season_type == "playoffs" else {"totals_stats", "totals"}
    tables = [t for t in soup.find_all("table") if t.get("id") in table_ids]
    if len(tables) != 1:
        raise ValueError("BRef totals table missing or ambiguous")
    category = CATEGORIES[request.stat.stat]
    column = seasons.BREF_STATS[category][0]
    by_player: dict[str, list[tuple[str, dict]]] = {}
    for tr in tables[0].select("tbody tr"):
        anchor = tr.select_one('[data-stat="name_display"] a') or tr.select_one('[data-stat="player"] a')
        if anchor is None:
            continue  # repeated header or league-average row
        href_player = str(anchor.get("href", ""))
        if not href_player.startswith("/players/"):
            raise ValueError("BRef player link missing")
        cells = seasons._cells(tr)
        code = cells.get("team_name_abbr", cells.get("team_id", ""))
        by_player.setdefault(href_player, []).append((code, cells))
    rows = []
    for player_rows in by_player.values():
        aggregate = [r for r in player_rows if r[0] == "TOT" or r[0].endswith("TM")]
        if len(player_rows) > 1 and len(aggregate) != 1:
            raise ValueError("No unique BRef season aggregate")
        code, cells = aggregate[0] if aggregate else player_rows[0]
        games = seasons._number(cells.get("games", cells.get("g")))
        if not games:
            continue
        value = seasons._number(cells.get(column))
        if value is None or value < 0:
            raise ValueError("BRef recorded statistic missing")
        made, attempted = SHOTS.get(category, (None, None))
        rows.append({"name": cells.get("name_display", cells.get("player", "")).rstrip("*").strip(), "code": code,
                     "games": int(games), "value": value,
                     "made": seasons._number(cells.get(seasons.BREF_STATS[made][0])) if made else None,
                     "attempted": seasons._number(cells.get(seasons.BREF_STATS[attempted][0])) if attempted else None})
    if not rows:
        raise NotFoundError("no_record", "season_leaders_missing")
    # Competition ranking on exact totals.
    rows.sort(key=lambda r: (-r["value"], r["name"]))
    for i, row in enumerate(rows):
        row["rank"] = rows[i - 1]["rank"] if i and row["value"] == rows[i - 1]["value"] else i + 1
    shown = _top(rows)
    for row in shown:
        # Only rows that can be shown need a verified NBA identity and team.
        row["player_id"] = _catalog_identity(row["name"], request.season)
        code = row.pop("code")
        row["multiple_teams"] = code == "TOT" or code.endswith("TM")
        row["team"] = None if row["multiple_teams"] else _bref_team(code, request.season)
    return seasons.SeasonData(tuple(shown), "basketball_reference", href, seasons._now(),
                              seasons._complete(request.season))


def _stat_value(request, row, category):
    stat, value = request.stat.stat, row["value"]
    if value is None or value < 0:
        raise ValueError("Missing leader value")
    made, attempted = row.get("made"), row.get("attempted")
    if stat in LEADER_PERCENTAGES:
        if not (value <= 1 and made is not None and attempted and 0 <= made <= attempted):
            raise ValueError("Invalid leader percentage")
        return StatValue(stat=stat, value=value, display=f"{value * 100:.1f}%", made=int(made), attempted=int(attempted))
    if _mode(request) == "PerGame":
        return StatValue(stat=stat, value=value, display=f"{value:.1f}")
    if not float(value).is_integer():
        raise ValueError("Season totals must be whole numbers")
    shots = {}
    if made is not None and attempted is not None and float(made).is_integer() and float(attempted).is_integer():
        shots = {"made": int(made), "attempted": int(attempted)}
    return StatValue(stat=stat, value=value, display=f"{value:g}", **shots)


def _rows(data: seasons.SeasonData, request: SeasonLeadersRequest):
    """Validate a cached board and cut it to the requested top N without splitting a tie."""
    category = CATEGORIES[request.stat.stat]
    rows = []
    for raw in data.rows:
        rows.append(SeasonLeaderRow(rank=raw["rank"], player=PlayerRef(player_id=raw["player_id"], name=raw["name"]),
                                    team=TeamRef.model_validate(raw["team"]) if raw["team"] else None,
                                    multiple_teams=raw["multiple_teams"],
                                    games_played=raw["games"], value=_stat_value(request, raw, category)))
    if not rows:
        raise NotFoundError("no_record", "season_leaders_missing")
    if len({r.player.player_id for r in rows}) != len(rows):
        raise ValueError("Duplicate leader rows")
    for i, row in enumerate(rows):
        if i == 0:
            if row.rank != 1:
                raise ValueError("Leaders must start at rank 1")
            continue
        previous = rows[i - 1]
        tied = row.rank == previous.rank
        # Ranks are competition ranks on unrounded values, so rounded values never rise.
        if not (tied or row.rank == i + 1) or row.value.value > previous.value.value or (tied and row.value.value != previous.value.value):
            raise ValueError("Leader ranks are inconsistent with values")
    return cut_ties(rows, request.limit)


def cut_ties(rows, limit):
    """Every row ranked ``limit`` or better; a tie group past the row cap is left out whole.

    With limit <= 25 and competition ranks, only the last tie group can cross the cap."""
    shown = [r for r in rows if r.rank <= limit]
    omitted = None
    if len(shown) > MAX_LEADER_ROWS:
        crossing = shown[MAX_LEADER_ROWS].rank
        omitted = OmittedTie(rank=crossing, count=sum(1 for r in shown if r.rank == crossing))
        shown = [r for r in shown if r.rank < crossing]
        if not shown:
            raise UnsupportedError("other", "leader_tie_overflow")
    return shown, omitted


def season_leaders(request: SeasonLeadersRequest):
    start = int(request.season[:4])
    if start < RECORDED_FROM.get(request.stat.stat, 0):
        # Not recorded league-wide; neither source can fill it, so spend no fetch.
        raise NotFoundError("no_record", "season_stat_not_recorded")
    key = f"{request.season}|{request.season_type}|{request.stat.stat}|{_mode(request)}"
    data = seasons._season_cached("season-leaders", key, lambda: seasons._cached(seasons._load(
        lambda: _nba_board(request), lambda: _bref_board(request), lambda d: _rows(d, request)))).value
    rows, omitted = _rows(data, request)
    per_game = _mode(request) == "PerGame"
    qualified = per_game or request.stat.stat in LEADER_PERCENTAGES
    result = SeasonLeadersResult(
        season=request.season, season_type=request.season_type, stat=request.stat.stat,
        aggregation=request.stat.aggregation, limit=request.limit,
        qualification="source_qualified" if qualified else "all_players",
        qualification_note=PER_GAME_NOTE if per_game else PERCENT_NOTE if qualified else ALL_PLAYERS_NOTE,
        rows=rows, omitted_tie=omitted,
        coverage_note=TITLE_ERA_NOTE if per_game and start < 1969 and request.season_type == "regular_season" else None,
        as_of=data.fetched_at)
    return seasons._output(result, data)

