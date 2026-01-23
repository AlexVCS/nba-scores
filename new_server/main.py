from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from nba_api.stats.endpoints import scoreboardv3, boxscoretraditionalv3
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

@app.get("/test")
def test_route():
    return {
        "version": "2.0-testing-routes", 
        "status": "alive",
        "message": "If you see this, the new code is deployed"
    }

@app.get("/")
def get_v3_scoreboard(
    date: str = Query(
        default=None, 
        description="Format: YYYY-MM-DD",
        regex=r"^\d{4}-\d{2}-\d{2}$"
    )
):
    try:
        # If no date is provided, use today's date
        target_date = date if date else datetime.now().strftime("%Y-%m-%d")

        board = scoreboardv3.ScoreboardV3(
            game_date=target_date,
            league_id="00"
        )

        full_data = board.get_dict()
        
        return full_data["scoreboard"]

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch ScoreboardV3: {str(e)}"
        )
        
@app.get("/games/{game_id}/boxscore")
def get_game_boxscore(game_id: str):
    try:
        # Get player stats
        box = boxscoretraditionalv3.BoxScoreTraditionalV3(
            game_id=game_id,
            range_type=0,
            start_period=0,
            end_period=10,
            start_range=0,
            end_range=0
        )
        
        data = box.get_dict()
        
        
        return {
            "game": data["boxScoreTraditional"]
        }
    except Exception as e:
        print(f"Error fetching boxscore for {game_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch boxscore: {str(e)}"
        )   

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)