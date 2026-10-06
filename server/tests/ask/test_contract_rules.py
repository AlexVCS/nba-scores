"""Cross-cutting contract rules checked against every fixture and model."""

import datetime as dt
import json
import re
import typing
from pathlib import Path
from typing import get_args

import pytest
from pydantic import BaseModel, ValidationError

from server.ask.models import candidates, common, interpreter, request, response
from server.ask.models.candidates import CandidateField
from server.ask.models.common import ClarifyField, DateComponents, DateRange, TeamRef, canonical_json
from server.ask.models.interpreter import (
    CANDIDATE_BACKED_FIELDS,
    INTERPRETER_TO_CANDIDATE_FIELD,
    NormalizationResult,
)
from server.ask.models.request import AskContext, BoxscoreStatRequest, GameSearchRequest
from server.ask.models.response import AskResponse, PostseasonRoundRow, VerifiedLink
from server.ask.protocols import CASCADE_DECISION_ADAPTER, ClarifyDecision, ExpandCandidatesDecision

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_DIR = REPO_ROOT / "src" / "services" / "ask" / "fixtures"
ALL_FIXTURES = sorted(FIXTURE_DIR.glob("*/*.json"))
RESPONSES = {p.stem: json.loads(p.read_text()) for p in sorted((FIXTURE_DIR / "responses").glob("*.json"))}
LINK_KEYS = set(VerifiedLink.model_fields)
NEW_YORK = common.NEW_YORK


# ---------------------------------------------------------------- links


def _walk(node, path=()):
    yield path, node
    if isinstance(node, dict):
        for key, value in node.items():
            yield from _walk(value, path + (key,))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _walk(value, path + (index,))


def _contract_models():
    for module in (common, request, candidates, interpreter, response):
        for value in vars(module).values():
            if isinstance(value, type) and issubclass(value, BaseModel) and value.__module__ == module.__name__:
                yield value


def _mentions_link_type(annotation) -> bool:
    if annotation is VerifiedLink:
        return True
    return any(_mentions_link_type(arg) for arg in typing.get_args(annotation))


@pytest.mark.parametrize("model", list(_contract_models()), ids=lambda m: m.__name__)
def test_every_url_field_is_a_verified_link(model):
    for name, field in model.model_fields.items():
        if model is VerifiedLink and name == "href":
            continue
        if re.search(r"href|url|link", name):
            assert _mentions_link_type(field.annotation), f"{model.__name__}.{name} must use VerifiedLink"


@pytest.mark.parametrize("path", ALL_FIXTURES, ids=lambda p: f"{p.parent.name}/{p.stem}")
def test_fixture_urls_only_appear_in_verified_links(path):
    data = json.loads(path.read_text())
    for where, node in _walk(data):
        if isinstance(node, str) and re.match(r"^(/|https?:|javascript:|data:|mailto:|www\.)", node, re.I):
            assert where[-1] == "href", f"URL outside a link at {where}"
        if isinstance(node, dict) and "href" in node:
            assert set(node) == LINK_KEYS, f"href outside VerifiedLink at {where}"
            VerifiedLink.model_validate(node)


@pytest.mark.parametrize(
    "href",
    [
        "https://example.org/",
        "javascript:alert(1)",
        "//evil.example/games/0022500001/boxscore",
        "/playoffs/2025/finals-okc-ind",
        "/playoffs/2026/east-first-round-det-orl",
        "/playoffs/2026/series-r1-1610612753-1610612765",
    ],
)
def test_links_reject_unlisted_targets(href):
    for external in (False, True):
        with pytest.raises(ValidationError):
            VerifiedLink(kind="playoff_series", label="Open", href=href, external=external)
    opponent = TeamRef(team_id=1610612737, tricode="ATL", name="Atlanta Hawks")
    with pytest.raises(ValidationError):
        PostseasonRoundRow.model_validate(
            {
                "round": "first_round",
                "opponent": opponent.model_dump(),
                "team_wins": 4,
                "opponent_wins": 2,
                "won": True,
                "series_link": {"kind": "playoff_series", "label": "Open", "href": href, "external": False},
            }
        )


@pytest.mark.parametrize(
    "href",
    [
        "/playoffs/2025/the-finals",
        "/playoffs/2026/east-conference-first-round-1",
        "/playoffs/2026/west-conference-semifinal-2",
        "/playoffs/2026/east-conference-final-1",
        "/playoffs/1947/division-winners-first-round-1",
        "/playoffs/1950/nba-semifinals-round-3-1",
    ],
)
def test_links_accept_app_series_slugs(href):
    VerifiedLink(kind="playoff_series", label="Open series", href=href)


# ---------------------------------------------------------------- spoilers


def _is_postseason(data) -> bool:
    result = data.get("result") or {}
    if data.get("spoiler_gate") or result.get("kind") in ("playoff_series", "postseason_summary"):
        return True
    return result.get("kind") == "boxscore_stat" and result["game"]["season_type"] == "playoffs"


def _visible_team_ids(node):
    """Team IDs readable while hidden (skips anything flagged as a spoiler and
    the scoreboard payload, which GameResultItem guards)."""
    if isinstance(node, dict):
        if node.get("spoiler") is True or "gameId" in node:
            return
        if {"team_id", "tricode", "name"} <= set(node):
            yield node["team_id"]
        for value in node.values():
            yield from _visible_team_ids(value)
    elif isinstance(node, list):
        for value in node:
            yield from _visible_team_ids(value)


@pytest.mark.parametrize("name", [n for n, d in RESPONSES.items() if _is_postseason(d)])
def test_postseason_participants_are_named_or_guarded(name):
    data = RESPONSES[name]
    items = data["interpretation"]["items"]
    for item in items:
        if item["origin"] == "inferred" and item["field"] in ("team", "teams", "game", "series"):
            assert item["spoiler"], f"inferred {item['field']} chip must be a spoiler"
    named = {i["team_id"] for i in items if i["team_id"] and i["origin"] != "inferred" and not i["spoiler"]}
    assert set(_visible_team_ids(data["result"])) <= named


def test_gated_outcomes_share_hidden_state():
    gated = {n: d for n, d in RESPONSES.items() if d["spoiler_gate"]}
    assert {d["outcome"] for d in gated.values()} == {"answer", "not_found"}
    assert len({json.dumps(d["spoiler_gate"], sort_keys=True) for d in gated.values()}) == 1
    for data in gated.values():
        visible = [(i["field"], i["origin"]) for i in data["interpretation"]["items"] if not i["spoiler"]]
        assert ("round", "question") in visible and ("game_number", "question") in visible
        assert all(link["spoiler"] for link in data["links"])
        assert all(s["spoiler"] for s in data["suggestions"])


def _game_items(data):
    result = data.get("result") or {}
    if result.get("kind") == "games":
        for day in result["days"]:
            for item in day["games"]:
                yield day["date"], item
    elif result.get("kind") == "playoff_series":
        for item in result["games"]["value"]:
            yield item["date"], item


@pytest.mark.parametrize("name", list(RESPONSES))
def test_conditional_games_are_whole_unit_spoilers(name):
    data = RESPONSES[name]
    for _, item in _game_items(data):
        if item["game"]["ifNecessary"]:
            assert item["spoiler"] and item["spoilers"]["labels"]
    result = data.get("result") or {}
    if result.get("kind") == "boxscore_stat" and result["scope"] == "leaders":
        assert result["leaders"]["spoiler"]


def test_fixtures_cover_spoiler_edge_cases():
    leaders = [d["result"]["leaders"]["value"] for d in RESPONSES.values() if (d["result"] or {}).get("leaders")]
    assert any(len({row["rank"] for row in rows}) < len(rows) for rows in leaders), "need a tied-leaders fixture"
    assert any(item["spoiler"] for d in RESPONSES.values() for _, item in _game_items(d))
    rows = [r for d in RESPONSES.values() if (d["result"] or {}).get("kind") == "postseason_summary" for r in d["result"]["series"]["value"]]
    assert {r["status"] for r in rows} >= {"complete", "in_progress"}


# ---------------------------------------------------------------- dates


@pytest.mark.parametrize("name", list(RESPONSES))
def test_game_dates_agree_with_timestamps(name):
    for day_date, item in _game_items(RESPONSES[name]):
        game = item["game"]
        utc = dt.datetime.fromisoformat(game["gameTimeUTC"].replace("Z", "+00:00"))
        assert item["date"] == day_date == utc.astimezone(NEW_YORK).date().isoformat()
        assert game["gameCode"].startswith(item["date"].replace("-", ""))
        for link in item["links"]:
            if "?date=" in link["href"]:
                assert link["href"].endswith(item["date"])


@pytest.mark.parametrize(
    ("instant", "ny_date", "ny_offset_hours"),
    [
        ("2026-02-09T02:00:00Z", "2026-02-08", -5),  # after midnight UTC, still Feb 8 in New York
        ("2026-02-09T05:00:00Z", "2026-02-09", -5),  # New York midnight
        ("2026-03-08T06:59:00Z", "2026-03-08", -5),  # 01:59 EST, before spring-forward
        ("2026-03-08T07:00:00Z", "2026-03-08", -4),  # 03:00 EDT
        ("2026-11-01T05:30:00Z", "2026-11-01", -4),  # 01:30 EDT, before fall-back
        ("2026-11-01T06:30:00Z", "2026-11-01", -5),  # 01:30 EST, after fall-back
        ("2026-11-02T04:30:00Z", "2026-11-01", -5),
    ],
)
def test_reference_time_is_new_york(instant, ny_date, ny_offset_hours):
    context = AskContext(reference_time=instant)
    assert context.reference_time.date().isoformat() == ny_date
    assert context.reference_time.utcoffset() == dt.timedelta(hours=ny_offset_hours)
    interpretation = response.Interpretation(reference_time=instant)
    assert interpretation.reference_time == context.reference_time


def test_reference_time_must_be_aware():
    with pytest.raises(ValidationError):
        AskContext(reference_time=dt.datetime(2026, 2, 9, 2))


def test_overlong_relative_ranges_are_representable_but_not_executable():
    components = DateComponents(kind="relative", relative="past_days", count=8)
    assert components.count == 8
    with pytest.raises(ValidationError):
        DateRange(start=dt.date(2026, 2, 1), end=dt.date(2026, 2, 8))


# ---------------------------------------------------------------- cache keys


def test_canonical_json_is_the_cache_key():
    knicks = TeamRef(team_id=1610612752, tricode="NYK", name="New York Knicks")
    dates = {"start": "2026-02-02", "end": "2026-02-08"}
    a = GameSearchRequest(dates=dates, teams=[knicks])
    b = GameSearchRequest.model_validate({"teams": [knicks.model_dump()], "dates": dates, "intent": "game_search"})
    assert canonical_json(a) == canonical_json(b)
    assert canonical_json(a) != canonical_json(GameSearchRequest(dates=dates))
    with pytest.raises(TypeError):
        hash(a)  # shallowly frozen: nested lists make models unhashable


# ---------------------------------------------------------------- field enums


def test_clarify_fields_agree_across_layers():
    http = response.Clarification.model_fields["field"].annotation
    normalized = NormalizationResult.model_fields["clarify_field"].annotation
    assert http is ClarifyField
    assert set(get_args(normalized)) - {type(None)} == {ClarifyField}
    assert ClarifyDecision.model_fields["field"].annotation is ClarifyField
    assert ExpandCandidatesDecision.model_fields["field"].annotation is CandidateField
    assert set(INTERPRETER_TO_CANDIDATE_FIELD) == CANDIDATE_BACKED_FIELDS
    assert set(INTERPRETER_TO_CANDIDATE_FIELD.values()) == set(get_args(CandidateField))
    assert set(get_args(ClarifyField)) <= set(get_args(interpreter.InterpreterField))


def test_cascade_decisions_are_action_specific():
    with pytest.raises(ValidationError):
        CASCADE_DECISION_ADAPTER.validate_python({"action": "expand_candidates", "field": "teams", "reason": "x"})
    with pytest.raises(ValidationError):
        CASCADE_DECISION_ADAPTER.validate_python({"action": "fallback", "reason": "x"})
    decision = CASCADE_DECISION_ADAPTER.validate_python(
        {"action": "clarify", "field": "stat_scope", "clarify_reason": "ambiguous", "reason": "x"}
    )
    assert isinstance(decision, ClarifyDecision)


@pytest.mark.parametrize("stat", ["stat_line", "field_goal_percentage", "three_point_percentage", "free_throw_percentage"])
def test_leaders_reject_stats_without_a_ranking_rule(stat):
    with pytest.raises(ValidationError):
        BoxscoreStatRequest(scope="leaders", stat={"stat": stat}, game={"game_id": "0042400404"})


# ---------------------------------------------------------------- clarification tokens


def test_two_step_clarification_continues_without_a_model():
    first = RESPONSES["clarification-two-step-player"]
    second = RESPONSES["clarification-two-step-year"]
    assert first["clarification"]["field"] == "player"
    assert second["clarification"]["field"] == "date"
    assert second["question"] in {o["question"] for o in first["clarification"]["options"]}
    assert second["interpreter"]["model_called"] is False
    tokens = [o["resolution"] for r in (first, second) for o in r["clarification"]["options"]]
    assert len(tokens) == len(set(tokens))
    AskResponse.model_validate(second)
