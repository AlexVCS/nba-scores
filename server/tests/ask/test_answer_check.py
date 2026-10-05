"""Answer-accuracy check (ADR 0009 zero guesses and latency), fully offline."""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest
import requests

from server.ask import pipeline as pipeline_module
from server.ask.models.response import (
    SourceMetadata, TeamRecordRow, TeamRecordsResult,
)
from server.ask.resolvers import seasons
from server.ask.resolvers.errors import NotFoundError, UnavailableError
from server.ask.resolvers.output import ResolverOutput
from server.ask.tools import REGISTRY
from server.services import basketball_reference

REPO = Path(__file__).resolve().parents[3]
GOLD = REPO / "server/tests/ask/fixtures/answers/answer-gold-draft.json"
AS_OF = dt.datetime(2026, 9, 30, tzinfo=dt.timezone.utc)
BOS = {"team_id": 1610612738, "tricode": "BOS", "name": "Boston Celtics"}
JOKIC = {"player_id": 203999, "name": "Nikola Jokic"}
SOURCE = {"url": "https://www.basketball-reference.com/leagues/NBA_2008.html",
          "read": "Boston Celtics 66-16", "checked_at": "2026-09-30"}


def load():
    spec = importlib.util.spec_from_file_location("answer_check", REPO / "scripts/ask/answer_check.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def ac():
    return load()


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("Unexpected network")
    monkeypatch.setattr(requests.sessions.Session, "request", refuse)
    monkeypatch.setattr(basketball_reference, "_next_start", 0)
    seasons._cache.clear()


def record_case(id="tr-bos", wins=66, **overrides):
    case = {"id": id, "family": "team_records", "tags": ["team"], "question": "Celtics record in 2007-08",
            "request": {"intent": "team_records", "season": "2007-08", "team": BOS},
            "verified": True, "expected_outcome": "answer", "source": SOURCE,
            "checks": [{"path": "result.rows[team.team_id=1610612738].wins", "value": wins},
                       {"path": "result.rows[0].losses", "value": 82 - wins}]}
    return {**case, **overrides}


def gold(tmp_path, cases, name="gold.json"):
    path = tmp_path / name
    path.write_text(json.dumps({"draft": True, "reference_time": "2026-09-30T12:00:00-04:00", "cases": cases}))
    return path


def records_output(wins=66, losses=16):
    result = TeamRecordsResult(season="2007-08", team=BOS, as_of=AS_OF, rows=[
        TeamRecordRow(team=BOS, wins=wins, losses=losses, win_percentage=wins / (wins + losses))])
    return ResolverOutput(result, (), (SourceMetadata(name="nba_stats", label="NBA.com", complete=True),))


def install(monkeypatch, behavior):
    """Stub the resolver the pipeline calls; ``behavior`` maps a request to an output or raises."""
    calls = []

    def resolve(request, *, deadline=None):
        calls.append((request, deadline))
        return behavior(request)
    monkeypatch.setattr(pipeline_module, "resolve", resolve)
    return calls


def run(ac, tmp_path, cases, *extra):
    out = tmp_path / "report.json"
    code = ac.main(["--gold", str(gold(tmp_path, cases)), "--out", str(out), *extra])
    return code, json.loads(out.read_text())


# -- the draft gold fixture -------------------------------------------------------------------


def test_draft_gold_is_valid_marked_draft_and_covers_every_family(ac):
    doc, cases = ac.load_gold(GOLD)
    assert doc["draft"] is True and "DRAFT" in doc["status"]
    assert {c.family for c in cases} == set(REGISTRY)
    tags = {tag for c in cases for tag in c.tags}
    assert {"totals", "per_game", "ties", "playoffs", "pre_2000", "pre_1980", "career", "standings"} <= tags
    for case in cases:
        if case.verified:
            sources = case.source if isinstance(case.source, list) else [case.source]
            assert all(s["url"].startswith(("https://www.basketball-reference.com/", "https://www.nba.com/"))
                       for s in sources), case.id
        else:
            assert case.checks is None and case.expected_outcome is None, case.id


@pytest.mark.parametrize("change, message", [
    ({"family": "season_leaders"}, "differs from request intent"),
    ({"source": None}, "needs a source"),
    ({"source": {**SOURCE, "url": "http://example.com"}}, "needs a source"),
    ({"checks": []}, "at least one check"),
    ({"checks": [{"path": "result.rows[0].wins", "value": 66, "match": "round"}]}, "integer digits"),
    ({"checks": [{"path": "result.rows[0].wins", "value": 66, "match": "close"}]}, "invalid check"),
    ({"checks": [{"path": "result..wins", "value": 66}]}, "invalid path"),
    ({"verified": False}, "unverified cases leave"),
    ({"verified": "yes"}, "true or false"),
    ({"expected_outcome": "ok"}, "expected_outcome"),
])
def test_gold_validation_rejects_malformed_cases(ac, tmp_path, change, message):
    with pytest.raises(ValueError, match=message):
        ac.load_gold(gold(tmp_path, [record_case(**change)]))


def test_gold_validation_rejects_duplicates_and_invalid_requests(ac, tmp_path):
    with pytest.raises(ValueError, match="duplicate"):
        ac.load_gold(gold(tmp_path, [record_case(), record_case()]))
    bad = record_case(request={"intent": "team_records", "season": "2007-09", "team": BOS})
    with pytest.raises(ValueError):
        ac.load_gold(gold(tmp_path, [bad]))


def test_unverified_case_may_have_no_expected_values(ac, tmp_path):
    _, cases = ac.load_gold(gold(tmp_path, [record_case(verified=False, expected_outcome=None, checks=None, source=None)]))
    assert not cases[0].verified


# -- paths and tolerance rules ----------------------------------------------------------------


def test_paths_select_by_index_key_and_wildcard(ac):
    doc = {"result": {"rows": [{"team": {"tricode": "BOS"}, "wins": 64, "values": [{"stat": "points", "value": 1}]},
                               {"team": {"tricode": "NYK"}, "wins": 50, "values": []}]}}
    assert ac.resolve_path(doc, "result.rows[team.tricode=NYK].wins") == 50
    assert ac.resolve_path(doc, "result.rows[-1].team.tricode") == "NYK"
    assert ac.resolve_path(doc, "result.rows[*].wins") == [64, 50]
    assert ac.resolve_path(doc, "result.rows[0].values[stat=points].value") == 1
    for path in ("result.rows[2].wins", "result.rows[team.tricode=MIA].wins", "result.rows[0].losses", "result.rows.wins[0]"):
        with pytest.raises(ac.PathError):
            ac.resolve_path(doc, path)
    doc["result"]["rows"][1]["team"]["tricode"] = "BOS"
    with pytest.raises(ac.PathError, match="matched 2"):
        ac.resolve_path(doc, "result.rows[team.tricode=BOS].wins")


@pytest.mark.parametrize("actual, check, ok", [
    (976 / 79, {"value": 12.4, "match": "round", "digits": 1}, True),   # 12.354... shows as 12.4
    (12.34, {"value": 12.4, "match": "round", "digits": 1}, False),
    (0.4951, {"value": 0.495, "match": "round", "digits": 3}, True),
    (None, {"value": 12.4, "match": "round", "digits": 1}, False),
    ([33.9, 30.42], {"value": [33.9, 30.4], "match": "round", "digits": 1}, True),
    ([33.9], {"value": [33.9, 30.4], "match": "round", "digits": 1}, False),
    (None, {"value": [None], "match": "round", "digits": 1}, False),
    (81.0, {"value": 81}, True),
    (80, {"value": 81}, False),
    (1, {"value": True}, False),
    (None, {"value": None}, True),
    ([2, 1], {"value": [1, 2], "match": "unordered"}, True),
    ([2, 1], {"value": [1, 2]}, False),
    ([1, 1, 2], {"value": [1, 2, 2], "match": "unordered"}, False),
    ([1, 2, 3], {"value": 3, "match": "length"}, True),
    ("nba_stats", {"value": ["nba_stats", "basketball_reference"], "match": "one_of"}, True),
])
def test_compare_tolerance_rules(ac, actual, check, ok):
    assert (ac.compare(actual, check) is None) is ok


# -- scoring through the production execution path --------------------------------------------


def test_correct_answer_passes_without_any_model_call(ac, tmp_path, monkeypatch):
    calls = install(monkeypatch, lambda request: records_output())
    code, report = run(ac, tmp_path, [record_case()])
    assert code == 0 and report["passed"]
    row = report["cases"][0]
    assert row["status"] == "pass" and row["outcome"] == "answer" and row["sources"] == ["nba_stats"]
    assert row["response"]["interpreter"]["model_called"] is False
    # The deadline-aware tool receives the shared retrieval deadline, as in production.
    request, deadline = calls[0]
    assert request.intent == "team_records" and deadline is not None and deadline.remaining() > 0
    assert report["gold_draft"] is True and report["summary"]["statuses"]["pass"] == 1


def test_wrong_value_fails_with_a_diff_and_nonzero_exit(ac, tmp_path, monkeypatch):
    install(monkeypatch, lambda request: records_output(wins=65, losses=17))
    code, report = run(ac, tmp_path, [record_case()])
    assert code == 1 and not report["passed"]
    row = report["cases"][0]
    assert row["status"] == "wrong"
    assert [(d["path"], d["expected"], d["actual"]) for d in row["diffs"]] == [
        ("result.rows[team.team_id=1610612738].wins", 66, 65), ("result.rows[0].losses", 16, 17)]
    assert report["gate_results"]["zero_wrong_answers"] is False


def test_outcomes_that_claim_or_withhold_an_answer(ac, tmp_path, monkeypatch):
    def behavior(request):
        season = request.season
        if season == "2008-09":
            raise NotFoundError("no_record", "season_records_missing")
        if season == "2009-10":
            raise UnavailableError("season_sources_unavailable")
        if season == "2010-11":
            raise RuntimeError("malformed source")
        return records_output()
    install(monkeypatch, behavior)
    cases = [record_case(id=f"c{year}", request={"intent": "team_records", "season": f"{year}-{(year + 1) % 100:02d}", "team": BOS})
             for year in (2007, 2008, 2009, 2010)]
    # Gold expects no record: rendering an answer instead is a wrong answer.
    cases.append(record_case(id="expects-none", expected_outcome="not_found",
                             checks=[{"path": "notice.code", "value": "no_record"}]))
    code, report = run(ac, tmp_path, cases)
    statuses = {r["case_id"]: r["status"] for r in report["cases"]}
    assert statuses == {"c2007": "pass", "c2008": "wrong", "c2009": "no_answer", "c2010": "error", "expects-none": "wrong"}
    assert code == 1
    assert report["summary"]["statuses"] == {"pass": 1, "wrong": 2, "no_answer": 1, "error": 1, "unverified": 0}
    assert report["summary"]["by_family"] == {"team_records": {"pass": 1, "wrong": 2, "no_answer": 1, "error": 1}}
    errored = next(r for r in report["cases"] if r["case_id"] == "c2010")
    assert "RuntimeError" in errored["diffs"][0]["reason"]


def test_expected_not_found_passes_and_unavailable_alone_does_not_fail(ac, tmp_path, monkeypatch):
    def behavior(request):
        if request.season == "2007-08":
            raise NotFoundError("no_record", "season_stat_not_recorded")
        raise UnavailableError("season_sources_unavailable")
    install(monkeypatch, behavior)
    none = record_case(id="none", expected_outcome="not_found", checks=[{"path": "notice.code", "value": "no_record"}])
    later = record_case(id="later", request={"intent": "team_records", "season": "2008-09", "team": BOS})
    code, report = run(ac, tmp_path, [none, later])
    assert [r["status"] for r in report["cases"]] == ["pass", "no_answer"]
    assert code == 0


def test_unverified_cases_run_and_time_but_are_not_scored(ac, tmp_path, monkeypatch):
    install(monkeypatch, lambda request: records_output(wins=1, losses=81))
    code, report = run(ac, tmp_path, [record_case(verified=False, expected_outcome=None, checks=None, source=None)])
    assert code == 0
    assert report["cases"][0]["status"] == "unverified" and report["summary"]["scored"] == 0
    assert report["cases"][0]["latency_ms"] >= 0


def test_latency_percentiles_and_family_breakdown(ac, tmp_path, monkeypatch):
    install(monkeypatch, lambda request: records_output())
    _, cases = ac.load_gold(gold(tmp_path, [record_case(id=f"c{i}") for i in range(20)]))
    ticks = iter(x for i in range(20) for x in (float(i), i + (i + 1) / 1000))  # case i takes (i + 1) ms
    with ac.tempfile.TemporaryDirectory() as state:
        pipe = ac.build_pipeline(Path(state))
        rows = [ac.run_case(pipe, case, dt.datetime.fromisoformat("2026-09-30T12:00:00-04:00"),
                            clock=lambda: next(ticks)) for case in cases]
    assert [r["latency_ms"] for r in rows] == [float(i + 1) for i in range(20)]
    summary = ac.summarize(rows)
    assert summary["latency_ms"]["p50"] == 10 and summary["latency_ms"]["p95"] == 19 and summary["latency_ms"]["max"] == 20
    assert summary["by_family"] == {"team_records": {"pass": 20}}
    assert ac.gate_results(summary)["p95_latency"] is True
    assert ac.gate_results({**summary, "latency_ms": {**summary["latency_ms"], "p95": 4001}})["p95_latency"] is False


def test_slow_answers_fail_only_when_latency_is_enforced(ac, tmp_path, monkeypatch):
    install(monkeypatch, lambda request: records_output())
    monkeypatch.setattr(ac, "GATES", {**ac.GATES, "p95_latency_ms_max": -1})
    code, report = run(ac, tmp_path, [record_case()])
    assert code == 0 and report["gate_results"]["p95_latency"] is False
    code = ac.main(["--gold", str(gold(tmp_path, [record_case()], "g2.json")), "--out", str(tmp_path / "r2.json"),
                   "--enforce-latency"])
    assert code == 1


def test_outputs_are_exclusive(ac, tmp_path, monkeypatch):
    install(monkeypatch, lambda request: records_output())
    path = gold(tmp_path, [record_case()])
    out = tmp_path / "report.json"
    assert ac.main(["--gold", str(path), "--out", str(out)]) == 0
    first = out.read_text()
    with pytest.raises(FileExistsError):
        ac.main(["--gold", str(path), "--out", str(out)])
    assert out.read_text() == first
    # A leftover journal from an interrupted run also blocks a repeat.
    (tmp_path / "other.jsonl").write_text("")
    with pytest.raises(FileExistsError):
        ac.main(["--gold", str(path), "--out", str(tmp_path / "other.json")])
    assert not (tmp_path / "other.json").exists()
    journal = [json.loads(line) for line in (tmp_path / "report.jsonl").read_text().splitlines()]
    assert [row["case_id"] for row in journal] == ["tr-bos"]


def test_case_filter_runs_only_named_cases(ac, tmp_path, monkeypatch):
    install(monkeypatch, lambda request: records_output())
    code, report = run(ac, tmp_path, [record_case(id="a"), record_case(id="b")], "--case", "b")
    assert code == 0 and [r["case_id"] for r in report["cases"]] == ["b"]
    with pytest.raises(ValueError, match="unknown case"):
        ac.main(["--gold", str(gold(tmp_path, [record_case(id="a")], "g3.json")), "--out", str(tmp_path / "x.json"),
                 "--case", "zzz"])


# -- the real resolver, with stubbed source responses -----------------------------------------


def nba_career(rows):
    headers = list(rows[0])
    payload = {"resultSets": [{"name": "SeasonTotalsRegularSeason", "headers": headers,
                               "rowSet": [[r[k] for k in headers] for r in rows]}]}
    return lambda **kwargs: SimpleNamespace(get_dict=lambda: payload)


JOKIC_ROW = {"PLAYER_ID": 203999, "SEASON_ID": "2023-24", "LEAGUE_ID": "00", "TEAM_ID": 1610612743, "GP": 79,
             "REB": 976, "PTS": 2085, "AST": 708, "STL": 108, "BLK": 68, "TOV": 237, "PF": 194, "MIN": 2737,
             "FGM": 822, "FGA": 1411, "FG_PCT": .583, "FG3M": 83, "FG3A": 231, "FG3_PCT": .359,
             "FTM": 358, "FTA": 439, "FT_PCT": .815}


def jokic_case(**overrides):
    return {"id": "pss-jokic", "family": "player_season_stats", "tags": ["per_game"],
            "request": {"intent": "player_season_stats", "player": JOKIC, "season": "2023-24",
                        "stat": {"stat": "rebounds", "aggregation": "per_game"}},
            "verified": True, "expected_outcome": "answer",
            "source": {"url": "https://www.basketball-reference.com/players/j/jokicni01.html",
                       "read": "2023-24 TRB/G 12.4, G 79, TRB 976", "checked_at": "2026-09-30"},
            "checks": [{"path": "result.values[0].value", "value": 12.4, "match": "round", "digits": 1},
                       {"path": "result.games_played", "value": 79},
                       {"path": "result.alternate.values[0].value", "value": 976},
                       {"path": "sources[0].name", "value": ["nba_stats", "basketball_reference"], "match": "one_of"}],
            **overrides}


def test_production_resolver_answer_is_checked_against_gold(ac, tmp_path, monkeypatch):
    monkeypatch.setattr(seasons.playercareerstats, "PlayerCareerStats", nba_career([JOKIC_ROW]))
    code, report = run(ac, tmp_path, [jokic_case()])
    row = report["cases"][0]
    assert code == 0 and row["status"] == "pass", row["diffs"]
    assert row["sources"] == ["nba_stats"]
    assert isinstance(row["response"]["result"], dict) and row["response"]["result"]["kind"] == "player_season_stats"


def test_production_resolver_wrong_source_value_is_caught(ac, tmp_path, monkeypatch):
    # A source row one rebound short changes the per-game display (975 / 79 = 12.34 -> 12.3).
    monkeypatch.setattr(seasons.playercareerstats, "PlayerCareerStats", nba_career([{**JOKIC_ROW, "REB": 975}]))
    code, report = run(ac, tmp_path, [jokic_case()])
    assert code == 1
    assert {d["path"] for d in report["cases"][0]["diffs"]} == {"result.values[0].value", "result.alternate.values[0].value"}


def test_no_model_components_are_ever_used(ac, tmp_path):
    with ac.tempfile.TemporaryDirectory() as state:
        pipe = ac.build_pipeline(Path(state))
    with pytest.raises(AssertionError, match="must not call a model"):
        pipe.adapter.interpret(None)
    with pytest.raises(AssertionError):
        pipe.lookup.lookup("q", None)
    with pytest.raises(AssertionError):
        pipe.policy.decide(None)


# -- answers a release run accepted (--from-run) ----------------------------------------------


def run_row(case_id, request, action="accept", guess=False):
    """A release journal row (scripts/ask/release.py live) reduced to what the check reads."""
    return {"case_id": case_id, "family": request["intent"] if request else "team_records",
            "score": {"case_id": case_id, "action": action, "correct": action == "accept" and not guess,
                      "guess": guess, "actual_request": request if action == "accept" else None},
            "decision": {"action": action}, "tier_outputs": []}


def journal(tmp_path, rows, name="run.jsonl"):
    path = tmp_path / name
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return path


def check_run(ac, tmp_path, rows, cases, *extra):
    out = tmp_path / "answers.json"
    run_path = journal(tmp_path, rows)
    code = ac.main(["--from-run", str(run_path), "--gold", str(gold(tmp_path, cases)), "--out", str(out), *extra])
    return code, json.loads(out.read_text())


LABEL = record_case()["request"]


def test_run_accepting_the_label_is_scored_against_gold(ac, tmp_path, monkeypatch):
    calls = install(monkeypatch, lambda request: records_output())
    # Team display fields are not compared, as in the release scorer.
    shown = {**LABEL, "team": {**BOS, "name": "Celtics"}}
    code, report = check_run(ac, tmp_path, [run_row("tr-bos", shown)], [record_case()])
    assert code == 0 and report["passed"], report["cases"][0]["diffs"]
    row = report["cases"][0]
    assert row["status"] == "pass" and row["has_gold"] and row["request"]["team"]["name"] == "Celtics"
    assert len(calls) == 1 and calls[0][0].team.name == "Celtics"  # the request the run produced is executed
    assert report["accepted"] == 1 and report["summary"]["statuses"]["guess"] == 0
    assert set(report["gate_results"]) == {"zero_wrong_answers", "zero_errors", "p95_latency", "zero_guesses", "all_verified"}


def test_run_wrong_value_for_the_labeled_request_is_wrong(ac, tmp_path, monkeypatch):
    install(monkeypatch, lambda request: records_output(wins=65, losses=17))
    code, report = check_run(ac, tmp_path, [run_row("tr-bos", LABEL)], [record_case()])
    assert code == 1 and report["cases"][0]["status"] == "wrong"
    assert report["gate_results"]["zero_wrong_answers"] is False


def test_run_request_that_differs_from_the_label_is_a_guess_and_what_it_showed_is_recorded(ac, tmp_path, monkeypatch):
    install(monkeypatch, lambda request: records_output())
    other = {**LABEL, "season": "2008-09"}
    code, report = check_run(ac, tmp_path, [run_row("tr-bos", other)], [record_case()])
    row = report["cases"][0]
    assert code == 1 and not report["passed"]
    # Even an answer whose values happen to equal gold is a guess for a wrong request.
    assert row["status"] == "guess" and row["outcome"] == "answer"
    assert row["response"]["result"]["rows"][0]["wins"] == 66 and row["request"]["season"] == "2008-09"
    assert row["diffs"][0]["path"] == "request" and row["diffs"][0]["expected"]["season"] == "2007-08"
    assert report["gate_results"]["zero_guesses"] is False


def test_run_answers_without_verified_gold_are_unverified_and_never_pass(ac, tmp_path, monkeypatch):
    install(monkeypatch, lambda request: records_output())
    unverified = record_case(id="u", verified=False, expected_outcome=None, checks=None, source=None)
    rows = [run_row("u", LABEL), run_row("no-gold", LABEL)]
    code, report = check_run(ac, tmp_path, rows, [unverified])
    assert [r["status"] for r in report["cases"]] == ["unverified", "unverified"]
    assert [r["has_gold"] for r in report["cases"]] == [True, False]
    assert code == 1 and not report["passed"] and report["gate_results"]["all_verified"] is False
    # Without a label, the run's own guess flag still marks a wrong interpretation.
    out = tmp_path / "flagged.json"
    code = ac.main(["--from-run", str(journal(tmp_path, [run_row("no-gold", LABEL, guess=True)], "g.jsonl")),
                    "--gold", str(gold(tmp_path, [unverified], "g.json")), "--out", str(out)])
    assert code == 1 and json.loads(out.read_text())["cases"][0]["status"] == "guess"


def test_run_cases_without_an_accept_are_not_executed(ac, tmp_path, monkeypatch):
    calls = install(monkeypatch, lambda request: records_output())
    rows = [run_row("tr-bos", LABEL), run_row("c", None, action="clarify"), run_row("u", None, action="unsupported"),
            run_row("f", None, action="fail")]
    code, report = check_run(ac, tmp_path, rows, [record_case(), record_case(id="c")])
    assert code == 0 and len(calls) == 1
    assert report["run_cases"] == 4 and report["accepted"] == 1 and report["gold_not_accepted"] == ["c"]
    # A run that accepted nothing has checked nothing, so it does not pass.
    out = tmp_path / "none.json"
    assert ac.main(["--from-run", str(journal(tmp_path, rows[1:], "no-accepts.jsonl")), "--gold",
                    str(gold(tmp_path, [record_case()], "n.json")), "--out", str(out)]) == 1
    assert json.loads(out.read_text())["passed"] is False


def test_run_errors_and_unavailable_follow_the_gold_rules(ac, tmp_path, monkeypatch):
    def behavior(request):
        if request.season == "2009-10":
            raise UnavailableError("season_sources_unavailable")
        raise RuntimeError("malformed source")
    install(monkeypatch, behavior)
    later = {**LABEL, "season": "2009-10"}
    cases = [record_case(id="a"), record_case(id="b", request=later)]
    code, report = check_run(ac, tmp_path, [run_row("a", LABEL), run_row("b", later)], cases)
    assert [r["status"] for r in report["cases"]] == ["error", "no_answer"] and code == 1


def test_run_cases_use_their_own_reference_time(ac, tmp_path, monkeypatch):
    install(monkeypatch, lambda request: records_output())
    case = record_case(reference_time="2025-02-10T12:00:00-05:00")
    _, report = check_run(ac, tmp_path, [run_row("tr-bos", LABEL)], [case])
    assert report["cases"][0]["response"]["interpretation"]["reference_time"].startswith("2025-02-10")


def test_run_reads_a_release_report_and_records_its_identity(ac, tmp_path, monkeypatch):
    install(monkeypatch, lambda request: records_output())
    path = tmp_path / "release.json"
    path.write_text(json.dumps({"frozen_commit": "abc", "cases_sha256": "def", "cases": [run_row("tr-bos", LABEL)]}))
    out = tmp_path / "answers.json"
    assert ac.main(["--from-run", str(path), "--gold", str(gold(tmp_path, [record_case()])), "--out", str(out)]) == 0
    report = json.loads(out.read_text())
    assert report["run_frozen_commit"] == "abc" and report["run_cases_sha256"] == "def" and len(report["run_sha256"]) == 64


def test_run_outputs_are_exclusive_and_inputs_validated(ac, tmp_path, monkeypatch):
    install(monkeypatch, lambda request: records_output())
    code, _ = check_run(ac, tmp_path, [run_row("tr-bos", LABEL)], [record_case()])
    assert code == 0
    with pytest.raises(FileExistsError):
        ac.main(["--from-run", str(tmp_path / "run.jsonl"), "--gold", str(tmp_path / "gold.json"),
                 "--out", str(tmp_path / "answers.json")])
    with pytest.raises(ValueError, match="duplicate"):
        ac.main(["--from-run", str(journal(tmp_path, [run_row("a", LABEL)] * 2, "dup.jsonl")),
                 "--gold", str(tmp_path / "gold.json"), "--out", str(tmp_path / "dup.json")])
    with pytest.raises(ValueError, match="without a recorded request"):
        bad = run_row("a", LABEL)
        bad["score"]["actual_request"] = None
        ac.main(["--from-run", str(journal(tmp_path, [bad], "bad.jsonl")),
                 "--gold", str(tmp_path / "gold.json"), "--out", str(tmp_path / "bad.json")])
    with pytest.raises(ValueError, match="unknown case"):
        ac.main(["--from-run", str(tmp_path / "run.jsonl"), "--gold", str(tmp_path / "gold.json"),
                 "--out", str(tmp_path / "x.json"), "--case", "zzz"])
