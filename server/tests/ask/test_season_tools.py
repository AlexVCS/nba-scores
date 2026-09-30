"""Stage 2 source boundaries, identity checks, missing facts and typed answers."""
import datetime as dt
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import pytest
import requests

from server.ask import tools
from server.ask.candidates.lookup import CandidateLookupService
from server.ask.candidates.teams import load_records
from server.ask.models.request import PlayerSeasonStatsRequest, TeamRecordsRequest, AskContext
from server.ask.models.interpreter import InterpreterOutput, InterpreterMetadata, FieldInterpretation
from server.ask.models.response import AskResponse, VerifiedLink
from server.ask.normalize import Normalizer
from server.ask.present import interpretation
from server.ask.resolvers import seasons
from server.ask.resolvers.errors import NotFoundError, UnavailableError, UnsupportedError
from server.services import basketball_reference, game_summary

PLAYER = {"player_id": 203999, "name": "Nikola Jokic"}
DEN = {"team_id": 1610612743, "tricode": "DEN", "name": "Denver Nuggets"}
CONTEXT = AskContext(reference_time=dt.datetime.fromisoformat("2026-09-29T12:00:00-04:00"))


def request(stat="rebounds", aggregation="per_game", **kwargs):
    return PlayerSeasonStatsRequest(player=PLAYER, season="2023-24", stat={"stat": stat, "aggregation": aggregation}, **kwargs)


def row(**kwargs):
    return {"PLAYER_ID": 203999, "SEASON_ID": "2023-24", "LEAGUE_ID": "00", "TEAM_ID": 1610612743,
            "GP": 79, "REB": 976, "PTS": 2085, "AST": 708, "STL": 108, "BLK": 68, "TOV": 237,
            "PF": 194, "MIN": 2737, "FGM": 822, "FGA": 1411, "FG_PCT": .583,
            "FG3M": 83, "FG3A": 231, "FG3_PCT": .359, "FTM": 358, "FTA": 439, "FT_PCT": .815, **kwargs}


def nba_payload(rows, name="SeasonTotalsRegularSeason"):
    headers = list(rows[0]) if rows else list(row())
    return {"resultSets": [{"name": name, "headers": headers, "rowSet": [[r.get(k) for k in headers] for r in rows]}]}


def install_nba(monkeypatch, rows, name="SeasonTotalsRegularSeason"):
    calls = []
    def career(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(get_dict=lambda: nba_payload(rows, name))
    monkeypatch.setattr(seasons.playercareerstats, "PlayerCareerStats", career)
    return calls


def source_data(rows, source="nba_stats", complete=True):
    return seasons.SeasonData(tuple(rows), source, "https://www.nba.com/stats/teams/traditional?Season=2023-24",
                              dt.datetime(2026, 9, 29, tzinfo=dt.timezone.utc), complete)


@pytest.fixture(autouse=True)
def clean_sources(monkeypatch):
    seasons._cache.clear()
    monkeypatch.setattr(basketball_reference, "_next_start", 0)
    monkeypatch.setattr(basketball_reference.requests, "get", lambda *a, **k: (_ for _ in ()).throw(AssertionError("Unexpected network")))
    monkeypatch.setattr(seasons.playercareerstats, "PlayerCareerStats", lambda **k: (_ for _ in ()).throw(AssertionError("Unexpected NBA network")))


def test_player_per_game_uses_totals_and_completed_cache(monkeypatch):
    calls = install_nba(monkeypatch, [row()])
    monkeypatch.setattr(seasons, "_bref_player", lambda r: pytest.fail("Fallback on valid NBA data"))
    output = seasons.player_season(request())
    assert output.result.values[0].value == pytest.approx(976 / 79)
    assert output.result.values[0].display == "12.4"
    assert output.result.games_played == 79
    assert output.sources[0].name == "nba_stats" and output.sources[0].complete
    assert calls[0]["per_mode36"] == "Totals" and calls[0]["timeout"] == 4
    seasons.player_season(request())
    assert len(calls) == 1


def test_traded_player_aggregate_not_sum_of_stints(monkeypatch):
    install_nba(monkeypatch, [row(TEAM_ID=0, REB=100, GP=10), row(REB=40, GP=3), row(TEAM_ID=1610612738, REB=60, GP=7)])
    assert seasons.player_season(request()).result.values[0].value == 10
    assert seasons.player_season(request(team=DEN)).result.values[0].value == pytest.approx(40 / 3)


def test_playoffs_are_separate_from_regular_season(monkeypatch):
    calls = install_nba(monkeypatch, [row(GP=12, REB=100)], "SeasonTotalsPostSeason")
    result = seasons.player_season(request(season_type="playoffs")).result
    assert result.games_played == 12 and result.season_type == "playoffs"
    assert len(calls) == 1


def test_wrong_player_row_falls_back_without_merging(monkeypatch):
    install_nba(monkeypatch, [row(PLAYER_ID=2544, REB=100000)])
    monkeypatch.setattr(seasons, "_bref_player", lambda r: source_data([row(REB=79)], "basketball_reference"))
    result = seasons.player_season(request())
    assert result.result.values[0].value == 1
    assert result.sources[0].name == "basketball_reference"


@pytest.mark.parametrize("bad", [None, float("nan"), -1, True])
def test_missing_specific_stat_triggers_fallback(monkeypatch, bad):
    install_nba(monkeypatch, [row(REB=bad)])
    monkeypatch.setattr(seasons, "_bref_player", lambda r: source_data([row(REB=158)], "basketball_reference"))
    assert seasons.player_season(request()).result.values[0].value == 2


def test_no_record_requires_successful_missing_records(monkeypatch):
    install_nba(monkeypatch, [])
    monkeypatch.setattr(seasons, "_bref_player", lambda r: (_ for _ in ()).throw(NotFoundError("no_record", "missing")))
    with pytest.raises(NotFoundError):
        seasons.player_season(request())
    monkeypatch.setattr(seasons, "_bref_player", lambda r: (_ for _ in ()).throw(requests.HTTPError("403")))
    with pytest.raises(UnavailableError):
        seasons.player_season(request())


def test_all_missing_stats_and_plus_minus_do_not_become_answers(monkeypatch):
    with pytest.raises(UnsupportedError):
        seasons.player_season(request("plus_minus"))
    install_nba(monkeypatch, [row(REB=None)])
    monkeypatch.setattr(seasons, "_bref_player", lambda r: source_data([row(REB=None)]))
    with pytest.raises(NotFoundError):
        seasons.player_season(request())


def test_missing_full_line_values_remain_missing(monkeypatch):
    install_nba(monkeypatch, [row(STL=None, BLK=None)])
    result = seasons.player_season(request("stat_line")).result
    assert result.coverage_note and [v.value for v in result.values if v.stat == "steals"] == [None]
    assert next(v for v in result.values if v.stat == "steals").display == "Unavailable"


def test_percentages_and_made_attempted_keep_units(monkeypatch):
    install_nba(monkeypatch, [row()])
    assert seasons.player_season(request("field_goal_percentage")).result.values[0].display == "58.3%"
    fg = seasons.player_season(request("field_goals")).result.values[0]
    assert fg.display == "10.4/17.9" and fg.made == 822 and fg.attempted == 1411


def player_html(rows, heading="2023-24 NBA Player Stats: Totals"):
    def tr(code, rebounds):
        return f'<tr><td data-stat="player"><a href="/players/j/jokicni01.html">Nikola Jokić</a></td><td data-stat="team_id">{code}</td><td data-stat="g">79</td><td data-stat="trb">{rebounds}</td></tr>'
    return f'<h1>{heading}</h1><!--<table id="totals_stats"><tbody>{"".join(tr(*r) for r in rows)}</tbody></table>-->'


def test_bref_commented_table_and_aggregate(monkeypatch):
    monkeypatch.setattr(seasons, "_html", lambda *a: player_html([("TOT", 976), ("DEN", 500), ("BOS", 476)]))
    data = seasons._bref_player(request())
    assert data.rows[0]["REB"] == "976" and data.source == "basketball_reference"
    assert data.href.endswith("NBA_2024_totals.html")


def test_bref_duplicate_stints_without_aggregate_are_unavailable(monkeypatch):
    monkeypatch.setattr(seasons, "_html", lambda *a: player_html([("DEN", 500), ("BOS", 476)]))
    with pytest.raises(ValueError):
        seasons._bref_player(request())


def team_rows():
    records = [r for r in load_records() if r.in_use(2023)]
    return [seasons._record(seasons._team(r.team_id, "2023-24"), 50, 32, "east" if i % 2 else "west").model_dump()
            for i, r in enumerate(records)]


def test_standings_reject_partial_or_duplicate_tables():
    rows = team_rows()
    request = TeamRecordsRequest(season="2023-24")
    assert len(seasons._valid_records(source_data(rows), request)) == 30
    with pytest.raises(ValueError):
        seasons._valid_records(source_data(rows[:-1]), request)
    with pytest.raises(ValueError):
        seasons._valid_records(source_data(rows + rows[:1]), request)


def test_conference_filter_and_single_team_filter():
    rows = team_rows()
    result = seasons._valid_records(source_data(rows), TeamRecordsRequest(season="2023-24", standings_scope="east"))
    assert len(result) == 15 and all(r.conference == "east" for r in result)
    result = seasons._valid_records(source_data(rows), TeamRecordsRequest(season="2023-24", team=DEN))
    assert len(result) == 1 and result[0].team.team_id == DEN["team_id"]


def test_nba_team_history_validates_identity_and_record(monkeypatch):
    values = {"TEAM_ID": DEN["team_id"], "YEAR": "2023-24", "TEAM_CITY": "Denver", "TEAM_NAME": "Nuggets", "WINS": 57, "LOSSES": 25, "CONF_RANK": 2}
    calls = []
    monkeypatch.setattr(seasons.teamyearbyyearstats, "TeamYearByYearStats", lambda **k: calls.append(k) or SimpleNamespace(get_dict=lambda: nba_payload([values], "TeamStats")))
    output = seasons.team_records(TeamRecordsRequest(team=DEN, season="2023-24"))
    assert output.result.rows[0].wins == 57 and output.result.rows[0].losses == 25
    assert output.result.rows[0].win_percentage == pytest.approx(57 / 82)
    assert calls[0]["season_type_all_star"] == "Regular Season"
    seasons._cache.clear()
    values["TEAM_ID"] = 1
    monkeypatch.setattr(seasons, "_bref_records", lambda r: (_ for _ in ()).throw(ValueError()))
    with pytest.raises(UnavailableError):
        seasons.team_records(TeamRecordsRequest(team=DEN, season="2023-24"))


def test_completed_and_current_seasons_have_different_cache_ttl(monkeypatch):
    data = source_data([row()], complete=False)
    assert seasons._cached(data).ttl_seconds == 30
    assert seasons._cached(source_data([row()])).ttl_seconds == 86400
    monkeypatch.setattr(seasons, "_now", lambda: dt.datetime(2020, 9, 1, tzinfo=dt.timezone.utc))
    assert not seasons._complete("2019-20")


def test_limiter_limits_all_callers_and_refuses_redirects(monkeypatch):
    calls = []
    response = SimpleNamespace(text="ok", status_code=200, raise_for_status=lambda: None)
    monkeypatch.setattr(basketball_reference.requests, "get", lambda *a, **k: calls.append(k) or response)
    monkeypatch.setattr(basketball_reference.time, "monotonic", lambda: 100)
    basketball_reference.get("https://www.basketball-reference.com/leagues/NBA_2024.html")
    with pytest.raises(basketball_reference.FallbackRateLimited):
        game_summary.fetch_bref_line_score("2024-01-01", "DEN")
    assert calls[0]["allow_redirects"] is False and "NBA-Scorez" in calls[0]["headers"]["User-Agent"]
    assert len(calls) == 1
    monkeypatch.setattr(basketball_reference.time, "monotonic", lambda: 107)
    response.status_code = 302
    with pytest.raises(requests.RequestException):
        basketball_reference.get("https://www.basketball-reference.com/leagues/NBA_2024.html")


def test_limiter_concurrent_requests_have_one_start(monkeypatch):
    monkeypatch.setattr(basketball_reference.time, "monotonic", lambda: 100)
    calls = []
    monkeypatch.setattr(basketball_reference.requests, "get", lambda *a, **k: calls.append(k) or SimpleNamespace(status_code=200, raise_for_status=lambda: None))
    def fetch(_):
        try:
            basketball_reference.get("https://www.basketball-reference.com/leagues/NBA_2024.html")
            return True
        except basketball_reference.FallbackRateLimited:
            return False
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(fetch, range(8))) == 1
    assert len(calls) == 1


@pytest.mark.parametrize("url", ["https://www.basketball-reference.com.evil/leagues/NBA_2024.html", "https://www.basketball-reference.com/players/j/jokicni01.html", "https://www.basketball-reference.com/leagues/NBA_2024.html?evil=1"])
def test_source_link_allowlist_rejects_other_paths(url):
    with pytest.raises(ValueError):
        VerifiedLink(kind="source", label="Source", href=url, external=True)


def interpreted(intent, fields):
    return InterpreterOutput(outcome="interpreted", fields=[FieldInterpretation(field=k, status="selected", selected=v if isinstance(v,list) else [v], confidence=1)
                                                             for k,v in {"intent":intent, **fields}.items()],
                             metadata=InterpreterMetadata(adapter="jev", provider="test", model="test", latency_ms=0))


def test_new_families_normalize_real_lookup_and_report_units():
    lookup = CandidateLookupService()
    q = "Nikola Jokic rebounds per game in 2023-24"
    c = lookup.lookup(q, CONTEXT)
    o = interpreted("player_season_stats", {"player":"player:203999", "season":"season:2023-24", "stat":"rebounds", "aggregation":"per_game"})
    n = Normalizer().normalize(o,c,CONTEXT)
    assert n.status == "valid" and n.request.season_type == "regular_season"
    readout = interpretation(o,c,CONTEXT,n.request)
    assert readout.detected_type == "season_stats" and readout.season == "2023-24"
    assert any(i.field == "aggregation" and i.value == "Per Game" for i in readout.items)
    q = "Celtics record in 2007-08"
    c = lookup.lookup(q, CONTEXT)
    n = Normalizer().normalize(interpreted("team_records", {"season":"season:2007-08", "teams":["team:1610612738"]}),c,CONTEXT)
    assert n.status == "valid" and n.request.team.team_id == 1610612738


def test_missing_season_is_clarified_not_defaulted():
    c = CandidateLookupService().lookup("Jokic points per game", CONTEXT)
    n = Normalizer().normalize(interpreted("player_season_stats", {"player":"player:203999", "stat":"points", "aggregation":"per_game"}),c,CONTEXT)
    assert n.status == "needs_clarification" and n.clarify_field == "season"


def test_bare_regular_year_stays_ambiguous():
    c = CandidateLookupService().lookup("Celtics record in 2008", CONTEXT)
    assert {v.value.season for v in c.sets["season"].candidates} == {"2007-08", "2008-09"}


def test_stage2_interpreter_closed_fields_are_offered_by_both_adapters():
    from server.ask.interpreters.jev import build_questions
    from server.ask.interpreters.openai_responses import build_schema
    from server.ask.interpreters import closed_sets
    c = CandidateLookupService().lookup("2023-24 Eastern conference standings", CONTEXT)
    questions, _ = build_questions(c)
    schema = build_schema(c)["properties"]
    for field in ("season_type", "standings_scope"):
        assert field in questions and field in schema
    assert not {"season_stats", "standings", "regular_season_record"}.intersection(closed_sets.UNSUPPORTED_REASONS)


def test_bref_wrong_season_heading_is_rejected(monkeypatch):
    monkeypatch.setattr(seasons, "_html", lambda *a: player_html([("DEN", 976)], heading="2022-23 NBA Player Stats: Totals"))
    with pytest.raises(ValueError):
        seasons._bref_player(request())


@pytest.mark.parametrize("question", ["Jokic rebounds per game at home in 2023-24", "Jokic points per 36 in 2023-24", "Jokic points per game in March 2024", "Jokic points against Boston in 2023-24", "Celtics record at home in 2023-24", "Atlantic division standings in 2023-24", "Celtics record before March 1, 2024", "Celtics best record in 2023-24"])
def test_unrepresented_season_splits_are_never_executed(question):
    from server.ask.season_scope import normalize_question
    c = CandidateLookupService().lookup(question, CONTEXT)
    if "Jokic" in question:
        intent, fields = "player_season_stats", {"player":"player:203999", "stat":"points", "aggregation":"per_game"}
    else:
        intent, fields = "team_records", {}
    if c.sets["season"].candidates:
        fields["season"] = c.sets["season"].candidates[0].id
    output = interpreted(intent, fields)
    assert normalize_question(Normalizer(),output,c,CONTEXT,question).status == "unsupported"


def test_stage2_source_fixtures_round_trip_response_contract():
    fixtures = Path(__file__).resolve().parents[3] / "src/services/ask/fixtures/responses"
    for name in ("answer-player-season", "answer-team-record", "answer-standings"):
        response = AskResponse.model_validate_json((fixtures / f"{name}.json").read_text())
        assert response.outcome == "answer" and response.interpretation.season == "2023-24"


def test_official_nba_clippers_abbreviation_is_not_a_name_mismatch():
    assert seasons._team(1610612746, "2023-24", "LA Clippers").name == "Los Angeles Clippers"
    with pytest.raises(ValueError):
        seasons._team(1610612738, "2023-24", "LA Clippers")


def test_nba_league_standings_season_and_historical_identity(monkeypatch):
    records = [r for r in load_records() if r.in_use(2023)]
    raw = [{"LeagueID":"00", "SeasonID":"22023", "TeamID":r.team_id, "TeamCity":r.city, "TeamName":r.nickname,
            "Conference":"East" if i % 2 else "West", "WINS":50, "LOSSES":32, "PlayoffRank":i//2+1}
           for i,r in enumerate(records)]
    calls=[]
    monkeypatch.setattr(seasons.leaguestandings,"LeagueStandings",lambda **k: calls.append(k) or SimpleNamespace(get_dict=lambda: nba_payload(raw,"Standings")))
    r=TeamRecordsRequest(season="2023-24",standings_scope="east")
    data=seasons._nba_records(r)
    assert len(seasons._valid_records(data,r)) == 15
    assert calls[0]["season_type"] == "Regular Season"
    raw[0]["SeasonID"]="22024"
    with pytest.raises(ValueError):
        seasons._nba_records(r)


def test_development_fixture_labels_and_candidate_seasons_validate():
    from server.ask.eval.runner import LabeledCase
    path=Path(__file__).parent / "fixtures/eval/stage2-dev.json"
    cases=[LabeledCase.from_json(c) for c in json.loads(path.read_text())["cases"]]
    assert len(cases)==21
    for c in cases:
        if c.action=="accept":
            candidates=CandidateLookupService().lookup(c.question,c.context)
            assert f"season:{c.request.season}" in [v.id for v in candidates.sets["season"].candidates]
