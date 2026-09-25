import logging
import time
from datetime import date as calendar_date, datetime, timezone

import requests
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from requests.exceptions import RequestException
from server.services import nba_stats_client
from server.services.game_details import fetch_game_details
from server.services.last_matchups import fetch_last_matchups
from server.services.nba_stats_client import (
    UpstreamBadResponseError,
    UpstreamUnavailableError,
)
from .utils.season import get_nba_season
from .utils.boxscore_availability import (
    is_boxscore_available_metadata,
)
from .services.nba_schedule import (
    ScheduleLookupCooldownError,
    get_game_days_in_month,
    get_next_game_date,
    get_recent_game_days,
)
from .models.schemas import GameDaysResponse, RecentGameDaysResponse
from .models.ask_response import AskQuestion, AskResponse
from .services.game_summary import (
    fetch_boxscoretraditional,
    fetch_inactive_players,
    fetch_bref_line_score,
    fetch_game_summary,
)
from .services.playoffs import (
    get_normalized_playoff_games,
    fetch_playoff_team_games_df,
    get_playoff_games_and_series,
    get_playoff_series,
)

logger = logging.getLogger(__name__)
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://nba-scorez.onrender.com", "https://nbascorez.com", "http://localhost:5173", "https://api.nbascorez.com"],
    allow_origin_regex=r"^http://(?:127\.0\.0\.1|localhost|10(?:\.\d{1,3}){3}|192\.168(?:\.\d{1,3}){2}|172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2}):5173$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def normalize_leading_path_slashes(request, call_next):
    path = request.scope.get("path", "")
    if path.startswith("//"):
        request.scope["path"] = "/" + path.lstrip("/")
    return await call_next(request)


def add_boxscore_availability_to_scoreboard(scoreboard):
    for game in scoreboard.get("games", []):
        game["boxscoreAvailable"] = is_boxscore_available_metadata(
            game.get("gameId"),
            game.get("gameStatus"),
        )
    return scoreboard


def raise_upstream_http(error: UpstreamUnavailableError | UpstreamBadResponseError):
    status_code = 503 if isinstance(error, UpstreamUnavailableError) else 502
    raise HTTPException(status_code=status_code, detail=error.public_detail()) from error


@app.get("/healthz")
def healthz():
    return {
        "ok": True,
        "service": "nba-scores-api",
        "version": "0.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/ask", response_model=AskResponse)
def ask(question: AskQuestion, request: Request):
    from .services.ask import answer_question
    from .services.ask_limits import BudgetLimitError, RateLimitError

    try:
        # Proxy trust is configured in uvicorn; never trust arbitrary forwarded headers here.
        return answer_question(question.question, request.client.host if request.client else "unknown")
    except (BudgetLimitError, RateLimitError) as error:
        raise HTTPException(status_code=429, detail="Search has reached its request limit. Please try again later.", headers={"Retry-After": "60"}) from error


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
        scoreboard = nba_stats_client.fetch_scoreboard_v3(target_date)
        if not date and not scoreboard["games"]:
            try:
                scoreboard["nextGameDate"] = get_next_game_date(calendar_date.fromisoformat(target_date))
            except ScheduleLookupCooldownError:
                pass
            except Exception:
                logger.warning("Next game date unavailable", exc_info=True)
        return add_boxscore_availability_to_scoreboard(scoreboard)
    except (UpstreamUnavailableError, UpstreamBadResponseError) as e:
        raise_upstream_http(e)


@app.get("/games/{game_id}/details")
def get_game_details(game_id: str, date: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")):
    try:
        return fetch_game_details(game_id, date)
    except (UpstreamUnavailableError, UpstreamBadResponseError) as e:
        raise_upstream_http(e)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@app.get("/matchups")
def get_last_matchups(
    team_id: int = Query(alias="teamId"),
    opponent_id: int = Query(alias="opponentId"),
    before: calendar_date = Query(),
    limit: int = Query(default=4, ge=1, le=10),
):
    try:
        return fetch_last_matchups(team_id, opponent_id, before, limit)
    except (UpstreamUnavailableError, UpstreamBadResponseError) as e:
        raise_upstream_http(e)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/games/{game_id}/boxscore")
def get_game_boxscore(game_id: str):
    try:
        return {"game": fetch_boxscoretraditional(game_id)}
    except (UpstreamUnavailableError, UpstreamBadResponseError) as e:
        raise_upstream_http(e)
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


@app.get("/games/{game_id}/inactive-players")
def get_game_inactive_players(game_id: str):
    try:
        return fetch_inactive_players(game_id)
    except (UpstreamUnavailableError, UpstreamBadResponseError) as e:
        raise_upstream_http(e)
    except Exception as e:
        logger.warning("Inactive players unavailable for %s: %s", game_id, e)
        raise HTTPException(status_code=502, detail="Inactive players unavailable") from e


@app.get("/gamesummary/{game_id}")
def get_game_summary(game_id: str):
    try:
        return fetch_game_summary(game_id)
    except HTTPException:
        raise
    except (UpstreamUnavailableError, UpstreamBadResponseError) as e:
        raise_upstream_http(e)
    except Exception as e:
        print(f"Error fetching game summary for {game_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch game summary: {str(e)}"
        )


@app.get("/debug/linescore/{game_date}")
def debug_linescore(game_date: str):
    sb = nba_stats_client.fetch_scoreboard_v2(game_date)
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
        schedule = nba_stats_client.fetch_schedule_league_v2(
            season=season,
            league_id=league_id,
        )
        frames = schedule.get_data_frames()
        df = frames[0]
        date_col = None
        for candidate in ["GAME_DATE", "gameDate", "gameDateTimeEst", "gameDateEst"]:
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
    except (UpstreamUnavailableError, UpstreamBadResponseError) as e:
        raise_upstream_http(e)
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to parse schedule for {season}: {type(e).__name__}",
        )

@app.get("/api/game-days", response_model=GameDaysResponse)
def game_days(
    year: int = Query(..., ge=1946, le=2100, description="Calendar year"),
    month: int = Query(..., ge=1, le=12, description="Month (1-12)"),
):
    season = get_nba_season(year, month)
    try:
        days = get_game_days_in_month(year, month)
    except (UpstreamUnavailableError, UpstreamBadResponseError) as e:
        raise_upstream_http(e)
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

@app.get("/api/game-days/recent", response_model=RecentGameDaysResponse)
def recent_game_days(
    before: calendar_date = Query(..., description="Exclusive upper bound (YYYY-MM-DD)"),
    months: int = Query(12, ge=1, le=24, description="Calendar months to include, ending with before's month"),
):
    try:
        days = get_recent_game_days(before, months)
    except (UpstreamUnavailableError, UpstreamBadResponseError) as e:
        raise_upstream_http(e)
    except Exception as e:
        logger.exception("recent_game_days failed")
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch schedule from NBA API: {e}",
        )
    return RecentGameDaysResponse(
        before=before.isoformat(),
        game_days=days,
        total=len(days),
    )

@app.get("/playoffs/raw")
def raw_playoff_games(season: str = "2023-24"):
    try:
        df = fetch_playoff_team_games_df(season)
    except (UpstreamUnavailableError, UpstreamBadResponseError) as e:
        raise_upstream_http(e)

    return {
        "season": season,
        "teamGameRowCount": len(df),
        "games": df.to_dict(orient="records"),
    }


@app.get("/playoffs")
def playoff_games(season: str = "2023-24"):
    try:
        return get_normalized_playoff_games(season)
    except (UpstreamUnavailableError, UpstreamBadResponseError) as e:
        raise_upstream_http(e)

@app.get("/playoffs/series")
def playoff_series(season: str = "2023-24"):
    try:
        return get_playoff_series(season)
    except HTTPException:
        raise
    except (UpstreamUnavailableError, UpstreamBadResponseError) as e:
        raise_upstream_http(e)
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
    except (UpstreamUnavailableError, UpstreamBadResponseError) as e:
        raise_upstream_http(e)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
