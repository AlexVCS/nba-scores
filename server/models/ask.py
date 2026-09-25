"""Typed natural-language request interpretation models.

These models describe what the user said. They deliberately do not contain
resolved team/player IDs, game IDs, URLs, or calendar dates.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


Intent = Literal[
    "game_search",
    "boxscore_stats",
    "playoff_series",
    "postseason_summary",
    "unsupported",
    "needs_clarification",
]
MentionKind = Literal["team", "player", "unknown"]
AskOperation = Literal[
    "list",
    "player_stats",
    "team_stats",
    "leaders",
    "series_result",
    "summary",
]
Statistic = Literal[
    "points",
    "rebounds",
    "assists",
    "steals",
    "blocks",
    "turnovers",
    "fouls",
    "minutes",
    "field_goals",
    "three_pointers",
    "free_throws",
    "field_goal_percentage",
    "three_point_percentage",
    "free_throw_percentage",
    "plus_minus",
    "quarter_scores",
]


class AskMention(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    text: str = Field(min_length=1, max_length=120)
    kind: MentionKind


class AskDateExpression(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    text: str = Field(min_length=1, max_length=120)
    # Keep this as language, not a date. The resolver owns America/New_York
    # and the definition of expressions such as "last week".
    kind: Literal["calendar_date", "season", "relative", "range", "unknown"]


class AskAmbiguity(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    field: str = Field(min_length=1, max_length=80)
    reason: str = Field(min_length=1, max_length=240)


class AskInterpretation(BaseModel):
    """The only model-authored part of an ask request."""

    model_config = ConfigDict(extra="forbid", strict=True)

    intent: Intent
    operation: AskOperation | None
    mentions: list[AskMention] = Field(..., max_length=8)
    date_expressions: list[AskDateExpression] = Field(..., max_length=4)
    round_mention: str | None = Field(..., max_length=80)
    game_number: int | None = Field(..., ge=1, le=7)
    statistics: list[Statistic] = Field(..., max_length=12)
    ambiguities: list[AskAmbiguity] = Field(..., max_length=6)
    unsupported_reason: str | None = Field(..., max_length=240)


class AskParseUsage(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)


class AskParseMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    provider: str
    model: str
    latency_ms: int = Field(ge=0)
    usage: AskParseUsage
    estimated_cost_usd: float | None = Field(default=None, ge=0)


class AskParseResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    interpretation: AskInterpretation
    metadata: AskParseMetadata
