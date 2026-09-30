"""OpenAI Responses adapter (`InterpreterAdapter`, name "openai_responses").

One class serves the gpt-4.1-mini baseline and the Luna models; the model is a
constructor argument. Strict structured outputs are built per question so every
candidate-backed selection is an enum of the lookup's candidate IDs and every
closed-set value is an enum from the contract. The model cannot return a name, number,
or year that candidate lookup did not offer, with one exception: when the date
candidate set has no candidates, the schema adds `extracted_date` (contract
`DateComponents`), which Python validates and resolves in the normalizer.

The Responses API reports no per-field probabilities, so `confidence` is None.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any, get_args

import httpx
from pydantic import ValidationError

from server.ask.interpreters import closed_sets as cs
from server.ask.interpreters.http import ProviderError, post_json
from server.ask.interpreters.pricing import cost_usd, estimate_max_cost
from server.ask.models.candidates import CandidateLookupResult
from server.ask.models.common import DateComponents, RelativeDate, Weekday
from server.ask.models.interpreter import (
    FieldInterpretation,
    InterpreterInput,
    InterpreterMetadata,
    InterpreterOutput,
    InterpreterUsage,
)
from server.ask.models.request import AskContext

logger = logging.getLogger(__name__)

RESPONSES_URL = "https://api.openai.com/v1/responses"
BASELINE_MODEL = "gpt-4.1-mini-2025-04-14"
LUNA_MODELS = ("gpt-6-luna", "gpt-5.6-luna")

STATUSES = ["selected", "absent", "ambiguous", "no_matching_candidate"]
# InterpreterField -> candidate set field.
CANDIDATE_FIELDS = {
    "player": "player",
    "teams": "team",
    "target_team": "team",
    "date": "date",
    "season": "season",
    "round": "round",
    "game_number": "game_number",
    "location": "location",
}
CLOSED_FIELDS = {"stat_scope": cs.STAT_SCOPES, "stat": cs.STATS, "aggregation": cs.AGGREGATIONS, "season_type": cs.SEASON_TYPES, "standings_scope": cs.STANDINGS_SCOPES}
PLACEHOLDER_ID = "__none__"

INSTRUCTIONS = """You interpret one NBA question for a basketball app. You do not answer it.
Return only IDs from `candidates` and values from the fixed options.

Intents:
{intents}

Field rules (every field has a status and a list of IDs/values):
- "selected": the question clearly refers to exactly these (1 value; teams may have 2).
- "absent": the question does not mention this detail. Leave the list empty.
- "ambiguous": the question mentions it, but two or more listed options fit. List them.
- "no_matching_candidate": the question mentions it, but no listed option matches. Leave the list empty.
- Never fill in a detail the question does not give. A missing detail is "absent".
- A missing candidate is not evidence the user meant a different listed candidate.
- Classify the request type separately from entity lookup. An unknown person or team
  in a one-game NBA stat or NBA game search is still a supported intent. Mark its
  player or teams field no_matching_candidate so the app can ask the user.
- location: select a city candidate only when the question asks for games played
  there ("games in New York"). A city used as a team name ("Boston's game",
  "New York beat Miami") is a team, not a location. Location applies to
  game_search only.
- teams lists every team the question names, opponents included. target_team selects,
  from the teams candidates, the one team whose own statistics a team-scope boxscore_stat
  question asks for ("Miami's rebounds against Boston": teams Miami and Boston,
  target_team Miami). If the question does not say which team's statistics it wants,
  target_team is ambiguous. For every other question target_team is absent.
- A game-search date range longer than seven days is still game_search. Select the
  date candidate even if its range is unresolved; Python asks the user to narrow it.
- Choose playoff_series when the request is framed as a series, matchup, or
  particular round, even if it says only a season or one team and does not yet
  identify which series. Singular or plural "series" alone does not mean all
  rounds; leave the unspecified round or opponent absent for clarification.
  Naming one team does not turn a series request into that team's whole run.
  Choose postseason_summary when the user explicitly asks for the whole
  tournament, all/every series, or a team's overall playoff run (for example,
  "how did they do in the playoffs?"). Do not widen an underspecified series
  request into a postseason summary just to satisfy required fields.
- A leader question tied to one date or game is boxscore_stat with stat_scope
  "leaders", even without a team. Several games on that date are resolved from
  data and may require a teams clarification. Use season_leaders for the
  league-wide leader(s) across one whole season.
- Season player statistics use player_season_stats, including per-game averages.
  Team regular-season records and league/conference standings use team_records.
  League-wide leaders in one season use season_leaders; select the measure only
  when the question states totals, per game or an average, otherwise leave aggregation
  absent. A player's career totals or averages, all-time leaders and a player's all-time
  rank use career_stats; career aggregation defaults to totals, so select per_game only
  for an explicit average. Career highs, team or franchise leaders remain unsupported.
  Never answer advanced metrics,
  division standings, home/away, opponent, month, date or other statistical splits as a whole season.
- season_type: select playoffs only when explicitly requested, regular_season when
  specified, otherwise absent. standings_scope: east/west only when explicitly
  requested; otherwise absent. Both apply only to season tools.
- stat and aggregation apply to boxscore_stat, player_season_stats, season_leaders and career_stats. stat_scope applies only to boxscores. Use stat "stat_line"
  when no particular statistic is named, and aggregation "per_game" when the question
  asks for an average across games.
- `page_game` true means the user is viewing one game's box score, so "this game"
  or "here" means that game, not an earlier answer. Leave date, season, round, and
  game_number absent; the app supplies the game.
- If the request is outside the intents above, set intent "unsupported" and a reason.
{date_rule}"""

DATE_RULE_CANDIDATES = "- Dates: choose among the date candidates only."
DATE_RULE_EXTRACT = """- Dates: no date candidates were found. If the question states a date, fill
  `extracted_date` with the parts it states; otherwise set it to null. Do not compute
  dates. If a calendar date has no year, set year to null; never assume a year."""


def _nullable_enum(values: list[str]) -> dict[str, Any]:
    return {"type": ["string", "null"], "enum": [*values, None]}


def _selection(values: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["status", "values"],
        "properties": {
            "status": {"type": "string", "enum": STATUSES},
            "values": {"type": "array", "items": {"type": "string", "enum": values or [PLACEHOLDER_ID]}},
        },
    }


def _date_schema() -> dict[str, Any]:
    nullable_int = {"type": ["integer", "null"]}
    props = {
        "kind": {"type": "string", "enum": ["calendar_date", "calendar_range", "relative"]},
        "year": nullable_int,
        "month": nullable_int,
        "day": nullable_int,
        "end_year": nullable_int,
        "end_month": nullable_int,
        "end_day": nullable_int,
        "relative": _nullable_enum(list(get_args(RelativeDate))),
        "weekday": _nullable_enum(list(get_args(Weekday))),
        "count": nullable_int,
    }
    return {
        "type": ["object", "null"],
        "additionalProperties": False,
        "required": list(props),
        "properties": props,
    }


def may_extract_date(candidates: CandidateLookupResult) -> bool:
    return candidates.sets["date"].status != "candidates"


def build_schema(candidates: CandidateLookupResult) -> dict[str, Any]:
    properties: dict[str, Any] = {
        "intent": {"type": "string", "enum": list(cs.INTENTS)},
        "unsupported_reason": _nullable_enum(list(cs.UNSUPPORTED_REASONS)),
    }
    for name, options in CLOSED_FIELDS.items():
        properties[name] = _selection(list(options))
    for name, cand_field in CANDIDATE_FIELDS.items():
        properties[name] = _selection([c.id for c in candidates.sets[cand_field].candidates])
    if may_extract_date(candidates):
        properties["extracted_date"] = _date_schema()
    return {"type": "object", "additionalProperties": False, "required": list(properties), "properties": properties}


def candidate_context(question: str, candidates: CandidateLookupResult,
                      context: AskContext | None = None) -> dict[str, Any]:
    listing: dict[str, Any] = {}
    for name, cand_field in CANDIDATE_FIELDS.items():
        if name == "target_team":
            continue  # selects from the `teams` listing
        cset = candidates.sets[cand_field]
        entries = []
        for c in cset.candidates:
            entry: dict[str, Any] = {"id": c.id, "label": c.label}
            if c.matched_text:
                entry["matched_text"] = c.matched_text
            if c.value.kind == "date" and c.value.resolved is not None:
                entry["dates"] = f"{c.value.resolved.start.isoformat()} to {c.value.resolved.end.isoformat()}"
            if c.source == "app_context":
                entry["from_page_context"] = True
            entries.append(entry)
        listing[name] = entries
    return {
        "question": question,
        "page_game": bool(context and context.route == "boxscore" and context.game_id),
        "candidates": listing,
        "options": {
            "stat_scope": cs.STAT_SCOPES,
            "stat": cs.STATS,
            "aggregation": cs.AGGREGATIONS,
            "season_type": cs.SEASON_TYPES,
            "standings_scope": cs.STANDINGS_SCOPES,
            "unsupported_reason": cs.UNSUPPORTED_REASONS,
        },
    }


def _field(name: str, raw: dict[str, Any], allowed: set[str]) -> FieldInterpretation | None:
    status = raw["status"]
    values = [v for v in dict.fromkeys(raw.get("values") or []) if v != PLACEHOLDER_ID]
    if any(v not in allowed for v in values):
        raise ValueError(f"{name}: value outside the offered options")
    if status == "selected":
        return FieldInterpretation(field=name, status="selected", selected=values)
    if status == "ambiguous":
        return FieldInterpretation(field=name, status="ambiguous", alternatives=values)
    return FieldInterpretation(field=name, status=status)


def decode(output: dict[str, Any], candidates: CandidateLookupResult) -> dict[str, Any]:
    """Validate structured output; returns InterpreterOutput keyword arguments."""
    intent = output["intent"]
    if intent == cs.UNSUPPORTED_INTENT:
        reason = output.get("unsupported_reason") or "other"
        return {"outcome": "unsupported", "fields": [], "unsupported_reason": reason}
    if intent not in cs.INTENTS:
        raise ValueError("unknown intent")
    fields = [FieldInterpretation(field="intent", status="selected", selected=[intent])]
    for name, options in CLOSED_FIELDS.items():
        fields.append(_field(name, output[name], set(options)))
    extracted = None
    invalid_extracted_date = False
    if may_extract_date(candidates) and output.get("extracted_date") is not None:
        try:
            extracted = DateComponents.model_validate(output["extracted_date"])
        except ValidationError:
            invalid_extracted_date = True
    for name, cand_field in CANDIDATE_FIELDS.items():
        if name == "date" and extracted is not None:
            continue  # the extracted date stands in for the (empty) date candidate set
        if name == "date" and invalid_extracted_date:
            fields.append(FieldInterpretation(field="date", status="no_matching_candidate"))
            continue
        allowed = {c.id for c in candidates.sets[cand_field].candidates}
        fields.append(_field(name, output[name], allowed))
    return {"outcome": "interpreted", "fields": fields, "unsupported_reason": None, "extracted_date": extracted}


def extract_output_text(response: dict[str, Any]) -> str:
    if response.get("status") not in (None, "completed"):
        reason = (response.get("incomplete_details") or {}).get("reason")
        raise ProviderError("incomplete_response", str(reason))
    for item in response.get("output") or []:
        if item.get("type") != "message":
            continue
        for content in item.get("content") or []:
            if content.get("type") == "refusal":
                raise ProviderError("refused")
            if content.get("type") == "output_text":
                return content.get("text") or ""
    raise ProviderError("invalid_response", "no output_text")


@dataclass(frozen=True)
class OpenAIConfig:
    model: str = BASELINE_MODEL
    # None for non-reasoning models (gpt-4.1-mini). Luna accepts none/low/medium/high/xhigh/max.
    reasoning_effort: str | None = None
    max_output_tokens: int = 2000
    timeout_s: float = 20.0


class OpenAIResponsesAdapter:
    """Implements `server.ask.protocols.InterpreterAdapter`."""

    name = "openai_responses"
    provider = "openai"

    def __init__(
        self,
        api_key: str,
        config: OpenAIConfig | None = None,
        *,
        http_client: httpx.Client | None = None,
        url: str = RESPONSES_URL,
    ):
        self.api_key = api_key
        self.config = config or OpenAIConfig()
        self.model = self.config.model
        self.url = url
        self._client = http_client or httpx.Client()

    @property
    def label(self) -> str:
        effort = f"@{self.config.reasoning_effort}" if self.config.reasoning_effort else ""
        return f"{self.config.model}{effort}"

    def build_payload(self, request: InterpreterInput) -> dict[str, Any]:
        candidates = request.candidates
        instructions = INSTRUCTIONS.format(
            intents="\n".join(f"- {k}: {v}" for k, v in cs.INTENTS.items()),
            date_rule=DATE_RULE_EXTRACT if may_extract_date(candidates) else DATE_RULE_CANDIDATES,
        )
        payload: dict[str, Any] = {
            "model": self.config.model,
            "input": [
                {"role": "developer", "content": instructions},
                {"role": "user", "content": json.dumps(candidate_context(request.question, candidates, request.context))},
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "ask_interpretation",
                    "strict": True,
                    "schema": build_schema(candidates),
                }
            },
            "max_output_tokens": self.config.max_output_tokens,
            "store": False,
        }
        if self.config.reasoning_effort is not None:
            payload["reasoning"] = {"effort": self.config.reasoning_effort}
        return payload

    def estimate_cost(self, request: InterpreterInput) -> float:
        payload = self.build_payload(request)
        return 2 * estimate_max_cost(self.config.model, len(json.dumps(payload)), self.config.max_output_tokens)

    def _metadata(self, started: float, resolved: str | None = None, usage: InterpreterUsage | None = None):
        return InterpreterMetadata(
            adapter="openai_responses",
            provider=self.provider,
            model=self.config.model,
            resolved_model=resolved,
            latency_ms=int((time.perf_counter() - started) * 1000),
            usage=usage or InterpreterUsage(provider_calls=0),
        )

    def interpret(self, request: InterpreterInput) -> InterpreterOutput:
        started = time.perf_counter()
        deadline = time.monotonic() + request.deadline_ms / 1000
        payload = self.build_payload(request)
        estimate = 2 * estimate_max_cost(self.config.model, len(json.dumps(payload)), self.config.max_output_tokens)
        if estimate > request.max_cost_usd:
            return InterpreterOutput(outcome="unavailable", error_code="budget_exceeded", metadata=self._metadata(started))

        calls = 0
        def record_attempt() -> None:
            nonlocal calls
            calls += 1

        usage = InterpreterUsage(provider_calls=0)
        resolved = None
        try:
            response = post_json(
                self._client, self.url, self.api_key, payload,
                timeout_s=self.config.timeout_s, deadline=deadline, on_attempt=record_attempt,
            )
            resolved = response.get("model")
            logger.info("openai requested=%s resolved=%s", self.config.model, resolved)
            raw_usage = response.get("usage") or {}
            input_tokens = int(raw_usage["input_tokens"]) if raw_usage.get("input_tokens") is not None else None
            output_tokens = int(raw_usage["output_tokens"]) if raw_usage.get("output_tokens") is not None else None
            raw_cached = (raw_usage.get("input_tokens_details") or {}).get("cached_tokens")
            cached = int(raw_cached) if raw_cached is not None else None
            usage = InterpreterUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cached_input_tokens=cached,
                provider_calls=calls,
                cost_usd=cost_usd(self.config.model, input_tokens, output_tokens, cached or 0)
                if calls == 1 and input_tokens is not None and output_tokens is not None else None,
            )
            text = extract_output_text(response)
        except ProviderError as exc:
            if usage.provider_calls != calls:
                usage = InterpreterUsage(provider_calls=calls)
            logger.info("openai unavailable: %s", exc)
            return InterpreterOutput(
                outcome="unavailable", error_code=exc.code, metadata=self._metadata(started, resolved, usage)
            )
        try:
            decoded = decode(json.loads(text), candidates=request.candidates)
            return InterpreterOutput(**decoded, metadata=self._metadata(started, resolved, usage))
        except (ValueError, KeyError, TypeError, ValidationError) as exc:
            # Ran and was billed, but the output is not usable: a fallback-eligible failure.
            logger.info("openai output rejected: %s", exc)
            return InterpreterOutput(
                outcome="unreliable", error_code="invalid_output", metadata=self._metadata(started, resolved, usage)
            )
