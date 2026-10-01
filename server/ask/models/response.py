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
    CareerView,
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
    SeasonType,
    StandingsScope,
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
DetectedType = Literal["games", "player_stat", "team_stat", "stat_leaders", "series", "postseason", "season_stats", "team_records", "season_leaders", "career_stats"]

LinkKind = Literal["boxscore", "scores_date", "playoff_series", "playoff_bracket", "nba_game", "nba_stat_event", "source"]

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
            nba = self.href.startswith(EXTERNAL_LINK_PREFIX)
            bref = self.kind == "source" and re.fullmatch(
                r"https://www\.basketball-reference\.com/(?:leagues/(?:NBA|BAA)_\d{4}(?:_totals)?|playoffs/NBA_\d{4}_totals)\.html",
                self.href)
            if not (nba or bref):
                raise ValueError("external links must point to nba.com or an allowlisted Basketball-Reference source")
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
    field_decisions: list[FieldDecision] = Field(default_factory=list, max_length=14,
                                                 exclude_if=lambda value: not value)


# --------------------------------------------------------------------------
# Interpretation ("Reading this as")
# --------------------------------------------------------------------------

InterpretationField = Literal[
    "player", "team", "teams", "game", "date", "dates", "stat", "season", "round", "series", "game_number",
    "location", "aggregation", "season_type", "standings_scope",
]


class InterpretationItem(ContractModel):
    field: InterpretationField
    value: str = Field(min_length=1, max_length=140)  # "James Harden", "Last week"
    detail: str | None = Field(default=None, max_length=140)  # "CLE", "Mon, Feb 2 – Sun, Feb 8, 2026 · ET"
    expression: str | None = Field(default=None, max_length=140)  # the user's words, if different
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


class MeasureValues(ContractModel):
    """The same statistics in the other measure, computed from the same source row.

    Lets the card switch between per game and totals without a second request or a
    second source (docs/ask-stage2.md, "Measure toggle")."""

    aggregation: Aggregation
    values: list[StatValue] = Field(min_length=1, max_length=20)


def _check_alternate(aggregation: str, values: list[StatValue], alternate: MeasureValues | None) -> None:
    if alternate is None:
        return
    if alternate.aggregation == aggregation:
        raise ValueError("the alternate measure must differ from the shown measure")
    if [v.stat for v in alternate.values] != [v.stat for v in values]:
        raise ValueError("both measures list the same statistics")


class PlayerSeasonStatsResult(ContractModel):
    kind: Literal["player_season_stats"] = "player_season_stats"
    player: PlayerRef
    season: Season
    season_type: SeasonType
    # The measure shown first; `alternate` holds the other one when it differs.
    aggregation: Aggregation
    team: TeamRef | None = None
    games_played: int = Field(ge=1)
    values: list[StatValue] = Field(min_length=1)
    alternate: MeasureValues | None = None
    coverage_note: str | None = Field(default=None, max_length=300)
    as_of: dt.datetime

    @model_validator(mode="after")
    def _measures(self) -> PlayerSeasonStatsResult:
        _check_alternate(self.aggregation, self.values, self.alternate)
        return self


class TeamRecordRow(ContractModel):
    team: TeamRef
    wins: int = Field(ge=0)
    losses: int = Field(ge=0)
    win_percentage: float = Field(ge=0, le=1)
    conference: Conference | None = None
    conference_rank: int | None = Field(default=None, ge=1)


class TeamRecordsResult(ContractModel):
    kind: Literal["team_records"] = "team_records"
    season: Season
    team: TeamRef | None = None
    standings_scope: StandingsScope = "league"
    rows: list[TeamRecordRow] = Field(min_length=1, max_length=40)
    as_of: dt.datetime


class SeasonLeaderRow(ContractModel):
    rank: int = Field(ge=1)  # competition ranking on unrounded values; ties share a rank
    player: PlayerRef
    # None when the player had several teams (``multiple_teams``) or the franchise is
    # outside the catalog (defunct early teams). stats.nba lists a traded player's last team.
    team: TeamRef | None = None
    multiple_teams: bool = False
    games_played: int = Field(ge=1)
    value: StatValue


class OmittedTie(ContractModel):
    """A whole tie group left out because it would pass the row cap."""

    rank: int = Field(ge=1)
    count: int = Field(ge=2)


MAX_LEADER_ROWS = 50


class SeasonLeadersResult(ContractModel):
    kind: Literal["season_leaders"] = "season_leaders"
    season: Season
    season_type: SeasonType
    stat: StatKey
    aggregation: Aggregation
    limit: int = Field(ge=1, le=25)
    # Set when the question asked for more than 25 ("Showing the top 25, the most Ask lists.").
    limit_note: str | None = Field(default=None, max_length=120)
    qualification: Literal["all_players", "source_qualified"]
    qualification_note: str = Field(max_length=200)
    rows: list[SeasonLeaderRow] = Field(min_length=1, max_length=MAX_LEADER_ROWS)
    omitted_tie: OmittedTie | None = None
    coverage_note: str | None = Field(default=None, max_length=300)
    as_of: dt.datetime

    @model_validator(mode="after")
    def _ranked(self) -> SeasonLeadersResult:
        ranks = [row.rank for row in self.rows]
        if ranks[0] != 1 or any(r > self.limit for r in ranks):
            raise ValueError("rows must start at rank 1 and stay within the requested top N")
        for i in range(1, len(ranks)):
            if ranks[i] != ranks[i - 1] and ranks[i] != i + 1:
                raise ValueError("ranks must use competition ranking")
        if len({row.player.player_id for row in self.rows}) != len(self.rows):
            raise ValueError("a player appears once")
        return self


class CareerLeaderRow(ContractModel):
    rank: int = Field(ge=1)  # the source's competition rank; ties share a rank
    player: PlayerRef
    active: bool
    value: StatValue


CAREER_LIST_SIZE = 250


class CareerStatsResult(ContractModel):
    """One of three views (ADR 0013): a player's career line, the all-time top N,
    or a player's all-time rank in NBA.com's top 250."""

    kind: Literal["career_stats"] = "career_stats"
    view: CareerView
    season_type: SeasonType
    stat: Stat
    aggregation: Aggregation
    player: PlayerRef | None = None
    # player_totals
    games_played: int | None = Field(default=None, ge=1)
    values: list[StatValue] = Field(default_factory=list, max_length=20)
    alternate: MeasureValues | None = None  # player_totals: the other measure, same source row
    # leaders
    limit: int | None = Field(default=None, ge=1, le=25)
    limit_note: str | None = Field(default=None, max_length=120)
    rows: list[CareerLeaderRow] = Field(default_factory=list, max_length=MAX_LEADER_ROWS)
    omitted_tie: OmittedTie | None = None
    # player_rank: rank None means outside the list of ``list_size`` ranks.
    rank: int | None = Field(default=None, ge=1)
    tied_count: int | None = Field(default=None, ge=2)
    list_size: int | None = None
    coverage_note: str | None = Field(default=None, max_length=300)
    as_of: dt.datetime

    @model_validator(mode="after")
    def _view_payload(self) -> CareerStatsResult:
        totals, leaders, rank = (self.view == v for v in ("player_totals", "leaders", "player_rank"))
        if leaders != (self.player is None):
            raise ValueError("only the leaders view has no player")
        if totals != (self.games_played is not None) or (totals and not self.values):
            raise ValueError("player_totals needs games_played and values")
        if leaders != bool(self.rows) or leaders != (self.limit is not None) or (leaders and self.values):
            raise ValueError("rows and limit are required iff view is leaders")
        if rank != (self.list_size is not None) or (not rank and (self.rank or self.tied_count)):
            raise ValueError("rank fields belong to the player_rank view")
        if rank and (self.rank is not None) != (len(self.values) == 1):
            raise ValueError("a ranked player has exactly one listed value")
        if self.tied_count is not None and self.rank is None:
            raise ValueError("tied_count needs a rank")
        if self.alternate is not None and not totals:
            raise ValueError("only a career line has a measure toggle")
        _check_alternate(self.aggregation, self.values, self.alternate)
        return self


AskResult = Annotated[
    Union[GamesResult, BoxscoreStatResult, PlayoffSeriesResult, PostseasonSummaryResult, PlayerSeasonStatsResult, TeamRecordsResult, SeasonLeadersResult, CareerStatsResult],
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
    prompt: str = Field(max_length=140)  # "Which Jalen?"
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
                "player_season_stats": "player_season_stats",
                "team_records": "team_records",
                "season_leaders": "season_leaders",
                "career_stats": "career_stats",
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
    label: str = Field(max_length=140)  # "NYK @ BOS · Sun, Feb 23"
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
