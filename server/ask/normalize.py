"""RequestNormalizer: validate an InterpreterOutput and build an AskRequest. Pure; no I/O.

Rules:
- Selected candidate IDs must exist in the lookup result and belong to the field's set;
  closed-set values must be contract enum values. Anything else is `invalid`.
- `ambiguous` / `no_matching_candidate` on a field the request uses, or a missing
  required field, is a clarification; never a default.
- A date candidate without a resolved range (or an extracted date without a year) is a
  `year_required` / `range_too_long` clarification. The year is never defaulted.
- A boxscore request with `aggregation="per_game"` is unsupported (`multi_game_average`).
- `extracted_date` is used only when the date candidate set had no candidates.
"""

from __future__ import annotations

import datetime as dt
from typing import Any, get_args
from zoneinfo import ZoneInfo

from pydantic import ValidationError

from server.ask.models.candidates import CandidateLookupResult
from server.ask.models.common import (
    MAX_GAME_SEARCH_DAYS,
    NEW_YORK_TZ,
    NON_LEADER_STATS,
    Aggregation,
    DateComponents,
    DateRange,
    Intent,
    Stat,
    StatScope,
)
from server.ask.models.interpreter import FieldInterpretation, InterpreterOutput, NormalizationResult
from server.ask.models.request import (
    AskContext,
    BoxscoreStatRequest,
    GameSearchRequest,
    GameSelector,
    PlayoffSeriesRequest,
    PostseasonSummaryRequest,
    StatSelection,
)

CANDIDATE_SET_FOR = {
    "player": "player",
    "teams": "team",
    "date": "date",
    "season": "season",
    "round": "round",
    "game_number": "game_number",
    "location": "location",
}
CLOSED_VALUES = {
    "intent": set(get_args(Intent)),
    "stat_scope": set(get_args(StatScope)),
    "stat": set(get_args(Stat)),
    "aggregation": set(get_args(Aggregation)),
}

# Fields each intent reads. A field outside this set is ignored, so a stray value on an
# irrelevant field never changes the request (and never blocks it).
RELEVANT_FIELDS: dict[str, frozenset[str]] = {
    "game_search": frozenset({"date", "teams", "location"}),
    "boxscore_stat": frozenset(
        {"stat_scope", "stat", "aggregation", "player", "teams", "date", "season", "round", "game_number"}
    ),
    "playoff_series": frozenset({"season", "teams", "round"}),
    "postseason_summary": frozenset({"season", "teams"}),
}

WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


class _Clarify(Exception):
    def __init__(self, field: str, reason: str):
        self.field = field
        self.reason = reason


class _Invalid(Exception):
    pass


def reference_date(context: AskContext) -> dt.date:
    return context.reference_time.astimezone(ZoneInfo(NEW_YORK_TZ)).date()


def resolve_components(parts: DateComponents, today: dt.date) -> DateRange | str:
    """Resolve date components against the New York reference date.

    Returns a DateRange, or one of "year_required", "range_too_long", "invalid_date".
    """
    try:
        if parts.kind == "relative":
            start, end = _relative(parts, today)
        else:
            if parts.year is None and parts.end_year is None:
                return "year_required"
            start_year = parts.year if parts.year is not None else parts.end_year
            start = dt.date(start_year, parts.month, parts.day)
            if parts.kind == "calendar_date":
                end = start
            else:
                end_year = parts.end_year if parts.end_year is not None else start_year + (
                    1 if parts.year is not None and parts.end_month < parts.month else 0
                )
                end = dt.date(end_year, parts.end_month, parts.end_day)
    except (TypeError, ValueError):
        return "invalid_date"
    if end < start:
        return "invalid_date"
    if (end - start).days >= MAX_GAME_SEARCH_DAYS:
        return "range_too_long"
    return DateRange(start=start, end=end)


def _relative(parts: DateComponents, today: dt.date) -> tuple[dt.date, dt.date]:
    monday = today - dt.timedelta(days=today.weekday())
    match parts.relative:
        case "today" | "tonight":
            return today, today
        case "yesterday" | "last_night":
            day = today - dt.timedelta(days=1)
            return day, day
        case "tomorrow":
            day = today + dt.timedelta(days=1)
            return day, day
        case "this_week":
            return monday, monday + dt.timedelta(days=6)
        case "last_week":
            return monday - dt.timedelta(days=7), monday - dt.timedelta(days=1)
        case "last_weekday":
            # Most recent past <weekday>, excluding today.
            back = (today.weekday() - WEEKDAYS.index(parts.weekday)) % 7 or 7
            day = today - dt.timedelta(days=back)
            return day, day
        case "this_weekday":
            day = monday + dt.timedelta(days=WEEKDAYS.index(parts.weekday))
            return day, day
        case "past_days":
            return today - dt.timedelta(days=parts.count - 1), today
    raise ValueError(f"unknown relative date {parts.relative!r}")


class Normalizer:
    """Implements `server.ask.protocols.RequestNormalizer`."""

    def normalize(
        self, output: InterpreterOutput, candidates: CandidateLookupResult, context: AskContext
    ) -> NormalizationResult:
        if output.outcome == "unsupported":
            return NormalizationResult(status="unsupported", unsupported_reason=output.unsupported_reason)
        if output.outcome != "interpreted":
            return NormalizationResult(status="invalid", errors=[f"interpreter outcome {output.outcome}"])
        try:
            self._check_values(output, candidates)
            return self._build(output, candidates, context)
        except _Clarify as c:
            return NormalizationResult(status="needs_clarification", clarify_field=c.field, clarify_reason=c.reason)
        except _Invalid as exc:
            return NormalizationResult(status="invalid", errors=[str(exc)[:200]])

    # -- validation -------------------------------------------------------------------

    def _check_values(self, output: InterpreterOutput, candidates: CandidateLookupResult) -> None:
        for f in output.fields:
            values = f.selected + f.alternatives
            if f.field in CLOSED_VALUES:
                bad = [v for v in values if v not in CLOSED_VALUES[f.field]]
                if bad:
                    raise _Invalid(f"{f.field}: unknown value {bad[0]!r}")
                continue
            wanted = CANDIDATE_SET_FOR[f.field]
            for value in values:
                candidate = candidates.by_id(value)
                if candidate is None or candidate.field != wanted:
                    raise _Invalid(f"{f.field}: unknown candidate {value!r}")

    # -- field access -----------------------------------------------------------------

    @staticmethod
    def _field(output: InterpreterOutput, name: str) -> FieldInterpretation:
        return output.get_field(name) or FieldInterpretation(field=name, status="absent")

    def _require(self, output: InterpreterOutput, name: str) -> list[str]:
        f = self._field(output, name)
        if f.status == "selected":
            return f.selected
        if f.status == "absent":
            raise _Clarify(name, "missing")
        raise _Clarify(name, f.status)

    def _optional(self, output: InterpreterOutput, name: str) -> list[str]:
        f = self._field(output, name)
        if f.status == "selected":
            return f.selected
        if f.status == "absent":
            return []
        if name == "aggregation":
            raise _Invalid(f"aggregation: unresolved {f.status} value")
        # The user said something we cannot pin down: dropping it would change the question.
        raise _Clarify(name, f.status)

    # -- entities ---------------------------------------------------------------------

    @staticmethod
    def _value(candidates: CandidateLookupResult, candidate_id: str):
        return candidates.by_id(candidate_id).value

    def _teams(self, candidates, ids):
        return [self._value(candidates, i).team for i in ids]

    def _dates(self, output, candidates, context, *, required: bool) -> DateRange | None:
        f = self._field(output, "date")
        if f.status == "selected":
            value = self._value(candidates, f.selected[0])
            if value.resolved is not None:
                return value.resolved
            reason = value.unresolved_reason or "missing"
            raise _Clarify("date", "missing" if reason == "invalid_date" else reason)
        if f.status in ("ambiguous", "no_matching_candidate"):
            raise _Clarify("date", f.status)
        if output.extracted_date is not None and candidates.sets["date"].status != "candidates":
            resolved = resolve_components(output.extracted_date, reference_date(context))
            if isinstance(resolved, DateRange):
                return resolved
            raise _Clarify("date", "missing" if resolved == "invalid_date" else resolved)
        if required:
            raise _Clarify("date", "missing")
        return None

    # -- request building -------------------------------------------------------------

    def _build(self, output, candidates, context) -> NormalizationResult:
        intent = self._require(output, "intent")[0]
        builder = {
            "game_search": self._game_search,
            "boxscore_stat": self._boxscore,
            "playoff_series": self._series,
            "postseason_summary": self._postseason,
        }[intent]
        try:
            request = builder(output, candidates, context)
        except ValidationError as exc:
            raise _Invalid(f"{intent}: {exc.errors()[0]['msg']}") from exc
        if isinstance(request, NormalizationResult):
            return request
        return NormalizationResult(status="valid", request=request)

    def _game_search(self, output, candidates, context):
        dates = self._dates(output, candidates, context, required=True)
        teams = self._teams(candidates, self._optional(output, "teams"))
        location_ids = self._optional(output, "location")
        location = self._value(candidates, location_ids[0]).location if location_ids else None
        return GameSearchRequest(dates=dates, teams=teams, location=location)

    def _boxscore(self, output, candidates, context):
        aggregation = self._optional(output, "aggregation")
        if aggregation == ["per_game"]:
            return NormalizationResult(status="unsupported", unsupported_reason="multi_game_average")
        scope = self._require(output, "stat_scope")[0]
        stat_values = self._optional(output, "stat")
        if not stat_values:
            if scope == "leaders":
                raise _Clarify("stat", "missing")
            stat_values = ["stat_line"]
        if scope == "leaders" and stat_values[0] in NON_LEADER_STATS:
            return NormalizationResult(status="unsupported", unsupported_reason="unsupported_leader_stat")

        teams = self._teams(candidates, self._optional(output, "teams"))
        player = None
        if scope == "player":
            player = self._value(candidates, self._require(output, "player")[0]).player
        team = None
        if scope == "team":
            if not teams:
                raise _Clarify("teams", "missing")
            if len(teams) > 1:
                # The interpreter identifies matchup participants but has no
                # field for which team's stat the user requested.
                raise _Clarify("teams", "ambiguous")
            team = teams[0]

        game = self._game_selector(output, candidates, context, teams)
        return BoxscoreStatRequest(
            scope=scope,
            stat=StatSelection(stat=stat_values[0], aggregation="total"),
            game=game,
            player=player,
            team=team,
        )

    def _game_selector(self, output, candidates, context, teams) -> GameSelector:
        dates = self._dates(output, candidates, context, required=False)
        season_ids = self._optional(output, "season")
        round_ids = self._optional(output, "round")
        number_ids = self._optional(output, "game_number")
        season = self._value(candidates, season_ids[0]).season if season_ids else None
        round_value = self._value(candidates, round_ids[0]) if round_ids else None
        number = self._value(candidates, number_ids[0]).game_number if number_ids else None
        # Page context identifies the game only when the question supplies no
        # game selector of its own. Keep named teams so the resolver verifies
        # that they participated in the contextual game.
        if dates is None and not (season_ids or round_ids or number_ids) and context.game_id:
            return GameSelector(game_id=context.game_id, teams=teams)
        if dates is not None:
            if dates.start != dates.end:
                raise _Clarify("date", "ambiguous")  # a boxscore needs one day
            # The date may conflict with an explicitly named playoff game. Keep
            # every constraint so the resolver can verify them before answering.
            return GameSelector(
                date=dates.start, teams=teams, season=season,
                round=round_value.round if round_value else None,
                conference=round_value.conference if round_value else None,
                game_number=number,
            )
        if not (season_ids or number_ids or round_ids):
            raise _Clarify("date", "missing")
        if not season_ids:
            raise _Clarify("season", "missing")
        if not number_ids:
            raise _Clarify("game_number", "missing")
        if round_value is None and len(teams) != 2:
            raise _Clarify("round" if len(teams) < 2 else "teams", "missing")
        return GameSelector(
            season=season,
            game_number=number,
            round=round_value.round if round_value else None,
            conference=round_value.conference if round_value else None,
            teams=teams,
        )

    def _series(self, output, candidates, context):
        season = self._value(candidates, self._require(output, "season")[0]).season
        teams = self._teams(candidates, self._optional(output, "teams"))
        round_ids = self._optional(output, "round")
        round_value = self._value(candidates, round_ids[0]) if round_ids else None
        round_name = round_value.round if round_value else None
        conference = round_value.conference if round_value else None
        identified = (
            len(teams) == 2
            or (len(teams) == 1 and round_name)
            or round_name == "finals"
            or (round_name == "conference_finals" and conference)
        )
        if not identified:
            raise _Clarify("teams" if round_name else "round", "missing")
        return PlayoffSeriesRequest(season=season, teams=teams, round=round_name, conference=conference)

    def _postseason(self, output, candidates, context):
        season = self._value(candidates, self._require(output, "season")[0]).season
        teams = self._teams(candidates, self._optional(output, "teams"))
        if len(teams) > 1:
            raise _Clarify("teams", "ambiguous")
        return PostseasonSummaryRequest(season=season, team=teams[0] if teams else None)


def relevant_fields(output: InterpreterOutput) -> frozenset[str]:
    intent = output.get_field("intent")
    if intent is None or intent.status != "selected":
        return frozenset({"intent"})
    return RELEVANT_FIELDS[intent.selected[0]] | {"intent"}


def canonical_request(request: Any) -> dict[str, Any]:
    """JSON form with team lists sorted, for order-insensitive comparison."""
    data = request.model_dump(mode="json")

    def sort_teams(obj: Any) -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key == "teams" and isinstance(value, list):
                    value.sort(key=lambda t: t["team_id"])
                sort_teams(value)

    sort_teams(data)
    return data
