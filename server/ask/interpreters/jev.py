"""TypeSafe Jev adapter (`InterpreterAdapter`, name "jev").

Jev is a System One model: it returns typed answers (Choice, Score, Noul) about a
`state`, never free text, and it does not extract names, numbers, or dates. The adapter
sends the question as state and asks one request of speculative closed-set questions
(the documented "fan-out" pattern); Python reads only what the chosen intent needs.

* intent (four intents + "unsupported"), unsupported reason, stat scope, stat, aggregation:
  Choices over the contract enums.
* player, date, season, round, game number: Choices over the lookup's candidate IDs plus
  `__none__` (not mentioned) and `__other__` (mentioned, but no listed candidate fits).
* teams: one Noul per team candidate, one Noul for "a team not in the list", and a
  team-count Choice as a consistency check.

Field confidence is the probability of the chosen option (Choice) or, for teams, the
least decisive team Noul. The adapter only decides `ambiguous` vs `selected`; whether a
confidence is high enough to act on is the cascade policy's job.

HTTP: POST https://api.typesafe.ai/v1/systemone with Bearer auth and
{"model", "state", "questions"}; the response has {"model", "answers", "usage"}.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any

import httpx

from server.ask.interpreters import closed_sets as cs
from server.ask.interpreters.http import ProviderError, post_json
from server.ask.interpreters.pricing import cost_usd, estimate_max_cost
from server.ask.models.candidates import Candidate, CandidateLookupResult
from server.ask.models.interpreter import (
    FieldInterpretation,
    InterpreterInput,
    InterpreterMetadata,
    InterpreterOutput,
    InterpreterUsage,
)

logger = logging.getLogger(__name__)

JEV_MODEL = "jev-1.13.0"
JEV_URL = "https://api.typesafe.ai/v1/systemone"
MAX_CHOICE_OPTIONS = 255

# InterpreterField -> (question id, candidate field) for Choice-backed candidate fields.
CANDIDATE_CHOICES: dict[str, tuple[str, str]] = {
    "player": ("player", "player"),
    "date": ("date", "date"),
    "season": ("season", "season"),
    "round": ("round", "round"),
    "game_number": ("game_number", "game_number"),
    "location": ("location", "location"),
}
NOUNS = {
    "player": "NBA player",
    "date": "date or day for the game(s)",
    "season": "NBA season or playoff year",
    "round": "playoff round",
    "game_number": "numbered game of a playoff series (e.g. 'game 4')",
    "location": "city where the games are played (a venue, not a team)",
}


@dataclass(frozen=True)
class JevThresholds:
    """Adapter-side decision thresholds. Defaults are UNCALIBRATED placeholders.

    Calibrate on development data (#199) before production; do not copy cookbook values.
    """

    # Below this intent probability the output is "unreliable" (fallback candidate).
    intent_min: float = 0.6
    # An "unsupported" top intent needs at least this probability.
    unsupported_min: float = 0.6
    # Two or more real candidates at or above this probability, with the top below
    # `ambiguity_top_max`, make a field "ambiguous".
    ambiguity_floor: float = 0.25
    ambiguity_top_max: float = 0.75
    # A team Noul at or above this selects the team; the team-count Choice must agree.
    noul_yes: float = 0.6
    count_min: float = 0.6


def _describe(candidate: Candidate) -> str:
    parts = [candidate.label]
    value = candidate.value
    if value.kind == "date" and value.resolved is not None:
        parts.append(f"({value.resolved.start.isoformat()} to {value.resolved.end.isoformat()})")
    if value.kind == "player" and value.first_season and value.last_season:
        parts.append(f"(played {value.first_season} to {value.last_season})")
    if value.kind == "team" and (value.valid_from or value.valid_to):
        parts.append(f"(name used {value.valid_from or '?'} to {value.valid_to or 'present'})")
    if candidate.matched_text:
        parts.append(f"- matched '{candidate.matched_text}'")
    if candidate.source == "app_context":
        parts.append("- from the page the user is viewing")
    return " ".join(parts)


def _choice(instructions: Any, criteria: dict[str, str | None]) -> dict[str, Any]:
    if len(criteria) > MAX_CHOICE_OPTIONS:
        raise ValueError(f"Choice has {len(criteria)} options; Jev accepts {MAX_CHOICE_OPTIONS}")
    return {"type": "choice", "instructions": instructions, "criteria": criteria}


def _noul(instructions: Any, true: str, false: str) -> dict[str, Any]:
    return {"type": "noul", "instructions": instructions, "criteria": {"true": true, "false": false}}


def build_questions(candidates: CandidateLookupResult) -> tuple[dict[str, Any], dict[str, str]]:
    """Return (questions, team question id -> team candidate id)."""
    q: dict[str, Any] = {
        "intent": _choice("What is the `question` asking for?", dict(cs.INTENTS)),
        "unsupported_reason": _choice(
            "If the `question` asks for something other than NBA games, one game's box score, "
            "one playoff series, or one postseason, what kind of request is it?",
            dict(cs.UNSUPPORTED_REASONS),
        ),
        "stat_scope": _choice(
            "If the `question` asks about statistics from one game, whose statistics?",
            dict(cs.STAT_SCOPES),
        ),
        "stat": _choice("Which box score statistic does the `question` ask for?", dict(cs.STATS)),
        "aggregation": _choice(
            "Does the `question` ask for a single-game total or an average across games?",
            dict(cs.AGGREGATIONS),
        ),
    }
    for field_name, (qid, cand_field) in CANDIDATE_CHOICES.items():
        noun = NOUNS[field_name]
        criteria: dict[str, str | None] = {
            c.id: _describe(c) for c in candidates.sets[cand_field].candidates
        }
        criteria[cs.NONE_OPTION] = f"The question does not mention any {noun}."
        criteria[cs.OTHER_OPTION] = f"The question mentions a {noun}, but not any of the other listed options."
        q[qid] = _choice(f"Which {noun} does the `question` refer to?", criteria)

    teams = candidates.sets["team"].candidates
    q["team_count"] = _choice(
        "How many different NBA teams does the `question` name or refer to?",
        {"0": "No team", "1": "Exactly one team", "2": "Exactly two teams", "3+": "Three or more teams"},
    )
    q["team_unlisted"] = _noul(
        {
            "listed_teams": [_describe(c) for c in teams],
            "question": "Does the `question` refer to an NBA team that is not one of `listed_teams`?",
        },
        "The question names a team that is not in the list.",
        "Every team the question names is in the list, or it names no team.",
    )
    team_ids: dict[str, str] = {}
    for index, team in enumerate(teams):
        qid = f"team_{index}"
        team_ids[qid] = team.id
        q[qid] = _noul(
            {"team": _describe(team), "question": "Does the `question` refer to `team`?"},
            "The question names or clearly refers to this team.",
            "The question does not refer to this team.",
        )
    return q, team_ids


def _ranked(answer: dict[str, Any]) -> list[tuple[str, float]]:
    probs = answer.get("probabilities") or {}
    return sorted(((str(k), float(v)) for k, v in probs.items()), key=lambda kv: -kv[1])


def _clamp(value: float) -> float:
    return min(1.0, max(0.0, value))


def decide_choice(field_name: str, answer: dict[str, Any], t: JevThresholds) -> FieldInterpretation:
    ranked = _ranked(answer)
    if not ranked:
        raise ProviderError("invalid_response", f"no probabilities for {field_name}")
    top, p1 = ranked[0]
    confidence = _clamp(p1)
    if top == cs.NONE_OPTION:
        return FieldInterpretation(field=field_name, status="absent", confidence=confidence)
    if top == cs.OTHER_OPTION:
        return FieldInterpretation(field=field_name, status="no_matching_candidate", confidence=confidence)
    real = [k for k, p in ranked if k not in (cs.NONE_OPTION, cs.OTHER_OPTION) and p >= t.ambiguity_floor]
    if len(real) >= 2 and p1 < t.ambiguity_top_max:
        return FieldInterpretation(field=field_name, status="ambiguous", alternatives=real[:12], confidence=confidence)
    return FieldInterpretation(field=field_name, status="selected", selected=[top], confidence=confidence)


def decide_teams(answers: dict[str, Any], team_ids: dict[str, str], t: JevThresholds) -> FieldInterpretation:
    nouls = {team_ids[qid]: float(answers[qid]["noul"]) for qid in team_ids}
    unlisted = float(answers["team_unlisted"]["noul"])
    ranked = sorted(nouls.items(), key=lambda kv: -kv[1])
    selected = [tid for tid, p in ranked if p >= t.noul_yes]
    plausible = [tid for tid, p in ranked if p >= 1 - t.noul_yes]
    # How decisive the least decisive yes/no judgement was.
    confidence = _clamp(min([max(p, 1 - p) for p in [*nouls.values(), unlisted]]))

    if unlisted >= t.noul_yes:
        return FieldInterpretation(field="teams", status="no_matching_candidate", confidence=_clamp(unlisted))
    count_ranked = _ranked(answers.get("team_count", {}))
    count, count_p = count_ranked[0] if count_ranked else (None, 0.0)
    count_disagrees = count_p >= t.count_min and (
        count == "3+" or (count in ("0", "1", "2") and int(count) != len(selected))
    )
    if len(selected) > 2 or count_disagrees:
        if len(plausible) < 2:
            raise ProviderError("inconsistent_team_count")
        return FieldInterpretation(
            field="teams", status="ambiguous", alternatives=plausible[:12], confidence=confidence
        )
    if not selected:
        if len(plausible) >= 2:
            return FieldInterpretation(
                field="teams", status="ambiguous", alternatives=plausible[:12], confidence=confidence
            )
        return FieldInterpretation(field="teams", status="absent", confidence=confidence)
    return FieldInterpretation(field="teams", status="selected", selected=selected, confidence=confidence)


def decode(response: dict[str, Any], team_ids: dict[str, str], t: JevThresholds) -> dict[str, Any]:
    """Map Jev answers onto InterpreterOutput keyword arguments (without metadata)."""
    answers = response.get("answers")
    if not isinstance(answers, dict):
        raise ProviderError("invalid_response", "no answers")
    try:
        intent_ranked = _ranked(answers["intent"])
        top_intent, top_p = intent_ranked[0]
        if top_intent == cs.UNSUPPORTED_INTENT and top_p >= t.unsupported_min:
            reason = _ranked(answers["unsupported_reason"])[0][0]
            return {"outcome": "unsupported", "fields": [], "unsupported_reason": reason}

        fields = []
        if top_intent != cs.UNSUPPORTED_INTENT:
            fields.append(
                FieldInterpretation(field="intent", status="selected", selected=[top_intent], confidence=_clamp(top_p))
            )
        for name in ("stat_scope", "stat", "aggregation"):
            fields.append(decide_choice(name, answers[name], t))
        for field_name, (qid, _) in CANDIDATE_CHOICES.items():
            fields.append(decide_choice(field_name, answers[qid], t))
        fields.append(decide_teams(answers, team_ids, t))
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise ProviderError("invalid_response", f"{type(exc).__name__}: {exc}") from exc

    reliable = top_intent != cs.UNSUPPORTED_INTENT and top_p >= t.intent_min
    return {"outcome": "interpreted" if reliable else "unreliable", "fields": fields, "unsupported_reason": None}


class JevAdapter:
    """Implements `server.ask.protocols.InterpreterAdapter`."""

    name = "jev"
    provider = "typesafe"

    def __init__(
        self,
        api_key: str,
        *,
        model: str = JEV_MODEL,
        thresholds: JevThresholds | None = None,
        timeout_s: float = 10.0,
        http_client: httpx.Client | None = None,
        url: str = JEV_URL,
    ):
        if model.endswith(("-latest", "-preview")):
            raise ValueError("Pin a versioned Jev model (e.g. jev-1.13.0); aliases move")
        self.api_key = api_key
        self.model = model
        self.thresholds = thresholds or JevThresholds()
        self.timeout_s = timeout_s
        self.url = url
        self._client = http_client or httpx.Client()

    def build_payload(self, request: InterpreterInput) -> tuple[dict[str, Any], dict[str, str]]:
        questions, team_ids = build_questions(request.candidates)
        return {"model": self.model, "state": {"question": request.question}, "questions": questions}, team_ids

    def estimate_cost(self, request: InterpreterInput) -> float:
        payload, _ = self.build_payload(request)
        return 2 * estimate_max_cost(self.model, len(json.dumps(payload)), 0)

    def _metadata(self, started: float, resolved: str | None = None, usage: InterpreterUsage | None = None):
        return InterpreterMetadata(
            adapter=self.name,
            provider=self.provider,
            model=self.model,
            resolved_model=resolved,
            latency_ms=int((time.perf_counter() - started) * 1000),
            usage=usage or InterpreterUsage(provider_calls=0),
        )

    def interpret(self, request: InterpreterInput) -> InterpreterOutput:
        started = time.perf_counter()
        deadline = time.monotonic() + request.deadline_ms / 1000
        try:
            payload, team_ids = self.build_payload(request)
        except ValueError:
            return InterpreterOutput(outcome="unavailable", error_code="too_many_options", metadata=self._metadata(started))
        if 2 * estimate_max_cost(self.model, len(json.dumps(payload)), 0) > request.max_cost_usd:
            return InterpreterOutput(outcome="unavailable", error_code="budget_exceeded", metadata=self._metadata(started))

        calls = 0
        def record_attempt() -> None:
            nonlocal calls
            calls += 1

        usage = InterpreterUsage(provider_calls=0)
        resolved = None
        try:
            response = post_json(
                self._client, self.url, self.api_key, payload, timeout_s=self.timeout_s, deadline=deadline,
                on_attempt=record_attempt,
            )
            resolved = response.get("model")
            logger.info("jev requested=%s resolved=%s", self.model, resolved)
            if resolved != self.model:
                logger.warning("Jev resolved model %s differs from pinned %s", resolved, self.model)
            raw_usage = response.get("usage") or {}
            input_tokens = int(raw_usage["input_tokens"]) if raw_usage.get("input_tokens") is not None else None
            output_tokens = int(raw_usage["output_tokens"]) if raw_usage.get("output_tokens") is not None else None
            usage = InterpreterUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                provider_calls=calls,
                cost_usd=cost_usd(self.model, input_tokens, output_tokens)
                if calls == 1 and input_tokens is not None and output_tokens is not None else None,
            )
            decoded = decode(response, team_ids, self.thresholds)
        except ProviderError as exc:
            if usage.provider_calls != calls:
                usage = InterpreterUsage(provider_calls=calls)
            logger.info("jev unavailable: %s", exc)
            return InterpreterOutput(
                outcome="unavailable", error_code=exc.code, metadata=self._metadata(started, resolved, usage)
            )
        return InterpreterOutput(**decoded, metadata=self._metadata(started, resolved, usage))
