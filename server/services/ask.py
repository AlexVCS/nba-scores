"""Coordinate one interpretation call and deterministic basketball retrieval."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from collections import deque
from datetime import datetime, timezone
import hashlib
import json
import logging
import os
import re
import threading
import time
from zoneinfo import ZoneInfo

from server.models.ask_response import AskResponse
from server.services import ask_parser
from server.services.ask_scope import unsupported_scope_message
from server.services.ask_limits import (
    Budget, BudgetLimitError, BudgetUnavailable, RateLimiter, RateLimitError, TTLCache,
)

logger = logging.getLogger(__name__)
_parses = TTLCache(max_entries=256)
_answers = TTLCache(max_entries=256)
_provider_health = TTLCache(max_entries=8)
_parse_lock = threading.Lock()
_rate = RateLimiter()
_workers = ThreadPoolExecutor(max_workers=2, thread_name_prefix="nba-ask")
_slots = threading.BoundedSemaphore(2)
_unsupported = deque(maxlen=200)
_unsupported_lock = threading.Lock()
_RETENTION_SECONDS = 7 * 86400


def _response(status, message, interpretation=None):
    return {"status": status, "message": message, "items": [],
            "interpretation": interpretation or []}


def _interpretation_labels(interpretation, resolved=None):
    """Return labels copied or deterministically derived from the validated parse."""
    from server.services.ask_basketball import STAT_KEYS, STAT_LABELS

    labels = [mention.text for mention in interpretation.mentions]
    if interpretation.operation == "leaders":
        labels.append("Game leaders")
    labels.extend(
        STAT_LABELS[STAT_KEYS[stat]] if stat in STAT_KEYS else stat.replace("_", " ").capitalize()
        for stat in interpretation.statistics
    )
    dates = [expression.text for expression in interpretation.date_expressions]
    round_label = interpretation.round_mention
    if round_label:
        season_year = next((text for text in dates if re.fullmatch(r"\d{4}(?:\s+playoffs)?", text, re.I)), None)
        if season_year and round_label.casefold() in {"finals", "nba finals", f"{season_year} finals".casefold(), f"{season_year} nba finals".casefold()}:
            year = re.search(r"\d{4}", season_year).group()
            round_label = f"{year} NBA Finals"
            dates.remove(season_year)
        labels.extend(dates)
        labels.append(round_label)
    else:
        labels.extend(dates)
    if interpretation.game_number is not None:
        labels.append(f"Game {interpretation.game_number}")
    ambiguities = interpretation.ambiguities
    if (resolved and getattr(resolved, "intent", None) == "game_search"
            and getattr(resolved, "team_ids", ())):
        ambiguities = [item for item in ambiguities
                       if item.field.casefold().replace('_', ' ') not in {"team", "team name"}]
    labels.extend(f"[which {item.field.replace('_', ' ')}?]" for item in ambiguities)
    return list(dict.fromkeys(labels))


def _parser_unavailable():
    return _response("unavailable", "Question interpretation is unavailable right now. You can still browse games by date.")


def _record_unsupported(question, interpretation=None):
    # Bounded, expiring process-local logs. No IPs, API keys, or raw questions.
    # Keep the requested operations and missing fields to guide supported scope.
    now = time.time()
    with _unsupported_lock:
        while _unsupported and _unsupported[0]["expires_at"] <= now:
            _unsupported.popleft()
        _unsupported.append({
            "question_hash": hashlib.sha256(question.encode()).hexdigest(),
            "intent": interpretation.intent if interpretation else "unsupported",
            "operation": interpretation.operation if interpretation else None,
            "statistics": interpretation.statistics if interpretation else [],
            "missing_fields": [item.field for item in interpretation.ambiguities] if interpretation else [],
            "expires_at": now + _RETENTION_SECONDS,
        })


def unsupported_request_log():
    """Internal diagnostics only. No public route exposes question logs."""
    with _unsupported_lock:
        now = time.time()
        while _unsupported and _unsupported[0]["expires_at"] <= now:
            _unsupported.popleft()
        return list(_unsupported)


def invalidate_ask_caches():
    """Call after source corrections; ASK_CACHE_VERSION also invalidates keys."""
    _parses.clear()
    _answers.clear()
    _provider_health.clear()


def _answer(question, now):
    scope_message = unsupported_scope_message(question)
    if scope_message:
        _record_unsupported(question)
        return _response("unsupported", scope_message)

    from server.services.ask_basketball import resolve_request, AskResolutionError
    from server.services.ask_data import retrieve_answer

    model = os.getenv("ASK_PARSER_MODEL", ask_parser.DEFAULT_MODEL)
    payload = ask_parser.build_request(question, model)
    # Prompt/schema, provider, model, and NY calendar day isolate parse caches.
    identity = dict(payload)
    identity.pop("input")
    identity["provider"] = os.getenv("ASK_PARSER_PROVIDER", "openai")
    identity["endpoint"] = os.getenv("OPENAI_RESPONSES_URL", "https://api.openai.com/v1/responses")
    fingerprint = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    version = os.getenv("ASK_CACHE_VERSION", "1")
    parse_key = (version, fingerprint, now.astimezone(ZoneInfo("America/New_York")).date().isoformat(), " ".join(question.casefold().split()))
    with _parse_lock:
        parsed = _parses.get(parse_key)
        if parsed is None:
            if _provider_health.get(fingerprint):
                return _parser_unavailable()
            budget = Budget()
            reserved = budget.reserve(payload, model)
            try:
                parsed = ask_parser.parse_ask(question)
            except ask_parser.AskParserUnavailable as error:
                # An uncertain provider failure may still be billable. Keep reservation.
                _provider_health.put(fingerprint, True, ttl=60)
                logger.warning("Ask interpretation provider unavailable code=%s", error.code or "unknown")
                return _parser_unavailable()
            except ask_parser.AskParserInvalidResponse:
                return _response("needs_clarification", "Please rephrase your question and include a date or playoff year.")
            budget.settle(reserved, parsed.metadata.usage)
            _parses.put(parse_key, parsed, ttl=3600)
            logger.info("Ask parser model=%s input_tokens=%s output_tokens=%s latency_ms=%s", model,
                        parsed.metadata.usage.input_tokens, parsed.metadata.usage.output_tokens, parsed.metadata.latency_ms)

    interpretation = parsed.interpretation
    interpretation_labels = _interpretation_labels(interpretation)
    if interpretation.intent in {"unsupported", "needs_clarification"}:
        _record_unsupported(question, interpretation)
    try:
        resolved = resolve_request(interpretation.model_dump(), now, ask_parser._load_aliases())
    except AskResolutionError as error:
        return _response(error.status, error.message, interpretation_labels)
    interpretation_labels = _interpretation_labels(interpretation, resolved)
    key = (version, resolved.normalized_key)
    answer = _answers.get(key)
    if answer is not None:
        return {**answer, "interpretation": interpretation_labels}
    try:
        answer, completed = retrieve_answer(resolved)
    except AskResolutionError as error:
        return _response(error.status, error.message, interpretation_labels)
    # Validate Python-authored response, including local route shape, before caching.
    answer = AskResponse.model_validate(answer).model_dump()
    if answer["status"] == "ok":
        _answers.put(key, answer, ttl=None if completed else 30)
    elif answer["status"] == "not_found":
        _answers.put(key, answer, ttl=30)
    return {**answer, "interpretation": interpretation_labels}


def answer_question(question: str, client_id: str, now: datetime | None = None):
    """Bound queue depth and response time even when an NBA service is slow."""
    _rate.check(client_id)
    if not _slots.acquire(blocking=False):
        raise RateLimitError("Search is busy. Try again shortly.")
    try:
        future = _workers.submit(_answer, question, now or datetime.now(timezone.utc))
    except Exception:
        _slots.release()
        raise
    future.add_done_callback(lambda _future: _slots.release())
    try:
        return future.result(timeout=20)
    except FutureTimeout:
        # The worker retains its slot until it stops; timed-out requests cannot
        # create an unbounded queue or an unbounded number of upstream calls.
        return _response("unavailable", "This search took too long. Please try again shortly.")
    except BudgetLimitError:
        raise
    except BudgetUnavailable:
        logger.warning("Ask budget state unavailable")
        return _parser_unavailable()
