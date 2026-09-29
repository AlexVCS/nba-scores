import json
from pathlib import Path
from typing import get_args

import pytest

from server.ask.models.common import Intent
from server.ask.models.response import AskResponse, AskSuggestResponse, Outcome

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_DIR = REPO_ROOT / "src" / "services" / "ask" / "fixtures"
RESPONSE_FIXTURES = sorted((FIXTURE_DIR / "responses").glob("*.json"))
SUGGEST_FIXTURES = sorted((FIXTURE_DIR / "suggest").glob("*.json"))


@pytest.mark.parametrize("path", RESPONSE_FIXTURES, ids=lambda p: p.stem)
def test_response_fixture_matches_contract(path):
    data = json.loads(path.read_text())
    response = AskResponse.model_validate(data)
    # Round-trip: fixtures spell out every field, so nothing is lost or added.
    assert response.model_dump(mode="json") == data


@pytest.mark.parametrize("path", SUGGEST_FIXTURES, ids=lambda p: p.stem)
def test_suggest_fixture_matches_contract(path):
    AskSuggestResponse.model_validate_json(path.read_text())


def test_fixtures_cover_every_outcome_and_intent():
    responses = [AskResponse.model_validate_json(p.read_text()) for p in RESPONSE_FIXTURES]
    assert {r.outcome for r in responses} == set(get_args(Outcome))
    answered = {r.interpretation.intent for r in responses if r.outcome == "answer"}
    assert answered == set(get_args(Intent))
    assert any(r.outcome == "needs_clarification" and r.clarification.options for r in responses)
    assert SUGGEST_FIXTURES
