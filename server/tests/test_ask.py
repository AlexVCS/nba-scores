from datetime import datetime, timezone
from types import SimpleNamespace
from pathlib import Path
import json

from fastapi.testclient import TestClient
import pytest

from server.main import app
from server.models.ask import AskInterpretation, AskParseMetadata, AskParseResult, AskParseUsage
from server.services import ask, ask_parser, ask_basketball, ask_data
from server.services.ask_limits import BudgetLimitError, RateLimiter, TTLCache

resolve_request = ask_basketball.resolve_request


def parsed_request(intent="game_search", **fields):
    interpretation = {"intent": intent, "operation": "list", "mentions": [],
                      "date_expressions": [{"text": "yesterday", "kind": "relative"}],
                      "round_mention": None, "game_number": None, "statistics": [],
                      "ambiguities": [], "unsupported_reason": None, **fields}
    return AskParseResult(interpretation=AskInterpretation.model_validate(interpretation),
                          metadata=AskParseMetadata(provider="openai", model="gpt-4.1-mini", latency_ms=1,
                                                    usage=AskParseUsage(input_tokens=20, output_tokens=30)))


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("ASK_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("ASK_PARSER_MODEL", "gpt-4.1-mini")
    monkeypatch.setattr(ask, "_parses", TTLCache())
    monkeypatch.setattr(ask, "_answers", TTLCache())
    monkeypatch.setattr(ask, "_provider_health", TTLCache())
    monkeypatch.setattr(ask, "_rate", RateLimiter())
    monkeypatch.setattr(ask_parser, "parse_ask", lambda question: parsed_request())
    monkeypatch.setattr(ask_basketball, "resolve_request", lambda *args: SimpleNamespace(normalized_key=("resolved",)))
    monkeypatch.setattr(ask_data, "retrieve_answer", lambda request: ({"status": "ok", "items": []}, False))
    return TestClient(app)


def test_route_validates_length_and_blank_before_parser(isolated, monkeypatch):
    monkeypatch.setattr(ask_parser, "parse_ask", lambda *_: pytest.fail("Invalid body reached parser"))
    for question in ["", "   ", "x" * 301]:
        assert isolated.post("/ask", json={"question": question}).status_code == 422
    assert isolated.post("/ask", json={"question": "hello", "api_key": "forbidden"}).status_code == 422


def test_unsupported_statistic_returns_a_response_instead_of_crashing(isolated, monkeypatch):
    monkeypatch.setattr(ask_basketball, "resolve_request", resolve_request)
    monkeypatch.setattr(ask_parser, "parse_ask", lambda _: parsed_request(
        "boxscore_stats", operation="team_stats", statistics=["quarter_scores"],
    ))
    response = isolated.post("/ask", json={"question": "Quarter scores yesterday"})
    assert response.status_code == 200
    assert response.json()["status"] == "unsupported"
    assert "Quarter scores" in response.json()["interpretation"]


def test_provider_failure_is_structured_and_cooled_down(isolated, monkeypatch):
    calls = []
    def unavailable(question):
        calls.append(question)
        raise ask_parser.AskParserUnavailable("secret provider response")
    monkeypatch.setattr(ask_parser, "parse_ask", unavailable)
    for question in ["Games yesterday", "Games today"]:
        response = isolated.post("/ask", json={"question": question})
        assert response.status_code == 200
        assert response.json()["status"] == "unavailable"
        assert "interpretation" in response.json()["message"]
        assert "secret" not in response.text
    assert len(calls) == 1


def test_identical_parse_only_spends_once(isolated, monkeypatch):
    calls = []
    def parse(question):
        calls.append(question)
        return parsed_request()
    monkeypatch.setattr(ask_parser, "parse_ask", parse)
    for question in ["Games yesterday", "  games   YESTERDAY "]:
        assert isolated.post("/ask", json={"question": question}).status_code == 200
    assert len(calls) == 1


def test_ny_day_invalidates_parse(isolated, monkeypatch):
    calls = []
    monkeypatch.setattr(ask_parser, "parse_ask", lambda query: (calls.append(query), parsed_request())[1])
    ask._answer("Games yesterday", datetime(2026, 3, 9, 3, 59, tzinfo=timezone.utc))
    ask._answer("Games yesterday", datetime(2026, 3, 9, 4, 1, tzinfo=timezone.utc))
    assert len(calls) == 2


def test_normalized_answer_cache_and_correction_invalidation(isolated, monkeypatch):
    calls = []
    def retrieve(request):
        calls.append(request)
        return {"status": "ok", "items": []}, True
    monkeypatch.setattr(ask_data, "retrieve_answer", retrieve)
    for question in ["Cavs games yesterday", "Cleveland games yesterday"]:
        isolated.post("/ask", json={"question": question})
    assert len(calls) == 1
    ask.invalidate_ask_caches()
    isolated.post("/ask", json={"question": "Cavs games yesterday"})
    assert len(calls) == 2


def test_interpretation_uses_current_validated_query_on_cached_answer(isolated, monkeypatch):
    monkeypatch.setattr(ask_parser, "parse_ask", lambda question: parsed_request(
        mentions=[{"text": "Cavs" if "Cavs" in question else "Cleveland Cavaliers", "kind": "team"}]))
    first = isolated.post("/ask", json={"question": "Cavs games yesterday"}).json()
    second = isolated.post("/ask", json={"question": "Cleveland Cavaliers games yesterday"}).json()
    assert first["interpretation"] == ["Cavs", "yesterday"]
    assert second["interpretation"] == ["Cleveland Cavaliers", "yesterday"]


def test_interpretation_formats_stats_playoff_context_and_missing_fields():
    parsed = parsed_request(
        "boxscore_stats", operation="leaders",
        mentions=[{"text": "Celtics", "kind": "team"}],
        date_expressions=[{"text": "2024", "kind": "season"}],
        round_mention="2024 Finals", game_number=4, statistics=["points"],
        ambiguities=[{"field": "player", "reason": "Missing player"}],
    )
    assert ask._interpretation_labels(parsed.interpretation) == [
        "Celtics", "Game leaders", "Points", "2024 NBA Finals", "Game 4", "[which player?]",
    ]


def test_interpretation_does_not_relabel_conference_finals():
    parsed = parsed_request(
        "playoff_series", operation="series_result",
        date_expressions=[{"text": "2024", "kind": "season"}],
        round_mention="Eastern Conference Finals",
    )
    assert ask._interpretation_labels(parsed.interpretation) == ["2024", "Eastern Conference Finals"]


def test_resolved_team_removes_stale_team_ambiguity_chip():
    parsed = parsed_request(
        mentions=[{"text": "Thunder", "kind": "team"}],
        date_expressions=[{"text": "January 2, 2024", "kind": "calendar_date"}],
        ambiguities=[{"field": "team", "reason": "Which team do you mean?"}],
    )
    resolved = SimpleNamespace(intent="game_search", team_ids=(1610612760,))
    assert ask._interpretation_labels(parsed.interpretation, resolved) == ["Thunder", "January 2, 2024"]


def test_rate_and_budget_reject_before_spending(isolated, monkeypatch):
    monkeypatch.setattr(ask, "_rate", RateLimiter(per_ip=0))
    monkeypatch.setattr(ask_parser, "parse_ask", lambda *_: pytest.fail("Rate limit reached parser"))
    response = isolated.post("/ask", json={"question": "Games yesterday"})
    assert response.status_code == 429
    assert response.headers["retry-after"] == "60"
    monkeypatch.setattr(ask, "_rate", RateLimiter())
    class ExhaustedBudget:
        def reserve(self, *args):
            raise BudgetLimitError("over budget")
    monkeypatch.setattr(ask, "Budget", ExhaustedBudget)
    assert isolated.post("/ask", json={"question": "Games yesterday"}).status_code == 429


def test_resolution_and_retrieval_clarification_are_structured(isolated, monkeypatch):
    def clarify(*args):
        raise ask_basketball.AskResolutionError("needs_clarification", "Which game do you mean?")
    monkeypatch.setattr(ask_data, "retrieve_answer", clarify)
    response = isolated.post("/ask", json={"question": "Games yesterday"})
    assert response.json()["status"] == "needs_clarification"
    assert response.json()["items"] == []


def test_logs_are_bounded_expiring_and_do_not_store_question_or_ip(isolated, monkeypatch):
    ask._unsupported.clear()
    parsed = parsed_request("unsupported", operation=None, date_expressions=[], unsupported_reason="Unsupported scope")
    monkeypatch.setattr(ask.time, "time", lambda: 1_000_000)
    for index in range(205):
        ask._record_unsupported(f"question-{index}", parsed.interpretation)
    rows = ask.unsupported_request_log()
    assert len(rows) == 200
    assert "question" not in rows[0] and "ip" not in rows[0]
    monkeypatch.setattr(ask.time, "time", lambda: 1_000_000 + 8 * 86400)
    assert ask.unsupported_request_log() == []


def test_endpoint_resolves_and_calculates_a_repository_boxscore(monkeypatch, tmp_path):
    """Only the external parser and NBA fetches are substituted in this path."""
    game = json.loads((Path(__file__).parents[2] / "exampleBoxScoreResponse.json").read_text())["game"]
    monkeypatch.setenv("ASK_STATE_DIR", str(tmp_path))
    monkeypatch.setattr(ask, "_rate", RateLimiter())
    ask.invalidate_ask_caches()
    monkeypatch.setattr(ask_parser, "parse_ask", lambda question: parsed_request(
        "boxscore_stats", operation="team_stats", mentions=[{"text": "Pistons", "kind": "team"}],
        date_expressions=[{"text": "2025-02-02", "kind": "calendar_date"}], statistics=["points"],
    ))
    monkeypatch.setattr(ask_data.nba_stats_client, "fetch_scoreboard_v3", lambda day: {"games": [game]})
    fetched = []
    monkeypatch.setattr(ask_data, "fetch_boxscoretraditional", lambda game_id: (fetched.append(game_id), game)[1])
    response = TestClient(app).post("/ask", json={"question": "How many points did the Pistons score on 2025-02-02?"})
    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["fields"][0]["value"] == game["homeTeam"]["statistics"]["points"]
    assert item["fields"][0]["spoiler"] is True
    assert fetched == [game["gameId"]]
    assert item["links"][0]["path"] == f"/games/{game['gameId']}/boxscore?date=2025-02-02"


@pytest.mark.parametrize("question, explanation", [
    ("how many wins did the Thunder have in the 2023-24 regular season?", "win totals"),
    ("how many points Shai score in the Thunder's largest win of the 2023–24 regular season?", "biggest win or loss"),
    ("what team won the most games in the 1949-50 regular season?", "standings"),
])
def test_unsupported_season_search_needs_no_provider_or_budget(isolated, monkeypatch, question, explanation):
    monkeypatch.setattr(ask_parser, "parse_ask", lambda *_: pytest.fail("Unsupported request reached provider"))
    monkeypatch.setattr(ask, "Budget", lambda: pytest.fail("Unsupported request reserved budget"))
    monkeypatch.setattr(ask._provider_health, "get", lambda *_: True)
    response = isolated.post("/ask", json={"question": question})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "unsupported"
    assert explanation in body["message"]
    assert body["items"] == []
    assert "Use a playoff year" not in body["message"]
    assert ask.unsupported_request_log()[-1]["intent"] == "unsupported"
