import json

import httpx
import pytest

from server.ask.eval import builders as b
from server.ask.interpreters import closed_sets as cs
from server.ask.interpreters.jev import JevAdapter, JevThresholds, build_questions, decode
from server.ask.models.common import DateComponents
from server.ask.models.interpreter import InterpreterInput
from server.ask.models.request import AskContext
from server.ask.protocols import InterpreterAdapter

import datetime as dt

CONTEXT = AskContext(reference_time=dt.datetime.fromisoformat("2026-09-29T12:00:00-04:00"))
CLE = b.team(1610612739, "CLE", "Cleveland Cavaliers", matched="Cavs")
LAL = b.team(1610612747, "LAL", "Los Angeles Lakers")
LAC = b.team(1610612746, "LAC", "LA Clippers")
LAST_WEEK = b.date(0, "last week", DateComponents(kind="relative", relative="last_week"),
                   start=dt.date(2026, 9, 21), end=dt.date(2026, 9, 27))
JALENS = [b.player(1628973, "Jalen Brunson"), b.player(1631114, "Jalen Williams")]


def fake_answers(questions, picks=None, nouls=None):
    """Answers where each Choice puts `prob` on the picked option (default: `__none__`
    or the first option at 0.9) and spreads the rest evenly."""
    picks = picks or {}
    nouls = nouls or {}
    answers = {}
    for qid, q in questions.items():
        if q["type"] == "noul":
            answers[qid] = {"type": "noul", "noul": nouls.get(qid, 0.02)}
            continue
        options = list(q["criteria"])
        pick = picks.get(qid)
        if pick is None:
            pick = (cs.NONE_OPTION if cs.NONE_OPTION in options else options[0], 0.9)
        dist = pick if isinstance(pick, dict) else {pick[0]: pick[1]}
        rest = [o for o in options if o not in dist]
        left = max(0.0, 1 - sum(dist.values()))
        probs = {**dist, **{o: left / len(rest) for o in rest}} if rest else dist
        answers[qid] = {"type": "choice", "choice": max(probs, key=probs.get), "probabilities": probs,
                        "confidence": 0.5}
    return answers


def request_for(question, candidates, *, max_cost=1.0, deadline_ms=5000):
    return InterpreterInput(question=question, context=CONTEXT, candidates=candidates,
                            deadline_ms=deadline_ms, max_cost_usd=max_cost)


def test_closed_sets_cover_contract_enums():
    cs.check_coverage()


def test_adapter_satisfies_protocol_and_refuses_aliases():
    adapter = JevAdapter("k", http_client=httpx.Client(transport=httpx.MockTransport(lambda r: None)))
    assert isinstance(adapter, InterpreterAdapter)
    assert adapter.model == "jev-1.13.0"
    for alias in ("jev-latest", "jev-preview"):
        with pytest.raises(ValueError):
            JevAdapter("k", model=alias)


def test_questions_offer_only_candidates_and_sentinels():
    candidates = b.lookup_result([CLE, LAST_WEEK, *JALENS])
    questions, team_ids = build_questions(candidates)
    assert set(questions["player"]["criteria"]) == {"player:1628973", "player:1631114", cs.NONE_OPTION, cs.OTHER_OPTION}
    assert set(questions["date"]["criteria"]) == {"date:0", cs.NONE_OPTION, cs.OTHER_OPTION}
    assert set(questions["intent"]["criteria"]) == set(cs.INTENTS)
    assert team_ids == {"team_0": "team:1610612739"}
    assert questions["team_0"]["type"] == "noul"
    # No date-part or year questions: Jev never extracts dates, it picks lookup candidates.
    assert not any("year" in qid or "month" in qid for qid in questions)


def test_decode_selects_confident_fields():
    candidates = b.lookup_result([CLE, LAST_WEEK])
    questions, team_ids = build_questions(candidates)
    answers = fake_answers(
        questions,
        picks={"intent": ("game_search", 0.95), "date": ("date:0", 0.92), "team_count": ("1", 0.9)},
        nouls={"team_0": 0.97},
    )
    decoded = decode({"model": "jev-1.13.0", "answers": answers}, team_ids, JevThresholds())
    fields = {f.field: f for f in decoded["fields"]}
    assert decoded["outcome"] == "interpreted"
    assert fields["intent"].selected == ["game_search"]
    assert fields["date"].selected == ["date:0"] and fields["date"].confidence == pytest.approx(0.92)
    assert fields["teams"].selected == ["team:1610612739"]
    assert fields["player"].status == "absent"


def test_decode_reports_ambiguity_instead_of_picking():
    candidates = b.lookup_result([*JALENS])
    questions, team_ids = build_questions(candidates)
    answers = fake_answers(questions, picks={
        "intent": ("boxscore_stat", 0.9),
        "player": {"player:1628973": 0.5, "player:1631114": 0.45},
    })
    fields = {f.field: f for f in decode({"answers": answers}, team_ids, JevThresholds())["fields"]}
    assert fields["player"].status == "ambiguous"
    assert fields["player"].alternatives == ["player:1628973", "player:1631114"]
    assert fields["player"].selected == []


def test_decode_other_option_is_no_matching_candidate():
    candidates = b.lookup_result([LAST_WEEK], unmatched={"team": ["Sonics"]})
    questions, team_ids = build_questions(candidates)
    answers = fake_answers(questions, picks={"intent": ("game_search", 0.9)}, nouls={"team_unlisted": 0.9})
    fields = {f.field: f for f in decode({"answers": answers}, team_ids, JevThresholds())["fields"]}
    assert fields["teams"].status == "no_matching_candidate"


def test_decode_team_count_disagreement_is_ambiguous():
    candidates = b.lookup_result([LAL, LAC])
    questions, team_ids = build_questions(candidates)
    answers = fake_answers(
        questions, picks={"intent": ("game_search", 0.9), "team_count": ("1", 0.9)},
        nouls={"team_0": 0.8, "team_1": 0.75},
    )
    fields = {f.field: f for f in decode({"answers": answers}, team_ids, JevThresholds())["fields"]}
    assert fields["teams"].status == "ambiguous"
    assert set(fields["teams"].alternatives) == {"team:1610612747", "team:1610612746"}


def test_decode_unsupported_and_unreliable():
    candidates = b.lookup_result([])
    questions, team_ids = build_questions(candidates)
    unsupported = fake_answers(questions, picks={"intent": ("unsupported", 0.9),
                                                 "unsupported_reason": ("career_stats", 0.8)})
    decoded = decode({"answers": unsupported}, team_ids, JevThresholds())
    assert decoded["outcome"] == "unsupported" and decoded["unsupported_reason"] == "career_stats"

    diffuse = fake_answers(questions, picks={"intent": {"game_search": 0.35, "boxscore_stat": 0.3}})
    assert decode({"answers": diffuse}, team_ids, JevThresholds())["outcome"] == "unreliable"


def _adapter(handler):
    return JevAdapter("test-key", http_client=httpx.Client(transport=httpx.MockTransport(handler)))


def test_interpret_posts_pinned_model_and_records_resolved_model_and_cost():
    candidates = b.lookup_result([CLE, LAST_WEEK])
    seen = {}

    def handler(request: httpx.Request):
        body = json.loads(request.content)
        seen["body"] = body
        seen["auth"] = request.headers["authorization"]
        answers = fake_answers(body["questions"], picks={"intent": ("game_search", 0.95), "date": ("date:0", 0.9),
                                                         "team_count": ("1", 0.9)}, nouls={"team_0": 0.95})
        return httpx.Response(200, json={"model": "jev-1.13.0", "answers": answers,
                                         "usage": {"input_tokens": 2000, "output_tokens": 300}})

    output = _adapter(handler).interpret(request_for("Cavs games last week", candidates))
    assert seen["body"]["model"] == "jev-1.13.0"
    assert seen["body"]["state"] == {"question": "Cavs games last week"}
    assert seen["auth"] == "Bearer test-key"
    assert output.outcome == "interpreted"
    assert output.metadata.resolved_model == "jev-1.13.0"
    assert output.metadata.usage.cost_usd == pytest.approx(2000 * 0.042 / 1e6)
    assert "test-key" not in output.model_dump_json()


@pytest.mark.parametrize(
    "response, code",
    [
        (httpx.Response(401, json={"error": "bad key"}), "auth_failed"),
        (httpx.Response(422, json={"detail": "bad"}), "http_422"),
        (httpx.Response(200, json={"model": "jev-1.13.0", "answers": {}}), "invalid_response"),
    ],
)
def test_provider_failures_return_unavailable(response, code):
    output = _adapter(lambda r: response).interpret(request_for("q", b.lookup_result([])))
    assert output.outcome == "unavailable"
    assert output.error_code == code
    assert output.fields == []


def test_timeout_and_budget_return_unavailable():
    def timeout(request):
        raise httpx.ReadTimeout("slow", request=request)

    assert _adapter(timeout).interpret(request_for("q", b.lookup_result([]))).error_code == "timeout"

    def never(request):  # pragma: no cover - must not be called
        raise AssertionError("no call expected")

    output = _adapter(never).interpret(request_for("q", b.lookup_result([]), max_cost=0.0))
    assert output.outcome == "unavailable" and output.error_code == "budget_exceeded"
    assert output.metadata.usage.provider_calls == 0
