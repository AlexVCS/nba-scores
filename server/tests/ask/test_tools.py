"""Tool registry and router (ADR 0010 stage 1): every layer covers every registered tool."""

from __future__ import annotations

import datetime as dt
from typing import get_args

import pytest

from server.ask import tools
from server.ask.interpreters import closed_sets as cs
from server.ask.models.common import Intent
from server.ask.models.request import ASK_REQUEST_ADAPTER, GameSearchRequest
from server.ask.normalize import RELEVANT_FIELDS, Normalizer
from server.ask.resolvers import EXECUTORS, _resolve

ORIGINAL_ROUTER_ORDER = ["game_search", "boxscore_stat", "playoff_series", "postseason_summary", "player_season_stats", "team_records", "season_leaders", "career_stats", "unsupported"]


def test_registry_matches_contract_intents():
    tools.check_registry()
    assert set(tools.REGISTRY) == set(get_args(Intent))
    for tool in tools.TOOLS:
        assert tool.request_model.model_fields["intent"].default == tool.name


def test_router_offers_every_tool_then_unsupported_in_stable_order():
    options = tools.router_options()
    assert list(options) == ORIGINAL_ROUTER_ORDER
    assert cs.INTENTS == options
    assert cs.UNSUPPORTED_INTENT == tools.UNSUPPORTED


def test_route_names_a_tool_or_none():
    assert tools.route("game_search") is tools.REGISTRY["game_search"]
    assert tools.route("unsupported") is None
    assert tools.route("career_leaders") is None


def test_every_layer_covers_every_tool():
    names = set(tools.REGISTRY)
    assert set(RELEVANT_FIELDS) == names
    assert set(Normalizer().builders()) == names
    assert set(EXECUTORS) == names
    for tool in tools.TOOLS:
        assert RELEVANT_FIELDS[tool.name] == tool.fields


def test_executor_dispatches_by_registered_tool(monkeypatch):
    calls = []
    monkeypatch.setitem(EXECUTORS, "game_search", lambda request: calls.append(request) or "result")
    request = GameSearchRequest(dates={"start": dt.date(2025, 1, 23), "end": dt.date(2025, 1, 23)})
    assert _resolve(request) == "result"
    assert calls == [request]


def test_unregistered_request_type_is_rejected():
    with pytest.raises(TypeError):
        _resolve(object())  # type: ignore[arg-type]


def test_request_adapter_round_trips_each_tool_model():
    request = ASK_REQUEST_ADAPTER.validate_python(
        {"intent": "postseason_summary", "season": "2023-24"})
    assert isinstance(request, tools.REGISTRY["postseason_summary"].request_model)
