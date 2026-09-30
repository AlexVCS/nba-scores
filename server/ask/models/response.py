"""HTTP contract for ``POST /ask`` and ``GET /ask/suggest``.

Response data is authored by Python, never by a model. JSON keys are
snake_case, except the embedded scoreboard ``game`` payload, which is passed
through unchanged (camelCase) so the shared GameCard can render it.

Spoilers (ADR 0006): asking is consent, so ``result`` and ``notice`` carry no
spoiler protection and the UI shows them immediately. The ``spoiler`` flags on
interpretation items, clarification options, links, and suggestions mark what
the user did not ask for; while results are hidden the UI omits flagged
entries from the DOM and accessibility text.

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
    ClarifyField,
    ClarifyReason,
    Conference,
    ContractModel,
    DateRange,
    Intent,
    NewYorkDateTime,
    PlayerRef,
    PlayoffRound,
    Season,
    Stat,
    StatKey,
    StatScope,
    TeamRef,
)
from .interpreter import AdapterName, FieldDecision, UnsupportedReason
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

    ``resolution`` is the opaque token from a ClarificationOption. It refers to
    server-validated resolution state, which may be partial. With a valid
    token the server makes zero model calls: if every required field is now
    resolved it executes the request, otherwise it returns the next
    ``needs_clarification`` (whose options carry new tokens that include the
    earlier choices). An expired or invalid token (bad signature, unknown,
    issued for another question) is ignored: the server handles ``question``
    as a new question, which may call a model. ``question`` is always the
    option's standalone rewritten question, so this fallback is safe.
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

# Series slugs follow src/utils/seriesSlug.ts: "the-finals", or
# "{slugify(bracketGroupId)}-{first-round|semifinal|final|round-N}-{bracketOrder+1}",
# e.g. "east-conference-first-round-1". Team-based slugs are not routes.
SERIES_SLUG_PATTERN = r"(the-finals|[a-z0-9]+(-[a-z0-9]+)*-(first-round|semifinal|final|round-\d+)-\d+)"
INTERNAL_LINK_PATTERN = (
    r"^/(\?date=\d{4}-\d{2}-\d{2}"
    r"|games/\d{10}/boxscore(\?date=\d{4}-\d{2}-\d{2})?"
    r"|playoffs(\?season=\d{4}-\d{2})?"
    r"|playoffs/\d{4}/" + SERIES_SLUG_PATTERN + r")$"
)
EXTERNAL_LINK_PREFIX = "https://www.nba.com/"


class VerifiedLink(ContractModel):
    """A link Python built from verified IDs. Internal ``href``s are
    design-agnostic app paths; the UI adds the active design prefix.

    This is the only URL-bearing type in the contract: every link anywhere in
    a response uses it, so one allowlist applies everywhere."""

    kind: LinkKind
    label: str = Field(min_length=1, max_length=80)
    href: str = Field(min_length=1, max_length=300)
    external: bool = False
    # True when the link would reveal a result the user did not ask for, such
    # as a follow-up card for another game. Links to what was asked are not
    # spoilers. The UI omits flagged links while results are hidden.
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
    # Cascade only: interpreter field -> tier that decided it (ADR 0002).
    field_tiers: dict[str, str] = Field(default_factory=dict)
    # Development servers only (`ASK_DEV=1`): per-field tier, confidence, and outcome.
    # Omitted from the JSON when empty, so production responses never carry the key.
    field_decisions: list[FieldDecision] = Field(default_factory=list, max_length=12,
                                                 exclude_if=lambda value: not value)


# --------------------------------------------------------------------------
# Interpretation ("Reading this as")
# --------------------------------------------------------------------------

InterpretationField = Literal[
    "player", "team", "teams", "game", "date", "dates", "stat", "season", "round", "series", "game_number",
    "location",
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
    # True when the item reveals a result: any participant or game the server
    # inferred for a postseason question (e.g. the teams in "the 2025 Finals").
    # Shown with an answer or not_found (the user asked); omitted beside a
    # clarification or notice while results are hidden.
    spoiler: bool = False


class Interpretation(ContractModel):
    intent: Intent | None = None
    detected_type: DetectedType | None = None
    items: list[InterpretationItem] = Field(default_factory=list, max_length=8)
    reference_time: NewYorkDateTime  # server "now", normalized to America/New_York
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


class GameResultItem(ContractModel):
    date: dt.date  # America/New_York game date; matches game.gameTimeUTC in New York
    game: ScoreboardGame
    links: list[VerifiedLink] = Field(default_factory=list, max_length=4)


class GameDay(ContractModel):
    date: dt.date
    games: list[GameResultItem] = Field(default_factory=list)


class GamesResult(ContractModel):
    kind: Literal["games"] = "games"
    dates: DateRange
    teams: list[TeamRef] = Field(default_factory=list, max_length=2)
    days: list[GameDay] = Field(min_length=1, max_length=7)
    total_games: int

    @model_validator(mode="after")
    def _count(self) -> GamesResult:
        items = [item for day in self.days for item in day.games]
        if self.total_games != len(items) or not items:
            raise ValueError("total_games must equal the number of games (at least one)")
        return self


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
    final_score: FinalScore | None  # None for games not finished


class PlayerStatLine(ContractModel):
    player: PlayerRef
    team: TeamRef
    status: Literal["played", "did_not_play", "inactive"]
    values: list[StatValue] = Field(default_factory=list, max_length=20)


class TeamStatLine(ContractModel):
    team: TeamRef
    values: list[StatValue] = Field(default_factory=list, max_length=20)


class LeaderRow(ContractModel):
    rank: int = Field(ge=1)  # ties share a rank
    player: PlayerRef
    team: TeamRef
    value: StatValue


class BoxscoreStatResult(ContractModel):
    kind: Literal["boxscore_stat"] = "boxscore_stat"
    scope: StatScope
    stat: Stat
    aggregation: Aggregation = "total"
    game: GameContext
    player_line: PlayerStatLine | None = None
    team_lines: list[TeamStatLine] = Field(default_factory=list, max_length=2)
    # Leaders scope only. Ties share a rank.
    leaders: list[LeaderRow] | None = None

    @model_validator(mode="after")
    def _scope_payload(self) -> BoxscoreStatResult:
        if self.scope == "player" and self.player_line is None:
            raise ValueError("player scope needs player_line")
        if self.scope == "team" and not self.team_lines:
            raise ValueError("team scope needs team_lines")
        if (self.scope == "leaders") != (self.leaders is not None):
            raise ValueError("leaders is required iff scope is leaders")
        if self.leaders is not None and not (1 <= len(self.leaders) <= 10):
            raise ValueError("leaders holds 1-10 rows")
        return self


class SeriesTeamRow(ContractModel):
    team: TeamRef
    seed: int | None
    wins: int
    won_series: bool | None  # None while undecided


class PlayoffSeriesResult(ContractModel):
    kind: Literal["playoff_series"] = "playoff_series"
    season: Season
    round: PlayoffRound
    conference: Conference | None = None
    teams: list[SeriesTeamRow] = Field(min_length=2, max_length=2)
    status: SeriesStatus
    games_played: int
    summary: str  # "DET won 4-2"
    games: list[GameResultItem]


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


SeriesStatus = Literal["not_started", "in_progress", "complete"]


class PostseasonRoundRow(ContractModel):
    round: PlayoffRound
    conference: Conference | None = None
    opponent: TeamRef
    team_wins: int = Field(ge=0, le=4)
    opponent_wins: int = Field(ge=0, le=4)
    won: bool | None  # None while undecided
    series_link: VerifiedLink | None = None


class SeriesParticipant(ContractModel):
    team: TeamRef
    wins: int = Field(ge=0, le=4)


class PostseasonSeriesRow(ContractModel):
    """League-wide summary row: one series, finished or not."""

    round: PlayoffRound
    conference: Conference | None = None
    teams: list[SeriesParticipant] = Field(min_length=2, max_length=2)
    status: SeriesStatus
    winner_team_id: int | None = None  # set iff status is complete

    @model_validator(mode="after")
    def _winner(self) -> PostseasonSeriesRow:
        if (self.status == "complete") != (self.winner_team_id is not None):
            raise ValueError("winner_team_id is required iff status is complete")
        if self.winner_team_id is not None and self.winner_team_id not in {p.team.team_id for p in self.teams}:
            raise ValueError("winner_team_id must be one of the two teams")
        return self


class PostseasonSummaryResult(ContractModel):
    """One team's postseason (team set) or the whole postseason (team None)."""

    kind: Literal["postseason_summary"] = "postseason_summary"
    season: Season
    team: TeamRef | None = None
    finish: PostseasonFinish | None
    record: WinLoss | None
    series_won: int | None
    rounds: list[PostseasonRoundRow]  # team scope
    champion: TeamRef | None  # league scope
    runner_up: TeamRef | None
    series: list[PostseasonSeriesRow]  # league scope


AskResult = Annotated[
    Union[GamesResult, BoxscoreStatResult, PlayoffSeriesResult, PostseasonSummaryResult],
    Field(discriminator="kind"),
]

# --------------------------------------------------------------------------
# Clarification, notices, suggestions
# --------------------------------------------------------------------------

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
    # Opaque server token; send back as AskQuery.resolution. Zero model calls:
    # the reply is the answer, or the next clarification if fields remain.
    resolution: str = Field(min_length=1, max_length=512)
    # True when the option itself reveals a result (e.g. a participant the
    # server inferred for a playoff round). Options are not answers: the UI
    # omits them while results are hidden unless the user shows all options.
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
    # True if the text itself reveals a result. Suggestions are never
    # requested answers, so the UI drops these while results are hidden.
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
    link: VerifiedLink


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
