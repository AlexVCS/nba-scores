"""Bounded, single-call natural-language request parser."""

from __future__ import annotations

import json
import os
import re
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

import requests

from server.models.ask import AskInterpretation, AskParseMetadata, AskParseResult, AskParseUsage


class AskParserError(RuntimeError):
    """Base class for parser failures."""


class AskParserUnavailable(AskParserError):
    def __init__(self, message: str, usage: AskParseUsage | None = None, code: str | None = None):
        super().__init__(message)
        self.usage = usage
        self.code = code


class AskParserInvalidResponse(AskParserError):
    pass


MAX_INPUT_CHARS = 300
MAX_OUTPUT_TOKENS = 500
REQUEST_TIMEOUT_SECONDS = 8.0
DEFAULT_MODEL = "gpt-4.1-mini-2025-04-14"
_ALIASES_PATH = Path(__file__).parents[1] / "constants" / "ask_team_aliases.json"


@lru_cache(maxsize=1)
def _load_aliases() -> dict[str, list[str]]:
    with _ALIASES_PATH.open(encoding="utf-8") as aliases_file:
        return json.load(aliases_file)


def _configured_api_key() -> str | None:
    """Read the process environment, with the server-local dotenv fallback."""
    key = os.getenv("OPENAI_API_KEY")
    if key:
        return key
    dotenv_path = Path(__file__).parents[1] / ".env"
    try:
        for line in dotenv_path.read_text(encoding="utf-8").splitlines():
            name, separator, value = line.partition("=")
            if separator and name.strip() == "OPENAI_API_KEY":
                return value.strip().strip('"\'') or None
    except OSError:
        return None
    return None


@lru_cache(maxsize=1)
def _schema() -> dict[str, Any]:
    """Return a strict JSON schema accepted by the Responses API."""
    statistics = [
        "points", "rebounds", "assists", "steals", "blocks", "turnovers", "fouls", "minutes",
        "field_goals", "three_pointers", "free_throws", "field_goal_percentage",
        "three_point_percentage", "free_throw_percentage", "plus_minus", "quarter_scores",
    ]
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "intent": {"type": "string", "enum": ["game_search", "boxscore_stats", "playoff_series", "postseason_summary", "unsupported", "needs_clarification"]},
            "operation": {"type": ["string", "null"], "enum": ["list", "player_stats", "team_stats", "leaders", "series_result", "summary", None]},
            "mentions": {"type": "array", "items": {"type": "object", "additionalProperties": False, "properties": {"text": {"type": "string"}, "kind": {"type": "string", "enum": ["team", "player", "unknown"]}}, "required": ["text", "kind"]}},
            "date_expressions": {"type": "array", "items": {"type": "object", "additionalProperties": False, "properties": {"text": {"type": "string"}, "kind": {"type": "string", "enum": ["calendar_date", "season", "relative", "range", "unknown"]}}, "required": ["text", "kind"]}},
            "round_mention": {"type": ["string", "null"]},
            "game_number": {"type": ["integer", "null"], "minimum": 1, "maximum": 7},
            "statistics": {"type": "array", "items": {"type": "string", "enum": statistics}},
            "ambiguities": {"type": "array", "items": {"type": "object", "additionalProperties": False, "properties": {"field": {"type": "string"}, "reason": {"type": "string"}}, "required": ["field", "reason"]}},
            "unsupported_reason": {"type": ["string", "null"]}
        },
        "required": ["intent", "operation", "mentions", "date_expressions", "round_mention", "game_number", "statistics", "ambiguities", "unsupported_reason"]
    }


@lru_cache(maxsize=1)
def _instructions() -> str:
    aliases = json.dumps(_load_aliases(), ensure_ascii=False, separators=(",", ":"))
    return (
        "Interpret one NBA natural-language request. Return only the supplied JSON schema. "
        "Supported intents are game_search, boxscore_stats, playoff_series, and postseason_summary. "
        "Set operation to list, player_stats, team_stats, leaders, series_result, or summary. "
        "Use unsupported for career stats, broad historical comparisons, non-NBA requests, or requests "
        "outside this product, predictions, season player averages, regular-season team win/loss totals or standings, season-wide biggest/smallest win or loss lookups, news, and conversational follow-ups. "
        "For unsupported, use null operation/round_mention/game_number, empty mentions/date_expressions/statistics/ambiguities, "
        "and a short unsupported_reason category. For needs_clarification use operation null, copy known selectors, "
        "and report missing fields using team, player, date, season, game, or statistic. "
        "Game search requires a date or week, with optional teams; 'last night' is a usable relative date. "
        "Player boxscore statistics require a player name and a single calendar date; a team is optional. Team totals and game leaders require a team and date. Alternatively use a playoff year, round or matchup, and game number. "
        "Use player_stats for one named player's stats, team_stats for team totals, leaders for the highest value of one stat. "
        "For 'How many points did Shai Gilgeous-Alexander score on January 2, 2024?', use boxscore_stats/player_stats, "
        "mention only Shai Gilgeous-Alexander as player, date January 2, 2024 as calendar_date, statistic points, and no ambiguities. "
        "Never infer a player's team; Python finds the player's game on the requested date. "
        "Use playoff_series/series_result for a series result with a year and matchup or round; "
        "use postseason_summary/summary for a whole postseason or team playoff run. "
        "Ask for clarification when only a raw game ID is given; v1 resolves games from dates and playoff selectors. "
        "A historical date or season is not unsupported just because records may be missing; Python checks availability. "
        "Use needs_clarification when a required detail is absent or ambiguous. "
        "Copy team and player mentions exactly as the user wrote them. Extract date language verbatim. "
        "Extract an explicit playoff round phrase into round_mention, and an explicit series game number "
        "such as game 4 into game_number. Leave either null when absent. Never infer either value. "
        "For example, 'Who led Celtics in scoring in game 4 of 2024 Finals?' has operation leaders, "
        "round_mention 'Finals', date_expressions [{text: '2024', kind: 'season'}], game_number 4, and statistic points. "
        "Keep the year separate from the round phrase. Do not include round or season phrases among team/player mentions. "
        "Never resolve IDs, URLs, dates, seasons, or relative dates. Never invent a statistic. "
        "A schema-valid guess is a failure. Team alias hints: " + aliases
    )


def _response_json(body: dict[str, Any]) -> Any:
    text = body.get("output_text")
    if not isinstance(text, str):
        for item in body.get("output", []):
            for content in item.get("content", []):
                if content.get("type") in {"output_text", "text"} and isinstance(content.get("text"), str):
                    text = content["text"]
                    break
    if not isinstance(text, str):
        raise AskParserInvalidResponse("Parser response did not contain JSON text")
    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        raise AskParserInvalidResponse("Parser response was not valid JSON") from error


def _validate_copied_selectors(query: str, interpretation: AskInterpretation) -> None:
    """Reject selectors the model invented instead of quoting from the query."""
    source = re.sub(r"\s+", " ", query).strip().casefold()
    selectors = [mention.text for mention in interpretation.mentions]
    selectors.extend(expression.text for expression in interpretation.date_expressions)
    if interpretation.round_mention:
        selectors.append(interpretation.round_mention)
    for selector in selectors:
        normalized = re.sub(r"\s+", " ", selector).strip().casefold()
        if not normalized or normalized not in source:
            raise AskParserInvalidResponse("Parser returned a selector absent from the query")
    if interpretation.game_number is not None:
        ordinal_values = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6, "seventh": 7}
        explicit_numbers = {int(value) for value in re.findall(r"\b(?:game|match)\s*(?:number\s*)?#?\s*([1-7])\b", source)}
        explicit_numbers.update(ordinal_values[value] for value in re.findall(r"\b(first|second|third|fourth|fifth|sixth|seventh)\s+(?:game|match)\b", source))
        if interpretation.game_number not in explicit_numbers:
            raise AskParserInvalidResponse("Parser returned a game number absent from the query")


def build_request(query: str, model: str | None = None) -> dict[str, Any]:
    """Build the bounded provider payload without making a network request."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must not be empty")
    if len(query) > MAX_INPUT_CHARS:
        raise ValueError(f"query exceeds {MAX_INPUT_CHARS} characters")
    return {
        "model": model or os.getenv("ASK_PARSER_MODEL", DEFAULT_MODEL),
        "instructions": _instructions(),
        "input": query.strip(),
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "store": False,
        "text": {"format": {"type": "json_schema", "name": "nba_ask_interpretation", "strict": True, "schema": _schema()}},
    }


def parse_ask(query: str) -> AskParseResult:
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must not be empty")
    if len(query) > MAX_INPUT_CHARS:
        raise ValueError(f"query exceeds {MAX_INPUT_CHARS} characters")

    provider = os.getenv("ASK_PARSER_PROVIDER", "openai")
    model = os.getenv("ASK_PARSER_MODEL", DEFAULT_MODEL)
    api_key = _configured_api_key() if provider == "openai" else os.getenv("ASK_API_KEY")
    if provider not in {"openai", "openai_compatible"}:
        raise AskParserUnavailable(f"Unsupported parser provider: {provider}")
    if not api_key:
        raise AskParserUnavailable("OPENAI_API_KEY is not configured")

    started = time.perf_counter()
    try:
        response = requests.post(
            os.getenv("OPENAI_RESPONSES_URL", "https://api.openai.com/v1/responses"),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=build_request(query, model),
            timeout=REQUEST_TIMEOUT_SECONDS,
            allow_redirects=False,
        )
        try:
            response.raise_for_status()
        except requests.HTTPError as error:
            code = None
            try:
                error_body = response.json()
                candidate = (error_body.get("error") or {}).get("code")
                if candidate in {"credit_balance_exhausted", "insufficient_quota", "invalid_api_key", "model_not_found", "rate_limit_exceeded"}:
                    code = candidate
                raw_usage = error_body.get("usage") or {}
                usage = AskParseUsage(input_tokens=raw_usage.get("input_tokens"), output_tokens=raw_usage.get("output_tokens"), total_tokens=raw_usage.get("total_tokens"))
            except (ValueError, AttributeError, TypeError):
                usage = None
            raise AskParserUnavailable("Parser provider rejected the request", usage=usage, code=code) from error
    except requests.RequestException as error:
        raise AskParserUnavailable("Parser provider request failed") from error

    try:
        body = response.json()
        if not isinstance(body, dict):
            raise AskParserInvalidResponse("Parser response was not an object")
        if body.get("status") not in (None, "completed"):
            raise AskParserInvalidResponse("Parser response did not complete")
        interpretation = AskInterpretation.model_validate(_response_json(body))
        _validate_copied_selectors(query, interpretation)
    except (ValueError, TypeError, AttributeError) as error:
        if isinstance(error, AskParserInvalidResponse):
            raise
        raise AskParserInvalidResponse("Parser response could not be validated") from error
    usage_body = body.get("usage") or {}
    usage = AskParseUsage(input_tokens=usage_body.get("input_tokens"), output_tokens=usage_body.get("output_tokens"), total_tokens=usage_body.get("total_tokens"))
    return AskParseResult(interpretation=interpretation, metadata=AskParseMetadata(provider=provider, model=model, latency_ms=round((time.perf_counter() - started) * 1000), usage=usage))


parse_query = parse_ask
