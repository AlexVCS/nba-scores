from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from nba_api.stats.endpoints import (
    ScheduleLeagueV2,
    scoreboardv2,
    scoreboardv3,
)
from datetime import datetime
from .utils.season import get_nba_season
from .utils.boxscore_availability import (
    is_boxscore_available_metadata,
)
from .services.nba_schedule import get_game_days_in_month
from .models.schemas import GameDaysResponse
from .services.game_summary import fetch_boxscoretraditional, fetch_game_summary
from .services.playoffs import (
    get_normalized_playoff_games,
    fetch_playoff_team_games_df,
    get_playoff_games_and_series,
    get_playoff_series,
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://nba-scorez.onrender.com", "https://nbascorez.com", "http://localhost:5173", "https://nba-scores.fastapicloud.dev/"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def add_boxscore_availability_to_scoreboard(scoreboard, target_date):
    for game in scoreboard.get("games", []):
        game_date = str(game.get("gameTimeUTC") or target_date)[:10]
        game["boxscoreAvailable"] = is_boxscore_available_metadata(
            game.get("gameId"),
            game_date,
            game.get("gameStatus"),
        )
    return scoreboard


@app.get("/")
def get_v3_scoreboard(
    date: str = Query(
        default=None,
        description="Format: YYYY-MM-DD",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    ),
):
    try:
        target_date = date if date else datetime.now().strftime("%Y-%m-%d")
        board = scoreboardv3.ScoreboardV3(game_date=target_date, league_id="00")
        full_data = board.get_dict()
        return add_boxscore_availability_to_scoreboard(
            full_data["scoreboard"], target_date
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch ScoreboardV3: {str(e)}"
        )


@app.get("/games/{game_id}/boxscore")
def get_game_boxscore(game_id: str):
    try:
        return {"game": fetch_boxscoretraditional(game_id)}
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=f"Boxscore unavailable for game {game_id}: {str(e)}",
        )
    except Exception as e:
        print(f"Error fetching boxscore for {game_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch boxscore: {str(e)}"
        )


@app.get("/gamesummary/{game_id}")
def get_game_summary(game_id: str):
    try:
        return fetch_game_summary(game_id)
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching game summary for {game_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch game summary: {str(e)}"
        )


@app.get("/debug/linescore/{game_date}")
def debug_linescore(game_date: str):
    sb = scoreboardv2.ScoreboardV2(game_date=game_date)
    linescore_df = sb.line_score.get_data_frame()
    return {
        "columns": list(linescore_df.columns),
        "first_row": linescore_df.iloc[0].to_dict()
        if not linescore_df.empty
        else None,
    }


@app.get("/schedule")
def debug_schedule(
    season: str = Query(..., alias="Season"),
    league_id: str = Query("00", alias="LeagueID"),
):
    try:
        schedule = ScheduleLeagueV2(season=season, league_id=league_id)
        frames = schedule.get_data_frames()
        df = frames[0]
        date_col = None
        for candidate in ["gameDate", "gameDateTimeEst", "gameDateEst"]:
            if candidate in df.columns:
                date_col = candidate
                break
        if date_col is None:
            raise ValueError(
                f"Could not find date column. Columns: {df.columns.tolist()}"
            )
        dates = {str(raw)[:10] for raw in df[date_col].dropna().unique()}
        return {
            "season": season,
            "league_id": league_id,
            "total_game_days": len(dates),
            "game_dates": sorted(dates),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch schedule for {season}: {str(e)}",
        )


@app.get("/api/game-days", response_model=GameDaysResponse)
def game_days(
    year: int = Query(..., ge=2000, le=2100, description="Calendar year"),
    month: int = Query(..., ge=1, le=12, description="Month (1-12)"),
):
    season = get_nba_season(year, month)
    try:
        days = get_game_days_in_month(year, month)
    except Exception as e:
        print(f"ERROR in game_days: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch schedule from NBA API: {e}",
        )
    return GameDaysResponse(
        year=year,
        month=month,
        season=season,
        game_days=days,
        total=len(days),
    )

@app.get("/playoffs/raw")
def raw_playoff_games(season: str = "2023-24"):
    df = fetch_playoff_team_games_df(season)

    return {
        "season": season,
        "teamGameRowCount": len(df),
        "games": df.to_dict(orient="records"),
    }


@app.get("/playoffs")
def playoff_games(season: str = "2023-24"):
    return get_normalized_playoff_games(season)

@app.get("/playoffs/series")
def playoff_series(season: str = "2023-24"):
    try:
        return get_playoff_series(season)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/playoffs/full")
def playoff_games_and_series(season: str = "2023-24"):
    try:
        return get_playoff_games_and_series(season)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)