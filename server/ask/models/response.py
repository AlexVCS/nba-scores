"""HTTP contract for ``POST /ask`` and ``GET /ask/suggest``.

Response data is authored by Python, never by a model. JSON keys are
snake_case, except the embedded scoreboard ``game`` payload, which is passed
through unchanged (camelCase) so the shared GameCard can render it.

Spoilers: every protected value is either a ``Guarded`` value or carries a
``spoiler`` flag. The server always includes the value; while results are
hidden the UI must omit flagged values from the DOM and accessibility text.

Mirrored in src/services/ask/types.ts. Frozen contract (docs/ask-contract.md).
"""

from __future__ import annotations

import datetime as dt
import re
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .common import (
    MAX_QUESTION_LENGTH,
    NEW_YORK_TZ,
    SCHEMA_VERSION,
    Aggregation,
    Conference,
    ContractModel,
    DateRange,
    Guarded,
    Intent,
    PlayerRef,
    PlayoffRound,
    Season,
    Stat,
    StatKey,
    StatScope,
    TeamRef,
)
from .interpreter import AdapterName, UnsupportedReason
from .request import AppRoute

# --------------------------------------------------------------------------
# Request body
# --------------------------------------------------------------------------


class ClientContext(ContractModel):
    """What the page shows. The server derives reference time itself."""

    route: AppRoute | None = None
    view_date: dt.date | None = None
    game_id: str | None = Field(default=None, pattern=r"^\d{10}$")
    playoff_season: Season | None = None


class AskQuery(ContractModel):
    """``POST /ask`` body.

    ``resolution`` is the opaque token from a ClarificationOption. When set,
    the server executes that already-validated request with zero model calls
    (``question`` still carries the option's standalone question for history).
    """

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    question: str = Field(min_length=1, max_length=MAX_QUESTION_LENGTH)
    context: ClientContext | None = None
    resolution: str | None = Field(default=None, max_length=512)


# --------------------------------------------------------------------------
# Shared pieces
# --------------------------------------------------------------------------

Outcome = Literal["answer", "needs_clarification", "unsupported", "not_found", "unavailable", "budget_exhausted"]

# Badge next to "Reading this as". Derived from intent (+ stat scope).
DetectedType = Literal["games", "player_stat", "team_stat", "stat_leaders", "series", "postseason"]

LinkKind = Literal["boxscore", "scores_date", "playoff_series", "playoff_bracket", "nba_game", "nba_stat_event"]

INTERNAL_LINK_PATTERN = (
    r"^/(\?date=\d{4}-\d{2}-\d{2}"
    r"|games/\d{10}/boxscore(\?date=\d{4}-\d{2}-\d{2})?"
    r"|playoffs(\?season=\d{4}-\d{2})?"
    r"|playoffs/\d{4}/[a-z0-9-]+)$"
)
EXTERNAL_LINK_PREFIX = "https://www.nba.com/"


class VerifiedLink(ContractModel):
    """A link Python built from verified IDs. Internal ``href``s are
    design-agnostic app paths; the UI adds the active design prefix."""

    kind: LinkKind
    label: str = Field(min_length=1, max_length=80)
    href: str = Field(min_length=1, max_length=300)
    external: bool = False
    spoiler: bool = False

    @model_validator(mode="after")
    def _allowlisted(self) -> VerifiedLink:
        if self.external:
            if not self.href.startswith(EXTERNAL_LINK_PREFIX):
                raise ValueError("external links must point to nba.com")
        elif not re.match(INTERNAL_LINK_PATTERN, self.href):
            raise ValueError(f"internal link not allowlisted: {self.href}")
        return self


class SourceMetadata(ContractModel):
    name: Literal["nba_live", "nba_stats", "nba_schedule", "basketball_reference", "app_cache"]
    label: str = Field(max_length=80)  # "NBA.com"
    fetched_at: dt.datetime | None = None
    complete: bool = True  # False while games/series are still in progress


class InterpreterInfo(ContractModel):
    """For source-aware copy. No prompts, raw output, or keys."""

    model_called: bool
    cache_hit: bool = False
    adapter: AdapterName | None = None
    model: str | None = Field(default=None, max_length=80)
    fallback_used: bool = False


# --------------------------------------------------------------------------
# Interpretation ("Reading this as")
# --------------------------------------------------------------------------

InterpretationField = Literal[
    "player", "team", "teams", "game", "date", "dates", "stat", "season", "round", "series", "game_number"
]


class InterpretationItem(ContractModel):
    field: InterpretationField
    value: str = Field(min_length=1, max_length=120)  # "James Harden", "Last week"
    detail: str | None = Field(default=None, max_length=120)  # "CLE", "Mon, Feb 2 – Sun, Feb 8, 2026 · ET"
    expression: str | None = Field(default=None, max_length=120)  # the user's words, if different
    origin: Literal["question", "inferred", "context"]
    status: Literal["resolved", "ambiguous"] = "resolved"
    match_count: int | None = Field(default=None, ge=2)  # ambiguous: "4 matches"
    team_id: int | None = None
    player_id: int | None = None
    # True when the item reveals a result (e.g. inferred series participants).
    spoiler: bool = False


class Interpretation(ContractModel):
    intent: Intent | None = None
    detected_type: DetectedType | None = None
    items: list[InterpretationItem] = Field(default_factory=list, max_length=8)
    reference_time: dt.datetime  # server "now" in America/New_York
    timezone: Literal["America/New_York"] = NEW_YORK_TZ
    dates: DateRange | None = None
    season: Season | None = None


# --------------------------------------------------------------------------
# Result payloads
# --------------------------------------------------------------------------


class ScoreboardTeam(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)

    teamId: int
    teamName: str
    teamTricode: str
    score: int


class ScoreboardGame(BaseModel):
    """The existing scoreboard game payload (``GameData`` in the frontend),
    passed through unchanged; extra keys are allowed."""

    model_config = ConfigDict(extra="allow", frozen=True)

    gameId: str
    gameCode: str = ""
    gameStatus: int
    gameLabel: str = ""
    gameSubLabel: str = ""
    gameTimeUTC: str = ""
    gameStatusText: str
    ifNecessary: bool = False
    seriesGameNumber: str = ""
    seriesText: str = ""
    boxscoreAvailable: bool = False
    homeTeam: ScoreboardTeam
    awayTeam: ScoreboardTeam


class GameSpoilers(ContractModel):
    """Which parts of a game payload are protected while hidden."""

    score: bool = True  # scores, winner, leaders
    status_text: bool = True  # "Final/OT" reveals overtime
    series_text: bool = True  # "NYK leads 2-1"


class GameResultItem(ContractModel):
    date: dt.date  # America/New_York game date
    game: ScoreboardGame
    spoilers: GameSpoilers = Field(default_factory=GameSpoilers)
    links: list[VerifiedLink] = Field(default_factory=list, max_length=4)


class GameDay(ContractModel):
    date: dt.date
    games: list[GameResultItem] = Field(default_factory=list)


class GamesResult(ContractModel):
    kind: Literal["games"] = "games"
    dates: DateRange
    teams: list[TeamRef] = Field(default_factory=list, max_length=2)
    days: list[GameDay] = Field(min_length=1, max_length=7)
    total_games: int = Field(ge=1)


class StatValue(ContractModel):
    stat: StatKey
    value: float | None  # None when the source has no value
    display: str = Field(max_length=20)  # "21", "8-15", "53.3%", "34:12"
    made: int | None = None
    attempted: int | None = None


class FinalScore(ContractModel):
    away: int
    home: int
    periods: int = Field(ge=4)  # > 4 reveals overtime


class GameContext(ContractModel):
    game_id: str = Field(pattern=r"^\d{10}$")
    date: dt.date
    away: TeamRef
    home: TeamRef
    season: Season
    season_type: Literal["regular_season", "playoffs", "play_in", "preseason", "all_star", "nba_cup_final"]
    round: PlayoffRound | None = None
    game_number: int | None = Field(default=None, ge=1, le=7)
    final_score: Guarded[FinalScore | None]  # None for games not finished


class PlayerStatLine(ContractModel):
    player: PlayerRef
    team: TeamRef
    status: Literal["played", "did_not_play", "inactive"]
    values: list[Guarded[StatValue]] = Field(default_factory=list, max_length=20)


class TeamStatLine(ContractModel):
    team: TeamRef
    values: list[Guarded[StatValue]] = Field(default_factory=list, max_length=20)


class LeaderRow(ContractModel):
    rank: int = Field(ge=1)  # ties share a rank
    player: Guarded[PlayerRef]
    team: Guarded[TeamRef]
    value: Guarded[StatValue]


class BoxscoreStatResult(ContractModel):
    kind: Literal["boxscore_stat"] = "boxscore_stat"
    scope: StatScope
    stat: Stat
    aggregation: Aggregation = "total"
    game: GameContext
    player_line: PlayerStatLine | None = None
    team_lines: list[TeamStatLine] = Field(default_factory=list, max_length=2)
    leaders: list[LeaderRow] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def _scope_payload(self) -> BoxscoreStatResult:
        if self.scope == "player" and self.player_line is None:
            raise ValueError("player scope needs player_line")
        if self.scope == "team" and not self.team_lines:
            raise ValueError("team scope needs team_lines")
        if self.scope == "leaders" and not self.leaders:
            raise ValueError("leaders scope needs leaders")
        return self


class SeriesTeamRow(ContractModel):
    # Spoiler when the user did not name this team (inferred participant).
    team: Guarded[TeamRef]
    seed: Guarded[int | None]
    wins: Guarded[int]
    won_series: Guarded[bool | None]  # None while undecided


class PlayoffSeriesResult(ContractModel):
    kind: Literal["playoff_series"] = "playoff_series"
    season: Season
    round: PlayoffRound
    conference: Conference | None = None
    teams: list[SeriesTeamRow] = Field(min_length=2, max_length=2)
    status: Guarded[Literal["not_started", "in_progress", "complete"]]
    games_played: Guarded[int]
    summary: Guarded[str]  # "DET won 4-2"
    games: Guarded[list[GameResultItem]]  # count reveals series length


class WinLoss(ContractModel):
    wins: int = Field(ge=0)
    losses: int = Field(ge=0)


PostseasonFinish = Literal[
    "champion",
    "lost_finals",
    "lost_conference_finals",
    "lost_conference_semifinals",
    "lost_first_round",
    "lost_play_in",
    "did_not_qualify",
    "in_progress",
]


class PostseasonRoundRow(ContractModel):
    round: PlayoffRound
    conference: Conference | None = None
    opponent: TeamRef
    team_wins: int = Field(ge=0, le=4)
    opponent_wins: int = Field(ge=0, le=4)
    won: bool | None  # None while undecided
    series_href: str | None = None


class PostseasonSeriesRow(ContractModel):
    """League-wide summary row: one series."""

    round: PlayoffRound
    conference: Conference | None = None
    winner: TeamRef | None
    loser: TeamRef | None
    winner_wins: int = Field(ge=0, le=4)
    loser_wins: int = Field(ge=0, le=4)


class PostseasonSummaryResult(ContractModel):
    """One team's postseason (team set) or the whole postseason (team None).

    Qualification and advancement are protected, including the length of
    ``rounds``, so they are wrapped as a whole.
    """

    kind: Literal["postseason_summary"] = "postseason_summary"
    season: Season
    team: TeamRef | None = None
    finish: Guarded[PostseasonFinish | None]
    record: Guarded[WinLoss | None]
    series_won: Guarded[int | None]
    rounds: Guarded[list[PostseasonRoundRow]]  # team scope
    champion: Guarded[TeamRef | None]  # league scope
    runner_up: Guarded[TeamRef | None]
    series: Guarded[list[PostseasonSeriesRow]]  # league scope


AskResult = Annotated[
    Union[GamesResult, BoxscoreStatResult, PlayoffSeriesResult, PostseasonSummaryResult],
    Field(discriminator="kind"),
]

# --------------------------------------------------------------------------
# Clarification, notices, suggestions
# --------------------------------------------------------------------------

ClarifyField = Literal["player", "team", "teams", "date", "season", "round", "game_number", "stat", "intent"]
ClarifyReason = Literal["ambiguous", "missing", "no_matching_candidate", "year_required", "range_too_long"]
MAX_CLARIFICATION_OPTIONS = 9  # number shortcuts 1-9


class ClarificationOption(ContractModel):
    id: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=80)  # "Jalen Duren"
    sublabel: str | None = Field(default=None, max_length=40)  # "C"
    detail: str | None = Field(default=None, max_length=80)  # "WAS @ DET"
    team: TeamRef | None = None
    player_id: int | None = None
    # Standalone rewritten question (for the input box and recent history).
    question: str = Field(min_length=1, max_length=MAX_QUESTION_LENGTH)
    # Opaque server token; send back as AskQuery.resolution. Zero model calls.
    resolution: str = Field(min_length=1, max_length=512)
    spoiler: bool = False


class Clarification(ContractModel):
    field: ClarifyField
    reason: ClarifyReason
    prompt: str = Field(max_length=120)  # "Which Jalen?"
    detail: str | None = Field(default=None, max_length=240)  # "Four Jalens played on Thursday, Feb 5."
    options: list[ClarificationOption] = Field(default_factory=list, max_length=MAX_CLARIFICATION_OPTIONS)
    hint: str | None = Field(default=None, max_length=300)  # "Looking for Jalen Brunson? ..."


NoticeCode = Literal[
    "unsupported",
    "no_games",  # not_found: no games in range
    "no_record",  # not_found: historical record missing
    "player_did_not_play",
    "service_unavailable",
    "interpreter_unavailable",
    "budget_exhausted",
    "rate_limited",
]


class Notice(ContractModel):
    code: NoticeCode
    title: str = Field(max_length=80)
    message: str = Field(max_length=300)
    retryable: bool = False
    retry_after_seconds: int | None = Field(default=None, ge=0)
    unsupported_reason: UnsupportedReason | None = None
    # True when this request produced an anonymous unsupported-diagnostics entry.
    diagnostics_recorded: bool = False


SuggestionCategory = Literal["games", "stats", "series", "postseason"]


class Suggestion(ContractModel):
    """A standalone question (all names and dates spelled out)."""

    question: str = Field(min_length=1, max_length=MAX_QUESTION_LENGTH)
    category: SuggestionCategory
    # True if the text itself reveals a result; the UI drops these while hidden.
    spoiler: bool = False


# --------------------------------------------------------------------------
# Response
# --------------------------------------------------------------------------


class AskResponse(ContractModel):
    schema_version: Literal["1"] = SCHEMA_VERSION
    request_id: str = Field(min_length=1, max_length=64)
    outcome: Outcome
    question: str = Field(max_length=MAX_QUESTION_LENGTH)
    interpretation: Interpretation | None = None
    result: AskResult | None = None
    clarification: Clarification | None = None
    notice: Notice | None = None
    links: list[VerifiedLink] = Field(default_factory=list, max_length=6)
    suggestions: list[Suggestion] = Field(default_factory=list, max_length=4)
    sources: list[SourceMetadata] = Field(default_factory=list, max_length=4)
    interpreter: InterpreterInfo

    @model_validator(mode="after")
    def _outcome_shape(self) -> AskResponse:
        o = self.outcome
        if (o == "answer") != (self.result is not None):
            raise ValueError("result is required iff outcome is answer")
        if (o == "needs_clarification") != (self.clarification is not None):
            raise ValueError("clarification is required iff outcome is needs_clarification")
        if o not in ("answer", "needs_clarification") and self.notice is None:
            raise ValueError(f"{o} needs a notice")
        if o == "answer" and (self.interpretation is None or self.interpretation.intent is None):
            raise ValueError("answers need an interpretation with an intent")
        if o == "answer" and self.interpretation and self.result:
            expected = {
                "games": "game_search",
                "boxscore_stat": "boxscore_stat",
                "playoff_series": "playoff_series",
                "postseason_summary": "postseason_summary",
            }[self.result.kind]
            if self.interpretation.intent != expected:
                raise ValueError("result kind does not match interpretation intent")
        if o == "unsupported" and (self.notice is None or self.notice.unsupported_reason is None):
            raise ValueError("unsupported needs notice.unsupported_reason")
        return self


# --------------------------------------------------------------------------
# GET /ask/suggest?q=...&hidden=true  (typeahead; never calls a model)
# --------------------------------------------------------------------------


class SuggestGame(ContractModel):
    """A direct game match; the UI navigates without calling POST /ask."""

    game_id: str = Field(pattern=r"^\d{10}$")
    date: dt.date
    away: TeamRef
    home: TeamRef
    label: str = Field(max_length=120)  # "NYK @ BOS · Sun, Feb 23"
    href: str = Field(pattern=INTERNAL_LINK_PATTERN)


class SuggestEntity(ContractModel):
    kind: Literal["player", "team"]
    label: str = Field(max_length=80)
    player_id: int | None = None
    team: TeamRef | None = None


class AskSuggestResponse(ContractModel):
    """Grouped typeahead. With ``hidden=true`` the server omits team-specific
    playoff series suggestions and anything else that reveals results."""

    query: str = Field(max_length=MAX_QUESTION_LENGTH)
    games: list[SuggestGame] = Field(default_factory=list, max_length=5)
    entities: list[SuggestEntity] = Field(default_factory=list, max_length=5)
    questions: list[Suggestion] = Field(default_factory=list, max_length=5)
