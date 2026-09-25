import json

import pytest
import requests

from server.models.ask import AskInterpretation
from server.services import ask_parser


def _provider_response(interpretation: dict, usage: dict | None = None):
    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"output_text": json.dumps(interpretation), "usage": usage or {}}

    return Response()


def test_parse_returns_mentions_and_unresolved_date(monkeypatch):
    payload = {
        "intent": "game_search",
        "operation": "list",
        "mentions": [{"text": "Cavs", "kind": "team"}],
        "date_expressions": [{"text": "last week", "kind": "relative"}],
        "round_mention": None,
        "game_number": None,
        "statistics": [],
        "ambiguities": [],
        "unsupported_reason": None,
    }
    calls = {}

    def fake_post(url, **kwargs):
        calls.update({"url": url, **kwargs})
        return _provider_response(payload, {"input_tokens": 40, "output_tokens": 25, "total_tokens": 65})

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(ask_parser.requests, "post", fake_post)
    result = ask_parser.parse_ask("What did the Cavs play last week?")

    assert result.interpretation.mentions[0].text == "Cavs"
    assert result.interpretation.date_expressions[0].text == "last week"
    assert result.metadata.usage.total_tokens == 65
    assert calls["timeout"] == ask_parser.REQUEST_TIMEOUT_SECONDS
    assert calls["json"]["max_output_tokens"] == ask_parser.MAX_OUTPUT_TOKENS
    assert "gameId" not in calls["json"]


def test_parse_preserves_explicit_abstention(monkeypatch):
    payload = {
        "intent": "needs_clarification",
        "operation": None,
        "mentions": [],
        "date_expressions": [],
        "round_mention": None,
        "game_number": None,
        "statistics": [],
        "ambiguities": [{"field": "date", "reason": "Which season do you mean?"}],
        "unsupported_reason": None,
    }
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(ask_parser.requests, "post", lambda *args, **kwargs: _provider_response(payload))

    result = ask_parser.parse_ask("How many points did he score?")
    assert result.interpretation.intent == "needs_clarification"
    assert result.interpretation.ambiguities[0].field == "date"


def test_parse_requires_key_and_bounds_input(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(ask_parser, "_configured_api_key", lambda: None)
    with pytest.raises(ask_parser.AskParserUnavailable):
        ask_parser.parse_ask("show games")
    with pytest.raises(ValueError):
        ask_parser.parse_ask("x" * (ask_parser.MAX_INPUT_CHARS + 1))


def test_interpretation_rejects_authoritative_fields():
    with pytest.raises(ValueError):
        AskInterpretation.model_validate({
            "intent": "game_search",
            "operation": "list",
            "mentions": [],
            "date_expressions": [],
            "round_mention": None,
            "game_number": None,
            "statistics": [],
            "ambiguities": [],
            "unsupported_reason": None,
            "game_id": "001",
        })


def test_parse_extracts_round_game_number_and_operation(monkeypatch):
    payload = {
        "intent": "boxscore_stats",
        "operation": "leaders",
        "mentions": [{"text": "Celtics", "kind": "team"}],
        "date_expressions": [{"text": "2024 Finals", "kind": "season"}],
        "round_mention": "2024 Finals",
        "game_number": 4,
        "statistics": ["points"],
        "ambiguities": [],
        "unsupported_reason": None,
    }
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(ask_parser.requests, "post", lambda *args, **kwargs: _provider_response(payload))

    result = ask_parser.parse_ask("Who led Celtics in scoring in game 4 of 2024 Finals?")
    assert result.interpretation.operation == "leaders"
    assert result.interpretation.round_mention == "2024 Finals"
    assert result.interpretation.game_number == 4
    assert result.interpretation.statistics == ["points"]


def test_parse_rejects_incomplete_provider_output(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(ask_parser.requests, "post", lambda *args, **kwargs: _provider_response({"intent": "game_search"}))

    with pytest.raises(ask_parser.AskParserInvalidResponse):
        ask_parser.parse_ask("show games")


def test_parse_maps_timeout_to_unavailable(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def timeout(*args, **kwargs):
        raise requests.Timeout("slow")

    monkeypatch.setattr(ask_parser.requests, "post", timeout)
    with pytest.raises(ask_parser.AskParserUnavailable):
        ask_parser.parse_ask("show games")


def test_parse_rejects_noncompleted_response(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    response = _provider_response({
        "intent": "game_search", "operation": "list", "mentions": [],
        "date_expressions": [], "round_mention": None, "game_number": None,
        "statistics": [], "ambiguities": [], "unsupported_reason": None,
    })
    original_json = response.json
    response.json = lambda: {**original_json(), "status": "incomplete"}
    monkeypatch.setattr(ask_parser.requests, "post", lambda *args, **kwargs: response)
    with pytest.raises(ask_parser.AskParserInvalidResponse):
        ask_parser.parse_ask("show games")


def test_parse_rejects_fabricated_selector(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    payload = {
        "intent": "game_search", "operation": "list",
        "mentions": [{"text": "Lakers", "kind": "team"}],
        "date_expressions": [], "round_mention": None, "game_number": None,
        "statistics": [], "ambiguities": [], "unsupported_reason": None,
    }
    monkeypatch.setattr(ask_parser.requests, "post", lambda *args, **kwargs: _provider_response(payload))
    with pytest.raises(ask_parser.AskParserInvalidResponse):
        ask_parser.parse_ask("show Celtics games")


def test_build_request_is_bounded_and_not_stored(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    request = ask_parser.build_request("game 4 Celtics", "eval-model")
    assert request["model"] == "eval-model"
    assert request["max_output_tokens"] == ask_parser.MAX_OUTPUT_TOKENS
    assert request["store"] is False


def test_parse_rejects_fabricated_game_number(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    payload = {
        "intent": "game_search", "operation": "list", "mentions": [],
        "date_expressions": [], "round_mention": None, "game_number": 4,
        "statistics": [], "ambiguities": [], "unsupported_reason": None,
    }
    monkeypatch.setattr(ask_parser.requests, "post", lambda *args, **kwargs: _provider_response(payload))
    with pytest.raises(ask_parser.AskParserInvalidResponse):
        ask_parser.parse_ask("show Celtics games")
