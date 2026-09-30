"""Python-authored HTTP copy and clarification choices for Ask."""

from __future__ import annotations

import datetime as dt
import re
from typing import Iterable

from server.ask import tools
from server.ask.models.candidates import Candidate, CandidateLookupResult
from server.ask.models.common import DateRange, MAX_QUESTION_LENGTH
from server.ask.models.interpreter import InterpreterOutput
from server.ask.models.request import AskContext, AskRequest, BoxscoreStatRequest, GameSearchRequest, PlayoffSeriesRequest, PostseasonSummaryRequest, PlayerSeasonStatsRequest, TeamRecordsRequest
from server.ask.models.response import (
    Clarification, ClarificationOption, Interpretation, InterpretationItem, Notice, Suggestion,
)
from server.ask.normalize import reference_date, resolve_components
from server.ask.resolution import PendingResolution, ResolutionStore, choose
from server.ask.season_scope import ambiguous_season_candidates


_TYPE = {
    "game_search": "games", "playoff_series": "series", "postseason_summary": "postseason", "player_season_stats": "season_stats", "team_records": "team_records",
}
_FIELD_LABEL = {
    "intent": "kind of question", "stat_scope": "stat scope", "stat": "statistic", "player": "player",
    "teams": "team", "date": "date", "season": "season", "round": "round", "game_number": "game number",
    "location": "location", "aggregation": "measure (season totals or per game)", "season_type": "season type (regular season or playoffs)",
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
            if field.field not in ("player", "teams", "date", "season", "round", "game_number", "location"):
                if field.field == "standings_scope" and field.status == "selected" and field.selected == ["league"]:
                    continue
                if field.status == "selected" and (field.field == "stat" or (field.field in {"aggregation", "season_type", "standings_scope"} and request is not None and request.intent in {"player_season_stats", "team_records"} and field.field in tools.REGISTRY[request.intent].fields)):
                    items.append(InterpretationItem(field=field.field, value=field.selected[0].replace("_", " ").title(), origin="question"))
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
    elif isinstance(request, (PlayoffSeriesRequest, PostseasonSummaryRequest, PlayerSeasonStatsRequest, TeamRecordsRequest)):
        season = request.season
    return Interpretation(intent=intent, detected_type=detected, items=items[:8],
                          reference_time=context.reference_time, dates=dates, season=season)


def notice(code: str, *, reason: str = "", retry_after: int | None = None,
           unsupported_reason: str | None = None, diagnostics_recorded: bool = False) -> Notice:
    copy = {
        "unsupported": ("Can't answer that one yet", "Ask covers games, boxscores, playoffs, player season stats, and regular-season records and standings. Try a full name and season such as 2023-24. Career totals, leaders and statistical splits are not supported yet."),
        "no_games": ("No games found", "No matching games were recorded for that date and team."),
        "no_record": ("No record found", "The data sources do not have a matching record for that question."),
        "player_did_not_play": ("Player did not play", "No game was recorded for that player on the selected date."),
        "service_unavailable": ("NBA data isn't responding", "Try again in a moment."),
        "interpreter_unavailable": ("Ask couldn't read that question", "Try again or add a date, team, or playoff year."),
        "budget_exhausted": ("Ask is paused for today", "The daily question budget has been reached. Try again tomorrow."),
        "rate_limited": ("Slow down a moment", "Too many requests were made. Try again shortly."),
    }
    title, message = copy[code]
    if reason == "before_records":
        message = "NBA and BAA records begin on November 1, 1946."
    elif reason == "no_games_at_location":
        message = "No games were played there on those dates."
    elif reason == "no_team_at_location":
        message = "No NBA team played home games there on those dates."
    elif code == "no_record" and reason == "recent_player_record_unverified":
        message = "No verified player record is available for that date yet."
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
    label = value.player.name if value.kind == "player" else value.team.name if value.kind == "team" else value.season if value.kind == "season" else candidate.label
    matched = candidate.matched_text
    if matched:
        match = re.search(re.escape(matched), question, re.IGNORECASE)
        if match:
            rewritten = question[:match.start()] + label + question[match.end():]
            return rewritten if len(rewritten) <= MAX_QUESTION_LENGTH else None
    rewritten = f"{question.rstrip(' ?')} {label}?"
    return rewritten if len(rewritten) <= MAX_QUESTION_LENGTH else None


def _candidate_options(field: str, reason: str, pending: PendingResolution, question: str) -> Iterable[Candidate]:
    lookup_field = "team" if field == "teams" else field
    if lookup_field not in pending.candidates.sets or reason == "no_matching_candidate":
        return []
    if field == "season" and reason == "ambiguous":
        year_options = ambiguous_season_candidates(pending.candidates, question)
        if year_options:
            return year_options[:9]
    field_result = pending.output.get_field(field)
    if field_result and field_result.status == "ambiguous":
        ids = field_result.alternatives
    elif field_result is None or field_result.status == "absent":
        ids = []
    else:
        return []
    source = pending.candidates.sets[lookup_field].candidates
    if field == "teams" and field_result and field_result.status == "ambiguous":
        alternative_spans = {candidate.span for candidate in source if candidate.id in ids}
        all_spans = {candidate.span for candidate in source}
        # The field schema cannot say whether another named team is a positive
        # participant, a correction, or a negation. Token choices are safe only
        # when this is one ambiguous mention and no other team mention exists.
        if len(alternative_spans) != 1 or None in alternative_spans or all_spans != alternative_spans:
            return []
    selected_ids = set(field_result.selected if field_result and field_result.status == "selected" else [])
    return [candidate for candidate in source if candidate.id not in selected_ids
            and (not ids or candidate.id in ids)][:9]


def clarification(field: str, reason: str, question: str, pending: PendingResolution,
                  store: ResolutionStore) -> Clarification:
    label = _FIELD_LABEL.get(field, field)
    options: list[ClarificationOption] = []
    overlong_rewrite = False
    if field in {"aggregation", "season_type"}:
        choices = ([("total", "Season totals"), ("per_game", "Per game")] if field == "aggregation"
                   else [("regular_season", "Regular season"), ("playoffs", "Playoffs")])
        pattern = (r"\b(?:season\s+totals?|totals?|per\s+game|averages?)\b" if field == "aggregation"
                   else r"\b(?:regular[ -]season|playoffs?|postseason)\b")
        base = re.sub(pattern, "", question, flags=re.IGNORECASE).rstrip(" ?")
        for value, choice_label in choices:
            chosen = choose(pending, field, closed_value=value)
            rewritten = f"{base} {choice_label.lower()}?"
            if len(rewritten) > MAX_QUESTION_LENGTH:
                overlong_rewrite = True
                continue
            options.append(ClarificationOption(id=f"{field}:{value}", label=choice_label, question=rewritten,
                                               resolution=store.issue(rewritten, chosen)))
    elif field == "date" and reason == "year_required":
        today = pending.context.reference_time.year
        for year in (today, today - 1, today + 1):
            try:
                chosen = choose(pending, "date", year=year)
            except ValueError:
                continue
            candidate = next((c for c in chosen.candidates.sets["date"].candidates
                              if c.id in (pending.output.get_field("date").selected if pending.output.get_field("date") else [])), None)
            if candidate is not None:
                if candidate.value.resolved is None:
                    continue
            elif chosen.output.extracted_date is not None:
                resolved_date = resolve_components(chosen.output.extracted_date, reference_date(chosen.context))
                if not isinstance(resolved_date, DateRange):
                    continue
            else:
                continue
            expression = candidate.matched_text if candidate else None
            match = re.search(re.escape(expression), question, re.IGNORECASE) if expression else None
            if match is None:
                # Without a known date span, a standalone games rewrite could
                # silently discard the requested player, team, or stat.
                continue
            if candidate.value.resolved.start.year != candidate.value.resolved.end.year:
                replacement = (f"{candidate.value.resolved.start.isoformat()} to "
                               f"{candidate.value.resolved.end.isoformat()}")
            else:
                replacement = f"{expression}, {year}"
            rewritten = question[:match.start()] + replacement + question[match.end():]
            if len(rewritten) > MAX_QUESTION_LENGTH:
                overlong_rewrite = True
                continue
            options.append(ClarificationOption(id=f"year:{year}", label=str(year), question=rewritten,
                                               resolution=store.issue(rewritten, chosen)))
    else:
        for candidate in _candidate_options(field, reason, pending, question):
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
    if not options and field == "teams" and reason == "ambiguous":
        scope = pending.output.get_field("stat_scope")
        if scope and scope.status == "selected" and scope.selected == ["team"]:
            hint = "Edit your question to name the team whose stat you want."
        else:
            hint = "Edit your question to make clear which teams you mean."
    if not options and field == "date" and reason in {"year_required", "range_too_long", "ambiguous"}:
        intent = pending.output.get_field("intent")
        if intent and intent.status == "selected" and intent.selected == ["boxscore_stat"]:
            prompt = "Which game date?"
            hint = ("Shorten your question, then name one game date." if overlong_rewrite
                    else "Edit your question to name one game date.")
        else:
            prompt = "Choose a specific game date"
            hint = ("Shorten your question, then name one date or a range of up to seven days." if overlong_rewrite
                    else "Edit your question to name one date or a range of up to seven days.")
    return Clarification(field=field, reason=reason, prompt=prompt, options=options[:9], hint=hint)
