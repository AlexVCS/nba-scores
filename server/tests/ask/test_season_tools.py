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


@pytest.mark.parametrize('question', [
    'Jokic points in the 2024 Finals', 'Jokic points in round 1 of the 2024 playoffs',
    'Jokic points in game 7 of the 2024 playoffs', 'Jokic points in wins in 2023-24',
    'Jokic points per 48 in 2023-24', 'Jokic points per minute in 2023-24',
    'Jokic clutch points in 2023-24', 'Jokic fourth quarter points in 2023-24',
    'Jokic first half points in 2023-24', 'Jokic overtime points in 2023-24',
    'Jokic points as a starter in 2023-24', 'Jokic bench points in 2023-24',
    'Jokic points on back-to-back games in 2023-24', 'Jokic points in his last five games in 2023-24',
    'Jokic and LeBron James points in 2023-24', 'Lakers record with LeBron James in 2023-24',
    'Lakers record without LeBron James in 2023-24', 'Celtics conference record in 2023-24',
    'Lakers record when LeBron James plays in 2023-24',
])
def test_review_scope_constraints_cannot_be_discarded(question):
    from server.ask.season_scope import normalize_question
    c = CandidateLookupService().lookup(question, CONTEXT)
    intent = 'team_records' if 'record' in question else 'player_season_stats'
    fields = {'season': c.sets['season'].candidates[0].id}
    if intent == 'player_season_stats':
        fields.update(player='player:203999', stat='points')
    assert normalize_question(Normalizer(), interpreted(intent, fields), c, CONTEXT, question).status == 'unsupported'


def test_playoff_language_requires_playoff_selection():
    from server.ask.season_scope import normalize_question
    q = 'Jokic points in the 2024 playoffs'
    c = CandidateLookupService().lookup(q, CONTEXT)
    fields = {'player':'player:203999', 'season':'season:2023-24', 'stat':'points'}
    n = normalize_question(Normalizer(), interpreted('player_season_stats', fields), c, CONTEXT, q)
    assert n.status == 'needs_clarification' and n.clarify_field == 'season_type'
    fields['season_type']='playoffs'
    assert normalize_question(Normalizer(), interpreted('player_season_stats', fields), c, CONTEXT, q).status == 'valid'
    assert normalize_question(Normalizer(), interpreted('team_records', {'season':'season:2023-24'}), c, CONTEXT, q).status == 'unsupported'


def test_curry_name_candidates_remain_clarifiable():
    from server.ask.season_scope import normalize_question
    q='Curry points in 2023-24'
    c=CandidateLookupService().lookup(q, CONTEXT)
    o=interpreted('player_season_stats', {'season':'season:2023-24','stat':'points'})
    o=o.model_copy(update={'fields':o.fields+[FieldInterpretation(field='player',status='ambiguous',alternatives=[p.id for p in c.sets['player'].candidates][:4],confidence=1)]})
    n=normalize_question(Normalizer(),o,c,CONTEXT,q)
    assert n.status == 'needs_clarification' and n.clarify_field == 'player'


@pytest.mark.parametrize('field, choices', [('aggregation', ['total','per_game']), ('season_type',['regular_season','playoffs'])])
def test_closed_choices_round_trip_tokens_and_scope_guard(tmp_path,field,choices):
    from server.ask.present import clarification
    from server.ask.resolution import PendingResolution, ResolutionStore
    from server.ask.season_scope import normalize_question
    q='Jokic points in 2023-24 playoffs' if field == 'season_type' else 'Jokic points total or per game in 2023-24'
    c=CandidateLookupService().lookup(q,CONTEXT)
    o=interpreted('player_season_stats',{'player':'player:203999','season':'season:2023-24','stat':'points'})
    o=o.model_copy(update={'fields':o.fields+[FieldInterpretation(field=field,status='ambiguous',alternatives=choices,confidence=1)]})
    pending=PendingResolution(o,c,CONTEXT);store=ResolutionStore(tmp_path/'choices.sqlite3')
    options=clarification(field,'ambiguous',q,pending,store).options
    assert len(options)==2
    for option,value in zip(options,choices):
        chosen=store.read(option.resolution,option.question,CONTEXT)
        assert chosen is not None
        n=normalize_question(Normalizer(),chosen.output,chosen.candidates,chosen.context,option.question)
        assert n.status=='valid'
        assert (n.request.stat.aggregation if field=='aggregation' else n.request.season_type)==value


@pytest.mark.parametrize('phase,games,points', [('regular_season',79,2085),('playoffs',12,344)])
def test_current_live_bref_markup_both_phases(monkeypatch,phase,games,points):
    html=(Path(__file__).parent/'fixtures/season-data/bref-jokic-2024.html').read_text()
    monkeypatch.setattr(seasons,'_html',lambda *a:html)
    r=request('points',season_type=phase,team=DEN)
    data=seasons._bref_player(r)
    gp,values=seasons._valid_player(data,r)
    assert gp==games and values[0].value==pytest.approx(points/games)
    assert data.href.endswith('NBA_2024_totals.html')


@pytest.mark.parametrize('attempts,made,pct', [(0,0,0),(None,0,0),(5,6,.8)])
def test_percentage_requires_valid_positive_attempts(attempts,made,pct):
    assert seasons._value(row(FGA=attempts,FGM=made,FG_PCT=pct),'field_goal_percentage',79,'total').value is None


def test_historical_unrecorded_stat_skips_fallback(monkeypatch):
    monkeypatch.setattr(seasons,'_nba_player',lambda *a:pytest.fail('Unrecorded stat must not fetch'))
    monkeypatch.setattr(seasons,'_bref_player',lambda *a:pytest.fail('Unrecorded stat must not consume fallback'))
    r=request('steals').model_copy(update={'season':'1960-61'})
    with pytest.raises(NotFoundError,match='season_stat_not_recorded'):
        seasons.player_season(r)
    _,values=seasons._valid_player(source_data([row(STL=0,BLK=0,FG3M=0,FG3A=0)]),request('stat_line').model_copy(update={'season':'1960-61'}))
    assert next(v for v in values if v.stat=='steals').value is None


def test_league_standings_sort_by_percentage_across_conferences():
    rows=team_rows()
    rows[0].update(wins=20,losses=62,win_percentage=20/82,conference_rank=1)
    rows[1].update(wins=70,losses=12,win_percentage=70/82,conference_rank=2)
    result=seasons._valid_records(source_data(rows),TeamRecordsRequest(season='2023-24'))
    assert result[0].team.team_id == rows[1]['team']['team_id']
    assert [r.win_percentage for r in result]==sorted((r.win_percentage for r in result),reverse=True)


def test_late_2020_playoffs_not_complete_in_october(monkeypatch):
    monkeypatch.setattr(seasons,'_now',lambda:dt.datetime(2020,10,15,tzinfo=dt.timezone.utc))
    assert not seasons._complete('2019-20')


def test_joined_cache_load_has_timeout_and_maps_to_unavailable(monkeypatch):
    from server.utils.ttl_cache import LoadInProgressError
    def joined(*a,**kwargs):
        assert kwargs['wait_timeout']==5
        raise LoadInProgressError('player')
    monkeypatch.setattr(seasons._cache,'get_or_load',joined)
    with pytest.raises(UnavailableError,match='season_load_in_progress'):
        seasons.player_season(request())


def test_development_accept_labels_survive_question_guard():
    from server.ask.eval.runner import LabeledCase, scored_request
    from server.ask.season_scope import normalize_question
    cases=[LabeledCase.from_json(c) for c in json.loads((Path(__file__).parent/'fixtures/eval/stage2-dev.json').read_text())['cases']]
    for case in cases:
        if case.action!='accept':continue
        r=case.request;c=CandidateLookupService().lookup(case.question,case.context)
        fields={'season':f'season:{r.season}'}
        if r.intent=='player_season_stats':
            fields.update(player=f'player:{r.player.player_id}',stat=r.stat.stat,aggregation=r.stat.aggregation,season_type=r.season_type)
        else: fields['standings_scope']=r.standings_scope
        if r.team: fields['teams']=[f'team:{r.team.team_id}']
        n=normalize_question(Normalizer(),interpreted(r.intent,fields),c,case.context,case.question)
        assert n.status=='valid',case.id
        assert scored_request(n.request)==scored_request(r),case.id


@pytest.mark.parametrize('team_id,tricode,bref_code', [(1610612756,'PHX','PHO'),(1610612751,'BKN','BRK'),(1610612766,'CHA','CHO')])
def test_bref_team_stint_provider_codes(monkeypatch,team_id,tricode,bref_code):
    html=(Path(__file__).parent/'fixtures/season-data/bref-jokic-2024.html').read_text().replace('/teams/DEN/2024.html',f'/teams/{bref_code}/2024.html').replace('>DEN</a>',f'>{bref_code}</a>')
    monkeypatch.setattr(seasons,'_html',lambda *a:html)
    data=seasons._bref_player(request(team=seasons._team(team_id,'2023-24')))
    assert data.rows[0]['GP']=='79'


def test_invalid_source_link_cannot_poison_completed_cache(monkeypatch):
    install_nba(monkeypatch,[row()])
    bad=source_data([row()]);bad=seasons.SeasonData(bad.rows,bad.source,'https://evil.test/fake',bad.fetched_at,bad.complete)
    monkeypatch.setattr(seasons,'_nba_player',lambda r:bad)
    monkeypatch.setattr(seasons,'_bref_player',lambda r:source_data([row(REB=158)]))
    assert seasons.player_season(request()).result.values[0].value==2


def test_continuation_rewritten_names_do_not_hide_trailing_split():
    from server.ask.season_scope import normalize_question
    c=CandidateLookupService().lookup('Curry rebounds 2023-24',CONTEXT)
    q='Stephen Curry rebounds at home in 2023-24'
    o=interpreted('player_season_stats',{'player':'player:201939','season':'season:2023-24','stat':'rebounds'})
    assert normalize_question(Normalizer(),o,c,CONTEXT,q).status=='unsupported'


def test_confident_bare_year_guess_requires_season_choice(tmp_path):
    from server.ask.present import clarification
    from server.ask.resolution import PendingResolution, ResolutionStore
    from server.ask.season_scope import normalize_question
    q='Celtics record in 2008';c=CandidateLookupService().lookup(q,CONTEXT)
    o=interpreted('team_records',{'teams':'team:1610612738','season':'season:2007-08'})
    n=normalize_question(Normalizer(),o,c,CONTEXT,q)
    assert n.status=='needs_clarification' and n.clarify_field=='season'
    store=ResolutionStore(tmp_path/'year.sqlite3');pending=PendingResolution(o,c,CONTEXT)
    options=clarification('season','ambiguous',q,pending,store).options
    assert len(options)==2
    for option in options:
        chosen=store.read(option.resolution,option.question,CONTEXT)
        n=normalize_question(Normalizer(),chosen.output,chosen.candidates,CONTEXT,option.question)
        assert n.status=='valid' and f'season:{n.request.season}'==option.id


@pytest.mark.parametrize('wording', ['including playoffs','regular season and playoffs','regular-season plus playoffs','playoffs included','combined postseason',
                                    'season and playoffs','regular and postseason','season & playoffs','regular + the postseason'])
@pytest.mark.parametrize('phase', ['regular_season','playoffs'])
def test_combined_regular_and_postseason_stats_are_unsupported(wording,phase):
    from server.ask.season_scope import normalize_question
    q=f'Jokic total points in 2023-24 {wording}';c=CandidateLookupService().lookup(q,CONTEXT)
    o=interpreted('player_season_stats',{'player':'player:203999','season':'season:2023-24','stat':'points','season_type':phase})
    assert normalize_question(Normalizer(),o,c,CONTEXT,q).status=='unsupported'


def test_standings_scope_choices_round_trip(tmp_path):
    from server.ask.present import clarification
    from server.ask.resolution import PendingResolution, ResolutionStore
    from server.ask.season_scope import normalize_question
    q='2023-24 NBA standings';c=CandidateLookupService().lookup(q,CONTEXT)
    o=interpreted('team_records',{'season':'season:2023-24'})
    o=o.model_copy(update={'fields':o.fields+[FieldInterpretation(field='standings_scope',status='ambiguous',alternatives=['league','east','west'],confidence=1)]})
    n=normalize_question(Normalizer(),o,c,CONTEXT,q)
    assert n.status=='needs_clarification' and n.clarify_field=='standings_scope'
    store=ResolutionStore(tmp_path/'scope.sqlite3')
    options=clarification('standings_scope','ambiguous',q,PendingResolution(o,c,CONTEXT),store).options
    assert [v.label for v in options]==['NBA league','Eastern conference','Western conference']
    for option,value in zip(options,['league','east','west']):
        chosen=store.read(option.resolution,option.question,CONTEXT)
        n=normalize_question(Normalizer(),chosen.output,chosen.candidates,CONTEXT,option.question)
        assert n.status=='valid' and n.request.standings_scope==value


def test_measure_choice_expands_abbreviations_and_does_not_offer_boxscore_rates(tmp_path):
    from server.ask.present import clarification
    from server.ask.resolution import PendingResolution, ResolutionStore
    q='Jokic ppg in 2023-24';c=CandidateLookupService().lookup(q,CONTEXT)
    o=interpreted('player_season_stats',{'player':'player:203999','season':'season:2023-24','stat':'points'})
    store=ResolutionStore(tmp_path/'measure.sqlite3')
    options=clarification('aggregation','ambiguous',q,PendingResolution(o,c,CONTEXT),store).options
    assert 'points' in options[0].question and 'ppg' not in options[0].question and 'per game' not in options[0].question
    old=interpreted('boxscore_stat',{'player':'player:203999','stat':'points'})
    assert clarification('aggregation','ambiguous',q,PendingResolution(old,c,CONTEXT),store).options==[]


def test_charlotte_bobcats_stint_keeps_legacy_bref_code(monkeypatch):
    player={'player_id':2744,'name':'Al Jefferson'}
    q=PlayerSeasonStatsRequest(player=player,season='2013-14',team=seasons._team(1610612766,'2013-14'),stat={'stat':'points','aggregation':'total'})
    html='<h1>2013-14 NBA Player Stats: Totals</h1><table id="totals_stats"><tbody><tr><td data-stat="name_display"><a href="/players/j/jeffeal01.html">Al Jefferson</a></td><td data-stat="team_name_abbr"><a href="/teams/CHA/2014.html">CHA</a></td><td data-stat="games">73</td><td data-stat="pts">1594</td></tr></tbody></table>'
    monkeypatch.setattr(seasons,'_html',lambda *a:html)
    data=seasons._bref_player(q)
    assert data.rows[0]['PTS']=='1594' and q.team.name=='Charlotte Bobcats'


def test_all_around_wording_is_supported_and_untracked_rebounds_missing():
    from server.ask.season_scope import normalize_question
    q='Jokic all-around stats in 2023-24';c=CandidateLookupService().lookup(q,CONTEXT)
    o=interpreted('player_season_stats',{'player':'player:203999','season':'season:2023-24','stat':'stat_line'})
    assert normalize_question(Normalizer(),o,c,CONTEXT,q).status=='valid'
    _,values=seasons._valid_player(source_data([row(REB=0)]),request('stat_line').model_copy(update={'season':'1949-50'}))
    assert next(v for v in values if v.stat=='rebounds').value is None


def test_answer_layer_waiter_is_bounded_and_returns_service_notice(tmp_path,monkeypatch):
    from server.ask.models.response import InterpreterInfo
    from server.utils.ttl_cache import LoadInProgressError
    from server.tests.ask.test_pipeline import pipeline,output
    from server.ask.eval import builders as b
    coordinator,_,_=pipeline(tmp_path,b.lookup_result([]),output())
    def joined(*args,**kwargs):
        assert args[0]=='answer' and kwargs['wait_timeout']==5
        raise LoadInProgressError('same-answer')
    monkeypatch.setattr(coordinator.cache,'get_or_load',joined)
    readout=interpretation(None,None,CONTEXT,request())
    response=coordinator._execute('Jokic rebounds 2023-24',request(),readout,InterpreterInfo(model_called=False))
    assert response.outcome=='unavailable' and response.notice.code=='service_unavailable'


@pytest.mark.parametrize('abbreviation,stat', [('spg','steals'),('bpg','blocks'),('mpg','minutes')])
def test_more_per_game_abbreviations_survive_total_choice(tmp_path,abbreviation,stat):
    from server.ask.present import clarification
    from server.ask.resolution import PendingResolution, ResolutionStore
    q=f'Jokic {abbreviation} in 2023-24';c=CandidateLookupService().lookup(q,CONTEXT)
    o=interpreted('player_season_stats',{'player':'player:203999','season':'season:2023-24','stat':stat})
    options=clarification('aggregation','ambiguous',q,PendingResolution(o,c,CONTEXT),ResolutionStore(tmp_path/'copy.sqlite3')).options
    assert stat in options[0].question and abbreviation not in options[0].question and 'per game' not in options[0].question
