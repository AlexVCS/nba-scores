"""Stage 3 season leaders: qualification modes, ties, sources and the scope guard."""
import copy
import datetime as dt
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import requests

from server.ask.candidates.lookup import CandidateLookupService
from server.ask.models.interpreter import FieldInterpretation, InterpreterMetadata, InterpreterOutput
from server.ask.models.request import AskContext, SeasonLeadersRequest
from server.ask.models.response import AskResponse, SeasonLeadersResult
from server.ask.normalize import Normalizer
from server.ask.present import interpretation
from server.ask.resolvers import leaders, seasons
from server.ask.resolvers.errors import NotFoundError, UnavailableError, UnsupportedError
from server.ask.season_scope import normalize_question
from server.services import basketball_reference

FIXTURES = Path(__file__).parent / "fixtures"
ORIGINAL_BREF_BOARD = leaders._bref_board
PROBE = json.loads((FIXTURES / "season-data/nba-leaders-2023-24.json").read_text())["payloads"]
CONTEXT = AskContext(reference_time=dt.datetime.fromisoformat("2026-09-29T12:00:00-04:00"))


def request(stat="points", aggregation="per_game", **kwargs):
    return SeasonLeadersRequest(season=kwargs.pop("season", "2023-24"), stat={"stat": stat, "aggregation": aggregation}, **kwargs)


def install(monkeypatch, payload):
    calls = []
    def leaders_endpoint(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(get_dict=lambda: copy.deepcopy(payload))
    monkeypatch.setattr(leaders.leagueleaders, "LeagueLeaders", leaders_endpoint)
    return calls


def synthetic(values, *, mode="Totals", category="PTS", season_type="Regular Season", ranks=None, season="2023-24"):
    """A LeagueLeaders payload with current franchises and real player IDs from the probe."""
    base = PROBE["Totals-RegularSeason-PTS-2023-24"]
    headers = base["resultSet"]["headers"]
    template = base["resultSet"]["rowSet"][0]
    rows = []
    for i, value in enumerate(values):
        row = dict(zip(headers, template))
        row.update(PLAYER_ID=1000 + i, PLAYER=f"Player {i}", RANK=ranks[i] if ranks else i + 1, GP=70, **{category: value})
        rows.append([row[h] for h in headers])
    return {"parameters": {"LeagueID": "00", "PerMode": mode, "StatCategory": category, "Season": season,
                           "SeasonType": season_type, "Scope": "S", "ActiveFlag": None},
            "resultSet": {"name": "LeagueLeaders", "headers": headers, "rowSet": rows}}


def competition(values):
    ordered = sorted(values, reverse=True)
    return [ordered.index(v) + 1 for v in ordered], ordered


@pytest.fixture(autouse=True)
def clean_sources(monkeypatch):
    seasons._cache.clear()
    monkeypatch.setattr(basketball_reference, "_next_start", 0)
    monkeypatch.setattr(basketball_reference.requests, "get", lambda *a, **k: (_ for _ in ()).throw(AssertionError("Unexpected network")))
    monkeypatch.setattr(leaders.leagueleaders, "LeagueLeaders", lambda **k: (_ for _ in ()).throw(AssertionError("Unexpected NBA network")))


# -- primary source ---------------------------------------------------------------------------


def test_per_game_board_uses_source_qualification_ranks_and_cache(monkeypatch):
    calls = install(monkeypatch, PROBE["PerGame-RegularSeason-PTS-2023-24"])
    monkeypatch.setattr(leaders, "_bref_board", lambda r: pytest.fail("Fallback on valid NBA data"))
    output = leaders.season_leaders(request())
    result = output.result
    assert [r.player.name for r in result.rows[:2]] == ["Luka Dončić", "Giannis Antetokounmpo"]
    assert result.rows[0].value.display == "33.9" and result.rows[0].games_played == 70
    assert result.qualification == "source_qualified" and "per-game minimum" in result.qualification_note
    assert len(result.rows) == 10 and result.limit == 10 and result.omitted_tie is None
    # Durant and Booker both display 27.1 but are not tied: the source ranks unrounded values.
    assert [(r.rank, r.value.display) for r in result.rows[4:6]] == [(5, "27.1"), (6, "27.1")]
    assert result.rows[0].team.tricode == "DAL" and not result.rows[0].multiple_teams
    assert calls[0] == {**calls[0], "per_mode48": "PerGame", "season": "2023-24", "season_type_all_star": "Regular Season",
                        "stat_category_abbreviation": "PTS", "league_id": "00", "scope": "S", "timeout": 4}
    assert output.sources[0].name == "nba_stats" and output.sources[0].complete
    assert output.links[0].href.startswith("https://www.nba.com/stats/leaders?Season=2023-24")
    # One board serves every top N.
    assert len(leaders.season_leaders(request(limit=3)).result.rows) == 3
    assert len(calls) == 1


def test_totals_ties_share_a_rank_and_are_all_listed(monkeypatch):
    install(monkeypatch, PROBE["Totals-RegularSeason-PTS-2023-24"])
    rows = leaders.season_leaders(request(aggregation="total", limit=22)).result.rows
    assert [r.rank for r in rows[-2:]] == [22, 22] and len(rows) == 23
    assert rows[-1].value.value == rows[-2].value.value
    assert leaders.season_leaders(request(aggregation="total", limit=21)).result.rows[-1].rank == 21
    result = leaders.season_leaders(request(aggregation="total")).result
    assert result.qualification == "all_players" and result.rows[0].value.display == "2370"


def test_tie_group_past_the_row_cap_is_omitted_whole(monkeypatch):
    values = [100, 90, 80, 70] + [50] * 60
    ranks, ordered = competition(values)
    install(monkeypatch, synthetic(ordered, ranks=ranks))
    result = leaders.season_leaders(request(aggregation="total")).result
    assert [r.rank for r in result.rows] == [1, 2, 3, 4]
    assert result.omitted_tie.rank == 5 and result.omitted_tie.count == 60
    seasons._cache.clear()
    install(monkeypatch, synthetic([10] * 60, ranks=[1] * 60))
    with pytest.raises(UnsupportedError):
        leaders.season_leaders(request(aggregation="total"))


@pytest.mark.parametrize("ranks", [[1, 3, 3], [1, 1, 3], [2, 3, 4]])
def test_inconsistent_source_ranks_are_not_answers(monkeypatch, ranks):
    install(monkeypatch, synthetic([30, 20, 20], ranks=ranks, mode="PerGame"))
    with pytest.raises(UnavailableError):
        leaders.season_leaders(request())


@pytest.mark.parametrize("field,value", [("Season", "2022-23"), ("PerMode", "Totals"), ("StatCategory", "REB"),
                                         ("SeasonType", "Playoffs"), ("LeagueID", "10")])
def test_parameter_echo_must_match_and_per_game_has_no_fallback(monkeypatch, field, value):
    payload = synthetic([30, 20], mode="PerGame")
    payload["parameters"][field] = value
    install(monkeypatch, payload)
    monkeypatch.setattr(seasons, "_html", lambda *a: pytest.fail("Per-game boards must not use the fallback"))
    with pytest.raises(UnavailableError):
        leaders.season_leaders(request())


def test_percentages_use_totals_mode_and_keep_made_attempted(monkeypatch):
    calls = install(monkeypatch, PROBE["Totals-RegularSeason-FG_PCT-2023-24"])
    result = leaders.season_leaders(request("field_goal_percentage", "total")).result
    assert calls[0]["per_mode48"] == "Totals" and calls[0]["stat_category_abbreviation"] == "FG_PCT"
    top = result.rows[0]
    assert top.player.name == "Daniel Gafford" and top.value.display == "72.5%"
    assert (top.value.made, top.value.attempted) == (348, 480)
    assert result.qualification == "source_qualified" and "made-shot minimum" in result.qualification_note
    with pytest.raises(ValueError):
        request("field_goal_percentage", "per_game")


def test_playoffs_are_a_separate_board(monkeypatch):
    calls = install(monkeypatch, PROBE["PerGame-Playoffs-PTS-2023-24"])
    result = leaders.season_leaders(request(season_type="playoffs")).result
    assert calls[0]["season_type_all_star"] == "Playoffs" and result.season_type == "playoffs"
    assert result.rows[0].player.name == "Joel Embiid" and result.rows[0].games_played == 6
    install(monkeypatch, PROBE["PerGame-RegularSeason-PTS-2023-24"])
    assert leaders.season_leaders(request()).result.rows[0].player.name == "Luka Dončić"


def test_unrecorded_statistics_skip_both_sources(monkeypatch):
    monkeypatch.setattr(leaders, "_nba_board", lambda r: pytest.fail("no fetch"))
    monkeypatch.setattr(leaders, "_bref_board", lambda r: pytest.fail("no fallback"))
    for stat, season in (("steals", "1970-71"), ("three_pointers", "1978-79"), ("turnovers", "1976-77")):
        with pytest.raises(NotFoundError, match="season_stat_not_recorded"):
            leaders.season_leaders(request(stat, "total", season=season))


def test_title_era_note_for_early_per_game_boards(monkeypatch):
    install(monkeypatch, synthetic([30.1, 25.0], mode="PerGame", season="1960-61"))
    monkeypatch.setattr(leaders, "_nba_team", lambda *a: None)
    result = leaders.season_leaders(request(season="1960-61")).result
    assert result.coverage_note and "1969-70" in result.coverage_note


def test_defunct_franchise_is_blank_but_known_franchise_out_of_era_fails():
    assert leaders._nba_team(1610610024, "1950-51") is None  # outside the current-franchise catalog
    assert leaders._nba_team(1610612743, "2023-24")["tricode"] == "DEN"
    with pytest.raises(ValueError):
        leaders._nba_team(1610612740, "1990-91")  # Pelicans franchise did not exist yet


# -- fallback ---------------------------------------------------------------------------------


def bref_html(rows, heading="2023-24 NBA Player Stats: Totals", table="totals_stats"):
    def tr(name, href, code, games, points):
        team = f'<a href="/teams/{code}/2024.html">{code}</a>' if not code.endswith("TM") and code != "TOT" else code
        return (f'<tr><td data-stat="name_display"><a href="{href}">{name}</a></td>'
                f'<td data-stat="team_name_abbr">{team}</td><td data-stat="games">{games}</td>'
                f'<td data-stat="pts">{points}</td><td data-stat="fg">1</td><td data-stat="fga">2</td></tr>')
    body = "".join(tr(*r) for r in rows)
    return f'<h1>{heading}</h1><!--<table id="{table}"><tbody>{body}<tr class="thead"><td>Player</td></tr></tbody></table>-->'


BREF_ROWS = [
    ("Luka Dončić", "/players/d/doncilu01.html", "DAL", 70, 2370),
    ("Shai Gilgeous-Alexander", "/players/g/gilgesh01.html", "OKC", 75, 2254),
    ("Pascal Siakam", "/players/s/siakapa01.html", "2TM", 80, 2200),
    ("Pascal Siakam", "/players/s/siakapa01.html", "TOR", 39, 850),
    ("Pascal Siakam", "/players/s/siakapa01.html", "IND", 41, 1350),
    ("Jalen Brunson", "/players/b/brunsja01.html", "NYK", 77, 2200),
]


def test_bref_totals_fallback_ranks_exact_totals_with_aggregates(monkeypatch):
    install(monkeypatch, synthetic([30], mode="Totals", ranks=[2]))  # malformed primary
    monkeypatch.setattr(seasons, "_html", lambda *a: bref_html(BREF_ROWS))
    output = leaders.season_leaders(request(aggregation="total"))
    rows = output.result.rows
    assert [(r.rank, r.player.player_id) for r in rows] == [(1, 1629029), (2, 1628983), (3, 1628973), (3, 1627783)]
    siakam = rows[3]
    assert siakam.team is None and siakam.multiple_teams and siakam.value.value == 2200
    assert rows[0].team.tricode == "DAL"
    assert output.sources[0].name == "basketball_reference"
    assert output.links[0].href == "https://www.basketball-reference.com/leagues/NBA_2024_totals.html"


def test_bref_playoff_table_is_separate(monkeypatch):
    install(monkeypatch, {"parameters": {}, "resultSet": {}})
    regular = bref_html(BREF_ROWS[:1])
    playoffs = bref_html([BREF_ROWS[1]], table="totals_stats_post").split("</h1>")[1]
    monkeypatch.setattr(seasons, "_html", lambda *a: regular + playoffs)
    rows = leaders.season_leaders(request(aggregation="total", season_type="playoffs")).result.rows
    assert [r.player.name for r in rows] == ["Shai Gilgeous-Alexander"]
    seasons._cache.clear()
    rows = leaders.season_leaders(request(aggregation="total")).result.rows
    assert [r.player.name for r in rows] == ["Luka Dončić"]


def test_bref_unverifiable_shown_player_is_unavailable(monkeypatch):
    install(monkeypatch, {"parameters": {}, "resultSet": {}})
    monkeypatch.setattr(seasons, "_html", lambda *a: bref_html([("Nobody Real", "/players/n/nobod01.html", "DAL", 70, 3000)] + BREF_ROWS))
    with pytest.raises(UnavailableError):
        leaders.season_leaders(request(aggregation="total"))


def test_bref_stint_rows_without_aggregate_are_unavailable(monkeypatch):
    install(monkeypatch, {"parameters": {}, "resultSet": {}})
    monkeypatch.setattr(seasons, "_html", lambda *a: bref_html([r for r in BREF_ROWS if r[2] != "2TM"]))
    with pytest.raises(UnavailableError):
        leaders.season_leaders(request(aggregation="total"))


def test_empty_primary_and_fallback_is_not_found_but_failures_are_unavailable(monkeypatch):
    empty = synthetic([])
    install(monkeypatch, empty)
    monkeypatch.setattr(leaders, "_bref_board", lambda r: (_ for _ in ()).throw(NotFoundError("no_record", "season_leaders_missing")))
    with pytest.raises(NotFoundError):
        leaders.season_leaders(request(aggregation="total"))
    monkeypatch.setattr(leaders, "_bref_board", lambda r: (_ for _ in ()).throw(requests.HTTPError("403")))
    with pytest.raises(UnavailableError):
        leaders.season_leaders(request(aggregation="total"))
    # Per-game boards: an empty primary never becomes "no record" through a refused fallback.
    seasons._cache.clear()
    install(monkeypatch, synthetic([], mode="PerGame"))
    monkeypatch.setattr(leaders, "_bref_board", ORIGINAL_BREF_BOARD)
    with pytest.raises(UnavailableError):
        leaders.season_leaders(request())


def test_fallback_uses_the_shared_throttled_transport(monkeypatch):
    install(monkeypatch, {"parameters": {}, "resultSet": {}})
    monkeypatch.setattr(basketball_reference.time, "monotonic", lambda: 100)
    monkeypatch.setattr(basketball_reference, "_next_start", 105)
    with pytest.raises(UnavailableError):
        leaders.season_leaders(request(aggregation="total"))


def test_joined_load_is_bounded(monkeypatch):
    from server.utils.ttl_cache import LoadInProgressError
    def joined(*a, **kwargs):
        assert kwargs["wait_timeout"] == 5
        raise LoadInProgressError("leaders")
    monkeypatch.setattr(seasons._cache, "get_or_load", joined)
    with pytest.raises(UnavailableError, match="season_load_in_progress"):
        leaders.season_leaders(request())


def test_result_requires_competition_ranking():
    row = {"player": {"player_id": 1, "name": "A"}, "games_played": 1, "value": {"stat": "points", "value": 1, "display": "1"}}
    base = dict(season="2023-24", season_type="regular_season", stat="points", aggregation="total", limit=10,
                qualification="all_players", qualification_note="x", as_of="2026-09-29T00:00:00Z")
    SeasonLeadersResult(**base, rows=[{**row, "rank": 1}, {**row, "rank": 1, "player": {"player_id": 2, "name": "B"}}])
    with pytest.raises(ValueError):
        SeasonLeadersResult(**base, rows=[{**row, "rank": 1}, {**row, "rank": 3, "player": {"player_id": 2, "name": "B"}}])
    with pytest.raises(ValueError):
        SeasonLeadersResult(**base, rows=[{**row, "rank": 2}])


# -- interpretation, guard and clarification --------------------------------------------------


def interpreted(fields):
    return InterpreterOutput(outcome="interpreted", metadata=InterpreterMetadata(adapter="jev", provider="test", model="test", latency_ms=0),
                             fields=[FieldInterpretation(field=k, status="selected", selected=v if isinstance(v, list) else [v], confidence=1)
                                     for k, v in {"intent": "season_leaders", **fields}.items()])


def guard(question, **fields):
    candidates = CandidateLookupService().lookup(question, CONTEXT)
    seasons_found = candidates.sets["season"].candidates
    if seasons_found and "season" not in fields:
        fields["season"] = seasons_found[0].id
    fields = {k: v for k, v in fields.items() if v is not None}
    return normalize_question(Normalizer(), interpreted(fields), candidates, CONTEXT, question)


def test_leaders_normalize_with_real_lookup_and_readout():
    q = "Who led the league in assists per game in 2019-20?"
    n = guard(q, stat="assists", aggregation="per_game")
    assert n.status == "valid" and n.request.limit == 10 and n.request.season == "2019-20"
    candidates = CandidateLookupService().lookup(q, CONTEXT)
    readout = interpretation(interpreted({"season": "season:2019-20", "stat": "assists", "aggregation": "per_game"}), candidates, CONTEXT, n.request)
    assert readout.detected_type == "season_leaders" and readout.season == "2019-20"
    assert any(i.field == "aggregation" and i.value == "Per Game" for i in readout.items)


def test_counting_stat_without_measure_is_clarified_but_percentages_are_not():
    n = guard("Who led the league in points in 2022-23?", stat="points")
    assert n.status == "needs_clarification" and n.clarify_field == "aggregation"
    n = guard("Who led the league in free throw percentage in 2022-23?", stat="free_throw_percentage", aggregation="per_game")
    assert n.status == "valid" and n.request.stat.aggregation == "total"


def test_missing_or_unrankable_statistic():
    assert guard("Who led the league in 2022-23?", stat="stat_line").clarify_field == "stat"
    assert guard("Who led the league in 2022-23?").clarify_field == "stat"
    n = guard("Who led the league in plus minus in 2022-23?", stat="plus_minus", aggregation="total")
    assert n.status == "unsupported"
    n = Normalizer().normalize(interpreted({"season": "season:2022-23", "stat": "fouls", "aggregation": "total"}),
                               CandidateLookupService().lookup("Who committed the most fouls in 2022-23", CONTEXT), CONTEXT)
    assert n.status == "unsupported" and n.unsupported_reason == "unsupported_leader_stat"


@pytest.mark.parametrize("question,limit", [
    ("Top 5 in total rebounds in 2023-24", 5), ("top ten scorers in total points in 2022-23", 10),
    ("Top twenty-five in total assists in 2022-23", 25), ("top 3-point makers in total in 2022-23", 10),
    ("Top 1 in total steals in 2022-23", 1),
])
def test_top_n_is_read_from_text(question, limit):
    stat = "three_pointers" if "3-point" in question else "rebounds" if "rebounds" in question else "assists" if "assists" in question else "steals" if "steals" in question else "points"
    n = guard(question, stat=stat, aggregation="total")
    assert n.status == "valid" and n.request.limit == limit


@pytest.mark.parametrize("question", [
    "Top 30 in total rebounds in 2023-24", "Top 0 scorers in total points in 2023-24",
    "Who led the Lakers in points per game in 2023-24?", "Did Nikola Jokic lead the league in rebounds per game in 2023-24?",
    "Who led the league in points and assists per game in 2023-24?", "Who led the league in points per game in 2022-23 and 2023-24?",
    "Which team scored the most points in 2023-24?", "Who led the Western conference in assists per game in 2023-24?",
    "Rookie leaders in points per game in 2023-24", "Who had the fewest turnovers per game in 2023-24?",
    "Who scored the most points in a game in 2023-24?", "Who led the league in points per game at home in 2023-24?",
    "Who led the league in points per game in March 2024?", "All-time leaders in points per game in 2023-24",
    "Who led the league in PER in 2023-24?", "Who led the league in points per 36 in 2023-24?",
    "Who had the most 40 point games in 2023-24?", "Who averaged at least 30 points per game in 2023-24?",
    "Who led the league in points including playoffs in 2023-24?", "Who led the league in double-doubles in 2023-24?",
    "Who led the league in points per game since 2019-20?", "Best career scoring average in 2023-24",
])
def test_out_of_scope_leader_questions_are_never_answered(question):
    assert guard(question, stat="points", aggregation="per_game").status == "unsupported"


def test_playoff_wording_requires_playoffs_and_bare_year_requires_season():
    q = "Who led the 2024 playoffs in points per game?"
    n = guard(q, stat="points", aggregation="per_game")
    assert n.status == "needs_clarification" and n.clarify_field == "season_type"
    n = guard(q, stat="points", aggregation="per_game", season_type="playoffs")
    assert n.status == "valid" and n.request.season == "2023-24" and n.request.season_type == "playoffs"
    n = guard("Who led the NBA in points per game in 2008", stat="points", aggregation="per_game")
    assert n.status == "needs_clarification" and n.clarify_field == "season"


def test_measure_choice_round_trips_and_keeps_top_n(tmp_path):
    from server.ask.present import clarification
    from server.ask.resolution import PendingResolution, ResolutionStore
    q = "Top 5 in points in 2022-23"
    candidates = CandidateLookupService().lookup(q, CONTEXT)
    output = interpreted({"season": "season:2022-23", "stat": "points"})
    assert normalize_question(Normalizer(), output, candidates, CONTEXT, q).clarify_field == "aggregation"
    store = ResolutionStore(tmp_path / "leaders.sqlite3")
    options = clarification("aggregation", "ambiguous", q, PendingResolution(output, candidates, CONTEXT), store).options
    assert [o.label for o in options] == ["Season totals", "Per game"]
    for option, value in zip(options, ["total", "per_game"]):
        chosen = store.read(option.resolution, option.question, CONTEXT)
        n = normalize_question(Normalizer(), chosen.output, chosen.candidates, CONTEXT, option.question)
        assert n.status == "valid" and n.request.stat.aggregation == value and n.request.limit == 5


def test_cascade_can_clarify_leader_measure():
    from server.ask.interpreters.cascade import _clarify
    assert _clarify("aggregation", "ambiguous", "x", interpreted({"stat": "points"})).field == "aggregation"


def test_development_cases_validate_and_accept_labels_survive_the_guard():
    from server.ask.eval.runner import LabeledCase, scored_request
    cases = [LabeledCase.from_json(c) for c in json.loads((FIXTURES / "eval/stage3-dev.json").read_text())["cases"]]
    assert len(cases) >= 20 and len({c.id for c in cases}) == len(cases)
    for case in cases:
        if case.action != "accept":
            continue
        r = case.request
        n = guard(case.question, season=f"season:{r.season}", stat=r.stat.stat, aggregation=r.stat.aggregation,
                  season_type=r.season_type)
        assert n.status == "valid", case.id
        assert scored_request(n.request) == scored_request(r), case.id


def test_answer_fixture_round_trips_the_contract():
    path = Path(__file__).resolve().parents[3] / "src/services/ask/fixtures/responses/answer-season-leaders.json"
    response = AskResponse.model_validate_json(path.read_text())
    assert response.result.kind == "season_leaders" and response.interpretation.intent == "season_leaders"


@pytest.mark.parametrize("question,stat", [
    ("Best 3-point shooting percentage in 2022-23", "three_point_percentage"),
    ("Who led the league in free throw shooting percentage in 2022-23?", "free_throw_percentage"),
    ("Top 5 in three-point field goals made in 2022-23", "three_pointers"),
    ("Who led the league in offensive rebounds per game in 2022-23?", "offensive_rebounds"),
])
def test_one_statistic_in_several_words_is_not_a_multi_stat_question(question, stat):
    aggregation = "per_game" if "per game" in question else "total"
    assert guard(question, stat=stat, aggregation=aggregation).status == "valid"
