"""Unseen 2026-09-29 cases 042, 064, 067 and 073: page context was not used."""

import datetime as dt
import json

from server.ask.candidates import CandidateLookupService
from server.ask.interpreters.openai_responses import OpenAIConfig, OpenAIResponsesAdapter
from server.ask.models.interpreter import FieldInterpretation, InterpreterInput, InterpreterMetadata, InterpreterOutput
from server.ask.models.request import AskContext
from server.ask.normalize import Normalizer

NOW = dt.datetime.fromisoformat("2026-09-29T14:15:00-04:00")
META = InterpreterMetadata(adapter="cascade", provider="cascade", model="jev-1.13.0", latency_ms=1)
LOOKUP = CandidateLookupService()


def output(*fields):
    return InterpreterOutput(outcome="interpreted", fields=list(fields), metadata=META)


def selected(field, *values):
    return FieldInterpretation(field=field, status="selected", selected=list(values))


def absent(field):
    return FieldInterpretation(field=field, status="absent")


def test_absent_season_takes_the_selected_playoff_season():
    # 064: the model read the season as absent although lookup offered the page's season.
    context = AskContext(reference_time=NOW, route="playoffs", playoff_season="2023-24")
    candidates = LOOKUP.lookup("How did the Knicks do in the postseason shown here?", context)
    result = Normalizer().normalize(
        output(selected("intent", "postseason_summary"), absent("season"), selected("teams", "team:1610612752")),
        candidates, context,
    )
    assert result.status == "valid"
    assert (result.request.season, result.request.team.tricode) == ("2023-24", "NYK")


def test_absent_season_without_page_context_still_clarifies():
    context = AskContext(reference_time=NOW)
    candidates = LOOKUP.lookup("How did the Knicks do in the postseason?", context)
    result = Normalizer().normalize(
        output(selected("intent", "postseason_summary"), absent("season"), selected("teams", "team:1610612752")),
        candidates, context,
    )
    assert (result.status, result.clarify_field) == ("needs_clarification", "season")


def test_conference_after_round_identifies_the_series():
    # 067: "conference finals in the West" lost the conference, so teams were requested.
    context = AskContext(reference_time=NOW, route="playoffs", playoff_season="2023-24")
    question = "Open the conference finals in the West for the season selected here."
    candidates = LOOKUP.lookup(question, context)
    rounds = candidates.sets["round"].candidates
    assert [(c.value.round, c.value.conference) for c in rounds] == [("conference_finals", "west")]
    result = Normalizer().normalize(
        output(selected("intent", "playoff_series"), selected("round", rounds[0].id), absent("teams"), absent("season")),
        candidates, context,
    )
    assert result.status == "valid"
    request = result.request
    assert (request.season, request.round, request.conference, request.teams) == (
        "2023-24", "conference_finals", "west", [])


def test_selected_scores_date_is_offered_and_used():
    # 073: "the date selected on this page" produced no date candidate.
    context = AskContext(reference_time=NOW, route="scores", view_date=dt.date(2024, 4, 14))
    candidates = LOOKUP.lookup("Who played on the date selected on this page?", context)
    offered = candidates.sets["date"].candidates
    assert [c.source for c in offered] == ["app_context"]
    result = Normalizer().normalize(
        output(selected("intent", "game_search"), absent("date"), absent("teams")), candidates, context,
    )
    assert result.status == "valid"
    assert (result.request.dates.start, result.request.dates.end) == (dt.date(2024, 4, 14), dt.date(2024, 4, 14))


def test_luna_is_told_a_boxscore_game_is_open():
    # 042: without page context Luna read "this game" as a follow-up to an earlier answer.
    question = "How many turnovers did Jayson Tatum have in this game?"
    luna = OpenAIResponsesAdapter("test-key", OpenAIConfig(model="gpt-6-luna", reasoning_effort="low"))
    for context, expected in (
        (AskContext(reference_time=NOW, route="boxscore", game_id="0042300405"), True),
        (AskContext(reference_time=NOW), False),
    ):
        request = InterpreterInput(question=question, context=context, candidates=LOOKUP.lookup(question, context),
                                   deadline_ms=5000, max_cost_usd=1.0)
        payload = luna.build_payload(request)
        assert json.loads(payload["input"][1]["content"])["page_game"] is expected
        assert "`page_game`" in payload["input"][0]["content"]


def test_boxscore_page_game_fills_the_game_selector():
    context = AskContext(reference_time=NOW, route="boxscore", game_id="0042300405")
    question = "How many turnovers did Jayson Tatum have in this game?"
    result = Normalizer().normalize(
        output(selected("intent", "boxscore_stat"), selected("stat_scope", "player"), selected("stat", "turnovers"),
               selected("aggregation", "total"), selected("player", "player:1628369"), absent("date")),
        LOOKUP.lookup(question, context), context,
    )
    assert result.status == "valid"
    assert (result.request.game.game_id, result.request.player.player_id) == ("0042300405", 1628369)
