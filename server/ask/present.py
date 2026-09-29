"""Python-authored HTTP copy and clarification choices for Ask."""

from __future__ import annotations

import datetime as dt
import re
from typing import Iterable

from server.ask.models.candidates import Candidate, CandidateLookupResult
from server.ask.models.common import DateRange, MAX_QUESTION_LENGTH
from server.ask.models.interpreter import InterpreterOutput
from server.ask.models.request import AskContext, AskRequest, BoxscoreStatRequest, GameSearchRequest, PlayoffSeriesRequest, PostseasonSummaryRequest
from server.ask.models.response import (
    Clarification, ClarificationOption, Interpretation, InterpretationItem, Notice, Suggestion,
)
from server.ask.resolution import PendingResolution, ResolutionStore, choose


_TYPE = {
    "game_search": "games", "playoff_series": "series", "postseason_summary": "postseason",
}
_FIELD_LABEL = {
    "intent": "kind of question", "stat_scope": "stat scope", "stat": "statistic", "player": "player",
    "teams": "team", "date": "date", "season": "season", "round": "round", "game_number": "game number",
}


def interpretation(output: InterpreterOutput | None, candidates: CandidateLookupResult | None,
                   context: AskContext, request: AskRequest | None = None) -> Interpretation:
    intent = request.intent if request else None
    detected = _TYPE.get(intent)
    if isinstance(request, BoxscoreStatRequest):
        detected = {"player": "player_stat", "team": "team_stat", "leaders": "stat_leaders"}[request.scope]
    items: list[InterpretationItem] = []
    if output is not None and candidates is not None:
        for field in output.fields:
            if field.field not in ("player", "teams", "date", "season", "round", "game_number"):
                if field.field == "stat" and field.status == "selected":
                    items.append(InterpretationItem(field="stat", value=field.selected[0].replace("_", " ").title(), origin="question"))
                continue
            ids = field.selected if field.status == "selected" else field.alternatives if field.status == "ambiguous" else []
            for value in ids[:2]:
                candidate = candidates.by_id(value)
                if candidate is None:
                    continue
                origin = "context" if candidate.source == "app_context" else "question"
                display_field = "team" if field.field == "teams" and len(ids) == 1 else field.field
                items.append(InterpretationItem(
                    field=display_field, value=candidate.label[:120], expression=candidate.matched_text,
                    origin=origin, status="ambiguous" if field.status == "ambiguous" else "resolved",
                    match_count=len(ids) if field.status == "ambiguous" and len(ids) >= 2 else None,
                    team_id=candidate.value.team.team_id if candidate.value.kind == "team" else None,
                    player_id=candidate.value.player.player_id if candidate.value.kind == "player" else None,
                ))
    dates: DateRange | None = None
    season = None
    if isinstance(request, GameSearchRequest):
        dates = request.dates
    elif isinstance(request, BoxscoreStatRequest):
        if request.game.date:
            dates = DateRange(start=request.game.date, end=request.game.date)
        season = request.game.season
    elif isinstance(request, (PlayoffSeriesRequest, PostseasonSummaryRequest)):
        season = request.season
    return Interpretation(intent=intent, detected_type=detected, items=items[:8],
                          reference_time=context.reference_time, dates=dates, season=season)


def notice(code: str, *, reason: str = "", retry_after: int | None = None,
           unsupported_reason: str | None = None, diagnostics_recorded: bool = False) -> Notice:
    copy = {
        "unsupported": ("Can't answer that one yet", "Ask covers games, boxscores, playoff series, and postseason results."),
        "no_games": ("No games found", "No matching games were recorded for that date and team."),
        "no_record": ("No record found", "NBA records do not have that game or series."),
        "player_did_not_play": ("Player did not play", "No game was recorded for that player on the selected date."),
        "service_unavailable": ("NBA data isn't responding", "Try again in a moment."),
        "interpreter_unavailable": ("Ask couldn't read that question", "Try again or add a date, team, or playoff year."),
        "budget_exhausted": ("Ask is paused for today", "The daily question budget has been reached. Try again tomorrow."),
        "rate_limited": ("Slow down a moment", "Too many requests were made. Try again shortly."),
    }
    title, message = copy[code]
    if reason == "before_records":
        message = "NBA and BAA records begin on November 1, 1946."
    return Notice(code=code, title=title, message=message, retryable=code in {
        "service_unavailable", "interpreter_unavailable", "rate_limited"},
        retry_after_seconds=retry_after, unsupported_reason=unsupported_reason,
        diagnostics_recorded=diagnostics_recorded)


def suggestions(request: AskRequest) -> list[Suggestion]:
    """Standalone next questions that contain no inferred participant or result."""
    if isinstance(request, GameSearchRequest):
        next_day = request.dates.end + dt.timedelta(days=1)
        return [Suggestion(question=f"Games on {next_day.isoformat()}?", category="games")]
    if isinstance(request, BoxscoreStatRequest) and request.game.date:
        return [Suggestion(question=f"Games on {request.game.date.isoformat()}?", category="games")]
    if isinstance(request, (PlayoffSeriesRequest, PostseasonSummaryRequest)):
        year = int(request.season[:4]) + 1
        return [Suggestion(question=f"{year} NBA postseason results?", category="postseason")]
    return []


def _rewrite(question: str, candidate: Candidate) -> str | None:
    value = candidate.value
    label = value.player.name if value.kind == "player" else value.team.name if value.kind == "team" else candidate.label
    matched = candidate.matched_text
    if matched:
        match = re.search(re.escape(matched), question, re.IGNORECASE)
        if match:
            rewritten = question[:match.start()] + label + question[match.end():]
            return rewritten if len(rewritten) <= MAX_QUESTION_LENGTH else None
    rewritten = f"{question.rstrip(' ?')} {label}?"
    return rewritten if len(rewritten) <= MAX_QUESTION_LENGTH else None


def _candidate_options(field: str, reason: str, pending: PendingResolution) -> Iterable[Candidate]:
    lookup_field = "team" if field == "teams" else field
    if lookup_field not in pending.candidates.sets or reason == "no_matching_candidate":
        return []
    field_result = pending.output.get_field(field)
    ids = field_result.alternatives if field_result and field_result.status == "ambiguous" else []
    source = pending.candidates.sets[lookup_field].candidates
    return [candidate for candidate in source if not ids or candidate.id in ids][:9]


def clarification(field: str, reason: str, question: str, pending: PendingResolution,
                  store: ResolutionStore) -> Clarification:
    label = _FIELD_LABEL.get(field, field)
    options: list[ClarificationOption] = []
    overlong_rewrite = False
    if field == "date" and reason == "year_required":
        today = pending.context.reference_time.year
        for year in (today, today - 1, today + 1):
            try:
                chosen = choose(pending, "date", year=year)
            except ValueError:
                continue
            candidate = next((c for c in chosen.candidates.sets["date"].candidates
                              if c.id in (pending.output.get_field("date").selected if pending.output.get_field("date") else [])), None)
            expression = candidate.matched_text if candidate else None
            if expression and expression in question:
                rewritten = question.replace(expression, f"{expression}, {year}", 1)
            else:
                rewritten = f"{question.rstrip(' ?')} in {year}?"
            if len(rewritten) > MAX_QUESTION_LENGTH:
                overlong_rewrite = True
                continue
            options.append(ClarificationOption(id=f"year:{year}", label=str(year), question=rewritten,
                                               resolution=store.issue(rewritten, chosen)))
    else:
        for candidate in _candidate_options(field, reason, pending):
            try:
                chosen = choose(pending, field, candidate_id=candidate.id)
            except ValueError:
                continue
            rewritten = _rewrite(question, candidate)
            if rewritten is None:
                overlong_rewrite = True
                continue
            options.append(ClarificationOption(
                id=candidate.id, label=candidate.label[:80], question=rewritten,
                team=candidate.value.team if candidate.value.kind == "team" else None,
                player_id=candidate.value.player.player_id if candidate.value.kind == "player" else None,
                resolution=store.issue(rewritten, chosen),
                spoiler=bool(candidate.field == "team" and any(
                    f.field == "round" and f.status == "selected" for f in pending.output.fields)
                    and candidate.source == "app_context"),
            ))
    prompt = f"Which {label}?" if reason in {"ambiguous", "year_required"} else f"Add a {label}"
    if reason == "year_required":
        prompt = "Which year?"
    hint = ("Shorten your question, then add a more specific name or date." if overlong_rewrite
            else "Edit your question to include a more specific name or date.") if not options else None
    return Clarification(field=field, reason=reason, prompt=prompt, options=options[:9], hint=hint)
