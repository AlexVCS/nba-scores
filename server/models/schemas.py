from pydantic import BaseModel


class GameDaysResponse(BaseModel):
    year: int
    month: int
    season: str
    game_days: list[str]  # ["2026-02-01", "2026-02-03", ...]
    total: int


class RecentGameDaysResponse(BaseModel):
    before: str
    game_days: list[str]  # newest first
    total: int
