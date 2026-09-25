"""Response data is authored by Python calculators, never by the model."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AskQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    question: str = Field(min_length=1, max_length=300)


class AskField(BaseModel):
    label: str
    value: str | int | float | None
    spoiler: bool = True


class AskLink(BaseModel):
    label: str
    path: str = Field(pattern=r"^/(?:\?|games/\d+/boxscore|playoffs(?:[/?]|$))")
    spoiler: bool = True


class AskTeam(BaseModel):
    id: int
    tricode: str
    name: str


class AskGameTeam(BaseModel):
    model_config = ConfigDict(extra="allow")

    teamId: int
    teamName: str
    teamTricode: str
    score: int


class AskGame(BaseModel):
    """Scoreboard data consumed directly by the existing game-card component."""

    model_config = ConfigDict(extra="allow")

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
    homeTeam: AskGameTeam
    awayTeam: AskGameTeam


class AskItem(BaseModel):
    kind: Literal["game", "statistic", "series", "postseason"]
    title: str
    title_spoiler: bool = True
    fields: list[AskField] = Field(default_factory=list)
    links: list[AskLink] = Field(default_factory=list)
    context: str | None = None
    teams: list[AskTeam] = Field(default_factory=list)
    player_id: int | None = None
    game: AskGame | None = None


class AskResponse(BaseModel):
    status: Literal["ok", "unsupported", "needs_clarification", "not_found", "unavailable"]
    message: str | None = None
    items: list[AskItem] = Field(default_factory=list)
    interpretation: list[str] = Field(default_factory=list)
