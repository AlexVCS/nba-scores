"""Normalized application request: the only thing Python executes.

Every interpreter adapter's output is normalized and validated into one of
these models before any data tool runs. All entities carry authoritative IDs
and all dates are resolved calendar dates in America/New_York.

Frozen contract (docs/ask-contract.md). Coordinate before changing.
"""

from __future__ import annotations

import datetime as dt
from typing import Annotated, Literal, Union

from pydantic import Field, TypeAdapter, model_validator

from .common import (
    CAREER_LEADER_STATS,
    DEFAULT_LEADER_LIMIT,
    CareerView,
    LEADER_PERCENTAGES,
    MAX_LEADER_LIMIT,
    NON_LEADER_STATS,
    SEASON_LEADER_STATS,
    Aggregation,
    Conference,
    ContractModel,
    DateRange,
    GameLocation,
    NewYorkDateTime,
    PlayerRef,
    PlayoffRound,
    Season,
    SeasonType,
    StandingsScope,
    Stat,
    StatScope,
    TeamRef,
)

AppRoute = Literal["scores", "boxscore", "playoffs", "series", "other"]


class AskContext(ContractModel):
    """App context for one request. ``reference_time`` is assigned by the
    server (never the client). It must be timezone-aware and is converted to
    America/New_York on validation, so ``reference_time.date()`` is the New York
    calendar date. Relative dates resolve against it, and that date is part of
    relative-parse cache keys."""

    reference_time: NewYorkDateTime
    route: AppRoute | None = None
    view_date: dt.date | None = None
    game_id: str | None = Field(default=None, pattern=r"^\d{10}$")
    playoff_season: Season | None = None


class GameSearchRequest(ContractModel):
    """Games on one date or up to seven consecutive days, optionally by team."""

    intent: Literal["game_search"] = "game_search"
    dates: DateRange
    teams: list[TeamRef] = Field(default_factory=list, max_length=2)
    # Games played in this city (home team in `location.teams`), ADR 0011.
    location: GameLocation | None = None


class StatSelection(ContractModel):
    stat: Stat
    aggregation: Aggregation = "total"


class GameSelector(ContractModel):
    """Identifies exactly one game. Valid forms:

    - ``game_id``
    - ``date`` (plus optional teams; a player alone is enough for player scope)
    - ``season`` + ``game_number`` + (``round`` or two ``teams``)
    """

    game_id: str | None = Field(default=None, pattern=r"^\d{10}$")
    date: dt.date | None = None
    teams: list[TeamRef] = Field(default_factory=list, max_length=2)
    season: Season | None = None
    round: PlayoffRound | None = None
    conference: Conference | None = None
    game_number: int | None = Field(default=None, ge=1, le=7)

    @model_validator(mode="after")
    def _one_game(self) -> GameSelector:
        if self.game_id or self.date:
            return self
        if self.season and self.game_number and (self.round or len(self.teams) == 2):
            return self
        raise ValueError("selector needs game_id, date, or season+game_number+(round or two teams)")


class BoxscoreStatRequest(ContractModel):
    """One statistic (or a full line) from one game's boxscore."""

    intent: Literal["boxscore_stat"] = "boxscore_stat"
    scope: StatScope
    stat: StatSelection
    game: GameSelector
    player: PlayerRef | None = None
    team: TeamRef | None = None

    @model_validator(mode="after")
    def _scope_fields(self) -> BoxscoreStatRequest:
        if self.scope == "player" and self.player is None:
            raise ValueError("player scope needs player")
        if self.scope != "player" and self.player is not None:
            raise ValueError("only player scope takes a player")
        if self.scope == "team" and self.team is None and len(self.game.teams) == 0:
            raise ValueError("team scope needs a team")
        if self.scope == "leaders" and self.stat.stat in NON_LEADER_STATS:
            raise ValueError(f"no leader ranking rule for {self.stat.stat} (unsupported_leader_stat)")
        if self.stat.aggregation != "total":
            raise ValueError("single-game statistics are totals; per_game is unsupported")
        return self


class PlayoffSeriesRequest(ContractModel):
    intent: Literal["playoff_series"] = "playoff_series"
    season: Season
    teams: list[TeamRef] = Field(default_factory=list, max_length=2)
    round: PlayoffRound | None = None
    conference: Conference | None = None

    @model_validator(mode="after")
    def _identifies_series(self) -> PlayoffSeriesRequest:
        if len(self.teams) == 2:
            return self
        if len(self.teams) == 1 and self.round:
            return self
        if self.round == "finals":
            return self
        if self.round == "conference_finals" and self.conference:
            return self
        raise ValueError("series needs two teams, one team + round, the finals, or conference + conference_finals")


class PostseasonSummaryRequest(ContractModel):
    """A whole postseason (team=None) or one team's postseason."""

    intent: Literal["postseason_summary"] = "postseason_summary"
    season: Season
    team: TeamRef | None = None


class PlayerSeasonStatsRequest(ContractModel):
    """One player's season, including all stints unless a team is named."""

    intent: Literal["player_season_stats"] = "player_season_stats"
    player: PlayerRef
    season: Season
    season_type: SeasonType = "regular_season"
    stat: StatSelection
    team: TeamRef | None = None


class TeamRecordsRequest(ContractModel):
    """Regular-season record for one team, or the league/conference standings."""

    intent: Literal["team_records"] = "team_records"
    season: Season
    team: TeamRef | None = None
    standings_scope: StandingsScope = "league"

    @model_validator(mode="after")
    def _one_scope(self):
        if self.team and self.standings_scope != "league":
            raise ValueError("Choose a team record or conference standings, not both")
        return self


class SeasonLeadersRequest(ContractModel):
    """League-wide leaders in one statistic for one season and phase (docs/ask-stage3.md).

    ``limit`` is read by Python from "top N" text, never by a model (ADR 0012). Every
    player whose rank is ``limit`` or better is returned, so ties can add rows.
    """

    intent: Literal["season_leaders"] = "season_leaders"
    season: Season
    season_type: SeasonType = "regular_season"
    stat: StatSelection
    limit: int = Field(default=DEFAULT_LEADER_LIMIT, ge=1, le=MAX_LEADER_LIMIT)
    # The user's "top N" when it was above the maximum and was shown as the top 25.
    requested_limit: int | None = Field(default=None, gt=MAX_LEADER_LIMIT)

    @model_validator(mode="after")
    def _leader_stat(self):
        if self.stat.stat not in SEASON_LEADER_STATS:
            raise ValueError(f"no season leaderboard for {self.stat.stat} (unsupported_leader_stat)")
        if self.stat.stat in LEADER_PERCENTAGES and self.stat.aggregation != "total":
            raise ValueError("percentage leaders have no per-game measure")
        return self


class CareerStatsRequest(ContractModel):
    """A player's career totals or averages, the all-time top N, or a player's all-time
    rank (docs/ask-stage3.md, ADR 0013). Python picks ``view`` and ``limit``."""

    intent: Literal["career_stats"] = "career_stats"
    view: CareerView
    player: PlayerRef | None = None
    season_type: SeasonType = "regular_season"
    stat: StatSelection
    limit: int = Field(default=DEFAULT_LEADER_LIMIT, ge=1, le=MAX_LEADER_LIMIT)
    # The user's "top N" when it was above the maximum and was shown as the top 25.
    requested_limit: int | None = Field(default=None, gt=MAX_LEADER_LIMIT)

    @model_validator(mode="after")
    def _view_shape(self):
        if (self.view == "leaders") != (self.player is None):
            raise ValueError("only the all-time leaders view has no player")
        if self.view == "player_totals":
            if self.stat.stat == "plus_minus":
                raise ValueError("no career plus/minus")
        elif self.stat.stat not in CAREER_LEADER_STATS or self.stat.aggregation != "total":
            raise ValueError("all-time lists are totals of counting statistics only")
        return self


AskRequest = Annotated[
    Union[GameSearchRequest, BoxscoreStatRequest, PlayoffSeriesRequest, PostseasonSummaryRequest, PlayerSeasonStatsRequest, TeamRecordsRequest, SeasonLeadersRequest, CareerStatsRequest],
    Field(discriminator="intent"),
]
ASK_REQUEST_ADAPTER: TypeAdapter[AskRequest] = TypeAdapter(AskRequest)
