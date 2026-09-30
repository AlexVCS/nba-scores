"""Stage 3 career stats: player career lines, all-time totals lists and ranks (ADR 0013)."""
import copy
import datetime as dt
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from server.ask.candidates.lookup import CandidateLookupService
from server.ask.models.interpreter import FieldInterpretation, InterpreterMetadata, InterpreterOutput
from server.ask.models.request import AskContext, CareerStatsRequest
from server.ask.models.response import AskResponse, CareerStatsResult
from server.ask.normalize import Normalizer
from server.ask.resolvers import career, leaders, seasons
from server.ask.resolvers.errors import NotFoundError, UnavailableError, UnsupportedError
from server.ask.season_scope import normalize_question

FIXTURES = Path(__file__).parent / "fixtures"
PROBE = json.loads((FIXTURES / "season-data/nba-career-probe.json").read_text())["payloads"]
CONTEXT = AskContext(reference_time=dt.datetime.fromisoformat("2026-09-29T12:00:00-04:00"))
LEBRON = {"player_id": 2544, "name": "LeBron James"}
CURRY = {"player_id": 201939, "name": "Stephen Curry"}


def request(view="player_totals", stat="points", aggregation="total", player=LEBRON, **kwargs):
    return CareerStatsRequest(view=view, player=player if view != "leaders" else None,
                              stat={"stat": stat, "aggregation": aggregation}, **kwargs)


def career_payload(**updates):
    payload = copy.deepcopy(PROBE["career-2544"])
    for table in payload["resultSets"]:
        headers = table["headers"]
        for row in table["rowSet"]:
            for key, value in updates.items():
                row[headers.index(key)] = value
    return payload


def install_career(monkeypatch, payload):
    calls = []
    monkeypatch.setattr(career.playercareerstats, "PlayerCareerStats",
                        lambda **k: calls.append(k) or SimpleNamespace(get_dict=lambda: copy.deepcopy(payload)))
    return calls


def board_payload(overrides=None, top_x="250", phase="Regular Season"):
    """Every counting category the tool validates; real probe rows where captured."""
    source = PROBE["atl-Totals-RegularSeason-50"]
    captured = {s["name"]: s for s in source["resultSets"]}
    points = captured["PTSLeaders"]["rowSet"]
    sets = []
    for stat in sorted(career.CATEGORIES):
        category = career.CATEGORIES[stat]
        if stat.endswith("percentage") or stat == "minutes":
            continue
        name = f"{category}Leaders"
        headers = ["PLAYER_ID", "PLAYER_NAME", category, f"{category}_RANK", "IS_ACTIVE_FLAG"]
        rows = captured[name]["rowSet"] if name in captured else [list(r) for r in points]
        sets.append({"name": name, "headers": headers, "rowSet": copy.deepcopy((overrides or {}).get(category, rows))})
    return {"parameters": {"LeagueID": "00", "SeasonType": phase, "PerMode": "Totals", "TopX": top_x},
            "resultSets": sets}


def install_board(monkeypatch, payload):
    calls = []
    monkeypatch.setattr(career.alltimeleadersgrids, "AllTimeLeadersGrids",
                        lambda **k: calls.append(k) or SimpleNamespace(get_dict=lambda: copy.deepcopy(payload)))
    return calls


@pytest.fixture(autouse=True)
def clean_sources(monkeypatch):
    seasons._cache.clear()
    monkeypatch.setattr(career.playercareerstats, "PlayerCareerStats", lambda **k: pytest.fail("Unexpected NBA network"))
    monkeypatch.setattr(career.alltimeleadersgrids, "AllTimeLeadersGrids", lambda **k: pytest.fail("Unexpected NBA network"))


# -- player career line -----------------------------------------------------------------------


def test_player_career_totals_and_average_from_exact_totals(monkeypatch):
    calls = install_career(monkeypatch, PROBE["career-2544"])
    output = career.career_stats(request())
    result = output.result
    assert result.view == "player_totals" and result.games_played == 1622
    assert result.values[0].value == 43440 and result.values[0].display == "43440"
    assert calls[0]["per_mode36"] == "Totals" and calls[0]["timeout"] == 4
    average = career.career_stats(request(aggregation="per_game")).result.values[0]
    assert average.value == pytest.approx(43440 / 1622) and average.display == "26.8"
    assert len(calls) == 1  # one cached career row serves both measures
    assert output.links[0].href == "https://www.nba.com/stats/player/2544/career"
    assert output.sources[0].name == "nba_stats" and not output.sources[0].complete  # active player


def test_playoff_career_is_separate_and_full_line_has_every_stat(monkeypatch):
    install_career(monkeypatch, PROBE["career-2544"])
    playoffs = career.career_stats(request(season_type="playoffs")).result
    assert playoffs.games_played == 302 and playoffs.values[0].value == 8521
    line = career.career_stats(request(stat="stat_line")).result
    assert [v.stat for v in line.values] == list(seasons.LINE) and line.coverage_note is None
    pct = career.career_stats(request(stat="field_goal_percentage")).result.values[0]
    assert pct.display == "50.7%"


def test_identity_mismatch_is_unavailable_and_missing_playoffs_not_found(monkeypatch):
    install_career(monkeypatch, career_payload(PLAYER_ID=893))
    with pytest.raises(UnavailableError):
        career.career_stats(request())
    seasons._cache.clear()
    payload = copy.deepcopy(PROBE["career-2544"])
    payload["resultSets"][1]["rowSet"] = []
    install_career(monkeypatch, payload)
    with pytest.raises(NotFoundError):
        career.career_stats(request(season_type="playoffs"))


def test_statistic_recorded_mid_career_keeps_total_but_not_average(monkeypatch):
    kareem = {"player_id": 76003, "name": "Kareem Abdul-Jabbar"}
    install_career(monkeypatch, career_payload(PLAYER_ID=76003, STL=1160, GP=1560))
    total = career.career_stats(request(stat="steals", player=kareem)).result
    assert total.values[0].value == 1160 and "1973-74" in total.coverage_note
    average = career.career_stats(request(stat="steals", aggregation="per_game", player=kareem)).result
    assert average.values[0].value is None and average.values[0].display == "Unavailable"


def test_statistic_recorded_after_career_is_never_a_zero(monkeypatch):
    wilt = {"player_id": 76375, "name": "Wilt Chamberlain"}
    install_career(monkeypatch, career_payload(PLAYER_ID=76375, STL=0, BLK=0))
    with pytest.raises(NotFoundError, match="career_stat_missing"):
        career.career_stats(request(stat="steals", player=wilt))
    line = career.career_stats(request(stat="stat_line", player=wilt)).result
    assert next(v for v in line.values if v.stat == "steals").display == "Unavailable"


# -- all-time lists ---------------------------------------------------------------------------


def test_all_time_leaders_list_totals_and_share_one_fetch(monkeypatch):
    calls = install_board(monkeypatch, board_payload())
    output = career.career_stats(request("leaders", limit=3))
    result = output.result
    assert [r.player.name for r in result.rows] == ["LeBron James", "Kareem Abdul-Jabbar", "Karl Malone"]
    assert result.rows[0].active and not result.rows[1].active and result.rows[0].value.display == "43,440"
    assert calls[0] == {**calls[0], "per_mode_simple": "Totals", "season_type": "Regular Season", "topx": 250, "timeout": 4}
    threes = career.career_stats(request("leaders", stat="three_pointers")).result
    assert threes.rows[0].player.name == "Stephen Curry" and "1979-80" in threes.coverage_note
    assert len(calls) == 1
    assert output.links[0].href.startswith("https://www.nba.com/stats/alltime-leaders")


def test_player_rank_in_and_outside_the_list(monkeypatch):
    install_board(monkeypatch, board_payload())
    ranked = career.career_stats(request("player_rank", stat="three_pointers", player=CURRY)).result
    assert ranked.rank == 1 and ranked.values[0].value == 4248 and ranked.list_size == 250 and ranked.tied_count is None
    outside = career.career_stats(request("player_rank", player={"player_id": 1, "name": "Someone"})).result
    assert outside.rank is None and outside.values == [] and outside.list_size == 250


def test_tied_ranks_are_listed_and_counted(monkeypatch):
    rows = [[2544, "LeBron James", 100, 1, "Y"], [201939, "Stephen Curry", 90, 2, "Y"], [893, "Michael Jordan", 90, 2, "N"],
            [977, "Kobe Bryant", 80, 4, "N"]]
    install_board(monkeypatch, board_payload({"STL": rows}))
    listed = career.career_stats(request("leaders", stat="steals", limit=2)).result
    assert [r.rank for r in listed.rows] == [1, 2, 2]
    rank = career.career_stats(request("player_rank", stat="steals", player=CURRY)).result
    assert rank.rank == 2 and rank.tied_count == 2


def test_tie_group_past_the_cap_is_omitted(monkeypatch):
    rows = [[2544, "LeBron James", 100, 1, "Y"]] + [[10 + i, f"P {i}", 50, 2, "N"] for i in range(60)]
    install_board(monkeypatch, board_payload({"BLK": rows}))
    result = career.career_stats(request("leaders", stat="blocks")).result
    assert len(result.rows) == 1 and result.omitted_tie.rank == 2 and result.omitted_tie.count == 60


@pytest.mark.parametrize("bad", ["top_x", "phase", "rank", "value", "flag"])
def test_malformed_all_time_data_is_unavailable_and_not_cached(monkeypatch, bad):
    payload = board_payload(top_x="10" if bad == "top_x" else "250", phase="Playoffs" if bad == "phase" else "Regular Season")
    table = next(s for s in payload["resultSets"] if s["name"] == "PTSLeaders")
    if bad == "rank":
        table["rowSet"][1][3] = 3
    elif bad == "value":
        table["rowSet"][1][2] = 99999
    elif bad == "flag":
        table["rowSet"][0][4] = None
    install_board(monkeypatch, payload)
    with pytest.raises(UnavailableError):
        career.career_stats(request("leaders"))
    calls = install_board(monkeypatch, board_payload())
    assert career.career_stats(request("leaders")).result.rows[0].player.name == "LeBron James"
    assert len(calls) == 1


def test_joined_load_is_bounded(monkeypatch):
    from server.utils.ttl_cache import LoadInProgressError
    def joined(*a, **kwargs):
        assert kwargs["wait_timeout"] == 5
        raise LoadInProgressError("career")
    monkeypatch.setattr(seasons._cache, "get_or_load", joined)
    with pytest.raises(UnavailableError):
        career.career_stats(request())


def test_request_and_result_shapes():
    with pytest.raises(ValueError):
        request("leaders", aggregation="per_game")
    with pytest.raises(ValueError):
        request("player_rank", stat="field_goal_percentage")
    with pytest.raises(ValueError):
        CareerStatsRequest(view="leaders", player=LEBRON, stat={"stat": "points"})
    with pytest.raises(ValueError):
        CareerStatsResult(view="player_rank", season_type="regular_season", stat="points", aggregation="total",
                          player=LEBRON, rank=3, list_size=250, as_of="2026-09-29T00:00:00Z")
    with pytest.raises(UnsupportedError):
        leaders.cut_ties([SimpleNamespace(rank=1)] * 60, 10)


# -- interpretation and guard -----------------------------------------------------------------


def interpreted(fields):
    return InterpreterOutput(outcome="interpreted", metadata=InterpreterMetadata(adapter="jev", provider="test", model="test", latency_ms=0),
                             fields=[FieldInterpretation(field=k, status="selected", selected=v if isinstance(v, list) else [v], confidence=1)
                                     for k, v in {"intent": "career_stats", **fields}.items()])


def guard(question, **fields):
    candidates = CandidateLookupService().lookup(question, CONTEXT)
    players = [c for c in candidates.sets["player"].candidates if c.source != "app_context"]
    if players and "player" not in fields and len({c.value.player.player_id for c in players}) == 1:
        fields["player"] = players[0].id
    fields = {k: v for k, v in fields.items() if v is not None}
    return normalize_question(Normalizer(), interpreted(fields), candidates, CONTEXT, question)


@pytest.mark.parametrize("question,fields,view,limit", [
    ("LeBron James career points", {"stat": "points"}, "player_totals", 10),
    ("LeBron James career points per game", {"stat": "points", "aggregation": "per_game"}, "player_totals", 10),
    ("LeBron James career stats", {}, "player_totals", 10),
    ("Who has the most career assists?", {"stat": "assists"}, "leaders", 10),
    ("Top 5 all-time in total blocks", {"stat": "blocks"}, "leaders", 5),
    ("Where does Stephen Curry rank all-time in 3-pointers made?", {"stat": "three_pointers"}, "player_rank", 10),
    ("Is LeBron James the all-time leading scorer?", {"stat": "points"}, "player_rank", 10),
])
def test_views_are_chosen_by_python(question, fields, view, limit):
    n = guard(question, **fields)
    assert n.status == "valid", n
    assert n.request.view == view and n.request.limit == limit
    if not fields:
        assert n.request.stat.stat == "stat_line"


@pytest.mark.parametrize("question,fields,status,clarify", [
    ("How many points does LeBron James have?", {"stat": "points"}, "needs_clarification", "intent"),
    ("LeBron James career playoff points", {"stat": "points"}, "needs_clarification", "season_type"),
    ("Where does LeBron James rank all-time?", {}, "needs_clarification", "stat"),
    ("Who has the most points ever?", {}, "needs_clarification", "stat"),
])
def test_career_clarifications(question, fields, status, clarify):
    n = guard(question, **fields)
    assert n.status == status and n.clarify_field == clarify


def test_playoff_career_with_playoff_reading_is_valid():
    n = guard("LeBron James career playoff points", stat="points", season_type="playoffs")
    assert n.status == "valid" and n.request.season_type == "playoffs"


@pytest.mark.parametrize("question,fields", [
    ("Kobe Bryant career high in points", {"stat": "points"}),
    ("Most points in a single season in NBA history", {"stat": "points"}),
    ("Lakers all-time leading scorer", {"stat": "points"}),
    ("LeBron James and Kareem Abdul-Jabbar career points", {"stat": "points"}),
    ("Who has the highest career points per game ever?", {"stat": "points", "aggregation": "per_game"}),
    ("Who has the most career minutes?", {"stat": "minutes"}),
    ("Best career free throw percentage ever", {"stat": "free_throw_percentage"}),
    ("Where does LeBron James rank all-time in career points per game?", {"stat": "points", "aggregation": "per_game"}),
    ("Top 5 in LeBron James career points", {"stat": "points"}),
    ("LeBron James career points in 2023-24", {"stat": "points"}),
    ("Active career assists leaders", {"stat": "assists"}),
    ("LeBron James career points including ABA", {"stat": "points"}),
    ("Most career triple-doubles", {"stat": "points"}),
    ("LeBron James career points against Boston", {"stat": "points"}),
])
def test_out_of_scope_career_questions_are_never_answered(question, fields):
    assert guard(question, **fields).status == "unsupported"


def test_career_measure_choice_uses_career_labels(tmp_path):
    from server.ask.present import clarification
    from server.ask.resolution import PendingResolution, ResolutionStore
    q = "LeBron James career scoring"
    candidates = CandidateLookupService().lookup(q, CONTEXT)
    output = interpreted({"player": "player:2544", "stat": "points"})
    store = ResolutionStore(tmp_path / "career.sqlite3")
    options = clarification("aggregation", "ambiguous", q, PendingResolution(output, candidates, CONTEXT), store).options
    assert [o.label for o in options] == ["Career totals", "Per game"]
    for option, value in zip(options, ["total", "per_game"]):
        chosen = store.read(option.resolution, option.question, CONTEXT)
        n = normalize_question(Normalizer(), chosen.output, chosen.candidates, CONTEXT, option.question)
        assert n.status == "valid" and n.request.stat.aggregation == value


def test_answer_fixtures_round_trip_the_contract():
    responses = Path(__file__).resolve().parents[3] / "src/services/ask/fixtures/responses"
    views = set()
    for name in ("answer-career-totals", "answer-career-leaders", "answer-career-rank"):
        response = AskResponse.model_validate_json((responses / f"{name}.json").read_text())
        assert response.result.kind == "career_stats"
        views.add(response.result.view)
    assert views == {"player_totals", "leaders", "player_rank"}


def test_development_career_labels_survive_the_guard():
    from server.ask.eval.runner import LabeledCase, scored_request
    cases = [LabeledCase.from_json(c) for c in json.loads((FIXTURES / "eval/stage3-dev.json").read_text())["cases"]]
    career_cases = [c for c in cases if c.id.startswith("stage3-career_stats")]
    assert len(career_cases) == 13
    for case in career_cases:
        if case.action != "accept":
            continue
        r = case.request
        fields = {"stat": r.stat.stat, "aggregation": r.stat.aggregation, "season_type": r.season_type}
        if r.player:
            fields["player"] = f"player:{r.player.player_id}"
        n = guard(case.question, **fields)
        assert n.status == "valid", case.id
        assert scored_request(n.request) == scored_request(r), case.id
