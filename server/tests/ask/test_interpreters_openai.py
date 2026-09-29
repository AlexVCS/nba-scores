import datetime as dt
import json

import httpx
import pytest

from server.ask.eval import builders as b
from server.ask.interpreters.openai_responses import (
    OpenAIConfig,
    OpenAIResponsesAdapter,
    build_schema,
)
from server.ask.models.common import DateComponents
from server.ask.models.interpreter import InterpreterInput
from server.ask.models.request import AskContext
from server.ask.protocols import InterpreterAdapter

CONTEXT = AskContext(reference_time=dt.datetime.fromisoformat("2026-09-29T12:00:00-04:00"))
TATUM = b.player(1628369, "Jayson Tatum")
CLE = b.team(1610612739, "CLE", "Cleveland Cavaliers")
LAST_WEEK = b.date(0, "last week", DateComponents(kind="relative", relative="last_week"),
                   start=dt.date(2026, 9, 21), end=dt.date(2026, 9, 27))


def blank_output(**overrides):
    empty = {"status": "absent", "values": []}
    data = {
        "intent": "game_search",
        "unsupported_reason": None,
        "stat_scope": empty, "stat": empty, "aggregation": empty,
        "player": empty, "teams": empty, "date": empty, "season": empty, "round": empty, "game_number": empty,
    }
    data.update(overrides)
    return data


def responses_body(output, *, model="gpt-6-luna-2026-09-01", status="completed"):
    return {
        "model": model,
        "status": status,
        "output": [
            {"type": "reasoning", "summary": []},
            {"type": "message", "content": [{"type": "output_text", "text": json.dumps(output)}]},
        ],
        "usage": {"input_tokens": 1000, "output_tokens": 200,
                  "input_tokens_details": {"cached_tokens": 0}, "output_tokens_details": {"reasoning_tokens": 50}},
    }


def adapter(handler, **config):
    return OpenAIResponsesAdapter(
        "test-key", OpenAIConfig(**config), http_client=httpx.Client(transport=httpx.MockTransport(handler))
    )


def request_for(question, candidates, max_cost=1.0):
    return InterpreterInput(question=question, context=CONTEXT, candidates=candidates,
                            deadline_ms=5000, max_cost_usd=max_cost)


def test_protocol_and_model_config():
    luna = adapter(lambda r: None, model="gpt-6-luna", reasoning_effort="low")
    assert isinstance(luna, InterpreterAdapter)
    assert luna.name == "openai_responses" and luna.model == "gpt-6-luna"
    payload = luna.build_payload(request_for("q", b.lookup_result([])))
    assert payload["reasoning"] == {"effort": "low"} and payload["store"] is False
    baseline = adapter(lambda r: None).build_payload(request_for("q", b.lookup_result([])))
    assert baseline["model"] == "gpt-4.1-mini-2025-04-14" and "reasoning" not in baseline


def test_schema_restricts_entities_to_candidate_ids():
    schema = build_schema(b.lookup_result([TATUM, CLE, LAST_WEEK]))
    props = schema["properties"]
    assert props["player"]["properties"]["values"]["items"]["enum"] == ["player:1628369"]
    assert props["teams"]["properties"]["values"]["items"]["enum"] == ["team:1610612739"]
    assert "extracted_date" not in props  # a date candidate exists
    assert set(schema["required"]) == set(props)


def test_schema_allows_extracted_date_only_without_date_candidates():
    props = build_schema(b.lookup_result([TATUM]))["properties"]
    assert "extracted_date" in props
    assert props["date"]["properties"]["values"]["items"]["enum"] == ["__none__"]


def test_interpret_decodes_selection_and_records_usage():
    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=responses_body(blank_output(
            teams={"status": "selected", "values": ["team:1610612739"]},
            date={"status": "selected", "values": ["date:0"]},
        )))

    output = adapter(handler, model="gpt-6-luna").interpret(
        request_for("Cavs games last week", b.lookup_result([CLE, LAST_WEEK]))
    )
    assert seen["body"]["text"]["format"]["strict"] is True
    assert output.outcome == "interpreted"
    assert output.get_field("teams").selected == ["team:1610612739"]
    assert output.get_field("teams").confidence is None
    assert output.metadata.resolved_model == "gpt-6-luna-2026-09-01"
    assert output.metadata.usage.cost_usd == pytest.approx((1000 * 0.10 + 200 * 0.50) / 1e6)


def test_extracted_date_is_kept_and_date_field_dropped():
    output_json = blank_output(extracted_date={
        "kind": "calendar_date", "year": None, "month": 1, "day": 23, "end_year": None,
        "end_month": None, "end_day": None, "relative": None, "weekday": None, "count": None,
    })
    output = adapter(lambda r: httpx.Response(200, json=responses_body(output_json))).interpret(
        request_for("games on January 23", b.lookup_result([]))
    )
    assert output.extracted_date.year is None and output.extracted_date.month == 1
    assert output.get_field("date") is None


@pytest.mark.parametrize("month,day", [(2, 32), (0, 1)])
def test_invalid_extracted_date_requests_date_clarification(month, day):
    output_json = blank_output(extracted_date={
        "kind": "calendar_date", "year": 2026, "month": month, "day": day,
        "end_year": None, "end_month": None, "end_day": None,
        "relative": None, "weekday": None, "count": None,
    })
    output = adapter(lambda r: httpx.Response(200, json=responses_body(output_json))).interpret(
        request_for("games on invalid date", b.lookup_result([]))
    )
    assert output.outcome == "interpreted"
    assert output.extracted_date is None
    assert output.get_field("date").status == "no_matching_candidate"


def test_missing_usage_keeps_cost_unknown():
    body = responses_body(blank_output())
    del body["usage"]
    output = adapter(lambda r: httpx.Response(200, json=body)).interpret(
        request_for("q", b.lookup_result([]))
    )
    assert output.metadata.usage.provider_calls == 1
    assert output.metadata.usage.input_tokens is None
    assert output.metadata.usage.cost_usd is None


def test_unknown_ids_or_bad_shapes_are_unreliable_not_guesses():
    bad_id = blank_output(player={"status": "selected", "values": ["player:999"]})
    output = adapter(lambda r: httpx.Response(200, json=responses_body(bad_id))).interpret(
        request_for("q", b.lookup_result([TATUM]))
    )
    assert output.outcome == "unreliable" and output.error_code == "invalid_output"

    two_players = blank_output(player={"status": "selected", "values": ["player:1628369", "player:2544"]})
    candidates = b.lookup_result([TATUM, b.player(2544, "LeBron James")])
    output = adapter(lambda r: httpx.Response(200, json=responses_body(two_players))).interpret(
        request_for("q", candidates)
    )
    assert output.outcome == "unreliable"


def test_unsupported_and_failures():
    unsupported = blank_output(intent="unsupported", unsupported_reason="career_stats")
    output = adapter(lambda r: httpx.Response(200, json=responses_body(unsupported))).interpret(
        request_for("career points", b.lookup_result([]))
    )
    assert output.outcome == "unsupported" and output.unsupported_reason == "career_stats"

    incomplete = responses_body(blank_output(), status="incomplete")
    output = adapter(lambda r: httpx.Response(200, json=incomplete)).interpret(request_for("q", b.lookup_result([])))
    assert output.outcome == "unavailable" and output.error_code == "incomplete_response"

    quota = httpx.Response(429, json={"error": {"type": "insufficient_quota", "message": "no credit"}})
    output = adapter(lambda r: quota).interpret(request_for("q", b.lookup_result([])))
    assert output.outcome == "unavailable" and output.error_code == "rate_limited"
    assert "no credit" not in output.model_dump_json()


def test_budget_is_checked_before_calling():
    def never(request):  # pragma: no cover
        raise AssertionError("no call expected")

    output = adapter(never, model="gpt-6-luna").interpret(request_for("q", b.lookup_result([]), max_cost=0.0))
    assert output.outcome == "unavailable" and output.error_code == "budget_exceeded"
