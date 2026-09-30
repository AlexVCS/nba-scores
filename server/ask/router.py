"""Bounded HTTP entry points for Ask."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Query, Request

from server.ask.config import AskConfig
from server.ask.limits import AskBusy, AskLimits, AskRateLimited, AskTimeout
from server.ask.models.response import AskQuery, AskResponse, AskSuggestResponse
from server.ask.pipeline import AskPipeline
from server.ask.present import notice
from server.ask.suggest import AskSuggester

router = APIRouter()
logger = logging.getLogger(__name__)
_config = AskConfig.from_env()
_pipeline = AskPipeline(_config)
_suggester = AskSuggester(cache=_pipeline.cache)
_limits = AskLimits(_config.per_client_per_minute, _config.per_worker_per_minute, _config.max_in_flight)
_suggest_limits = AskLimits(_config.suggest_per_client_per_minute, _config.suggest_per_worker_per_minute,
                            _config.suggest_max_in_flight)


def _client_id(request: Request) -> str:
    # The transport peer is trusted; a caller-supplied forwarded header is not.
    return request.client.host if request.client else "unknown"


@router.post("/ask", response_model=AskResponse)
def ask(query: AskQuery, request: Request) -> AskResponse:
    if not _config.enabled:
        return _pipeline.disabled(query.question)
    try:
        _limits.check_rate(_client_id(request))
        return _limits.run_bounded(lambda: _pipeline.answer(query), _config.deadline_seconds)
    except AskRateLimited:
        return _pipeline._response(query.question, "unavailable", _pipeline._info(),
                                   notice=notice("rate_limited", retry_after=60))
    except (AskBusy, AskTimeout):
        return _pipeline._response(query.question, "unavailable", _pipeline._info(),
                                   notice=notice("service_unavailable"))
    except Exception as error:
        logger.error("Ask request failed: %s", type(error).__name__)
        return _pipeline._response(query.question, "unavailable", _pipeline._info(),
                                   notice=notice("service_unavailable"))


@router.get("/ask/suggest", response_model=AskSuggestResponse)
def suggest(request: Request, q: str = Query(default="", max_length=300), hidden: bool = True) -> AskSuggestResponse:
    if not _config.enabled:
        return AskSuggestResponse(query=q)
    try:
        _suggest_limits.check_rate(_client_id(request))
        return _suggest_limits.run_bounded(lambda: _suggester.suggest(q, hidden), min(3.0, _config.deadline_seconds))
    except (AskBusy, AskRateLimited, AskTimeout):
        return AskSuggestResponse(query=q)
    except Exception as error:
        logger.error("Ask suggestion failed: %s", type(error).__name__)
        return AskSuggestResponse(query=q)
