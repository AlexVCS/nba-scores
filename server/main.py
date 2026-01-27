from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from nba_api.stats.endpoints import (
    boxscoresummaryv2,
    boxscoretraditionalv3,
    scoreboardv2,
    scoreboardv3,
)
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/")
def get_v3_scoreboard(
    date: str = Query(
        default=None, description="Format: YYYY-MM-DD", regex=r"^\d{4}-\d{2}-\d{2}$"
    ),
):
    try:
        # If no date is provided, use today's date
        target_date = date if date else datetime.now().strftime("%Y-%m-%d")

        board = scoreboardv3.ScoreboardV3(game_date=target_date, league_id="00")

        full_data = board.get_dict()

        return full_data["scoreboard"]

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch ScoreboardV3: {str(e)}"
        )


@app.get("/games/{game_id}/boxscore")
def get_game_boxscore(game_id: str):
    try:
        box = boxscoretraditionalv3.BoxScoreTraditionalV3(
            game_id=game_id,
            range_type=0,
            start_period=0,
            end_period=10,
            start_range=0,
            end_range=0,
        )

        data = box.get_dict()

        return {"game": data["boxScoreTraditional"]}
    except Exception as e:
        print(f"Error fetching boxscore for {game_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch boxscore: {str(e)}"
        )


@app.get("/gamesummary/{game_id}")
def get_game_summary(game_id: str):
    try:
        summary = boxscoresummaryv2.BoxScoreSummaryV2(game_id=game_id)
        game_summary_df = summary.game_summary.get_data_frame()

        if game_summary_df.empty:
            raise HTTPException(status_code=404, detail="Game not found")

        game_meta = game_summary_df.iloc[0]
        home_team_id = game_meta["HOME_TEAM_ID"]
        visitor_team_id = game_meta["VISITOR_TEAM_ID"]
        live_period = game_meta["LIVE_PERIOD"]
        game_status_id = game_meta["GAME_STATUS_ID"]

        raw_date = game_meta["GAME_DATE_EST"]
        game_date = str(raw_date)[:10]

        game_linescore = None
        linescore_source = None

        try:
            sb = scoreboardv2.ScoreboardV2(game_date=game_date)
            linescore_df = sb.line_score.get_data_frame()
            if not linescore_df.empty:
                filtered = linescore_df[linescore_df["GAME_ID"] == game_id]
                if not filtered.empty:
                    test_row = filtered[filtered["TEAM_ID"] == home_team_id].iloc[0]
                    has_data = (
                        test_row.get("PTS_QTR1") is not None
                        and str(test_row.get("PTS_QTR1")) != "nan"
                        and str(test_row.get("PTS_QTR1")) != "None"
                    )
                    if has_data:
                        game_linescore = filtered
                        linescore_source = "ScoreboardV2"
                    else:
                        print(
                            f"ScoreboardV2 has None values for {game_id}, will try fallback"
                        )
        except Exception as e:
            print(f"ScoreboardV2 failed for {game_id}: {e}")

        if game_linescore is None or game_linescore.empty:
            fallback_linescore = summary.line_score.get_data_frame()
            if not fallback_linescore.empty:
                game_linescore = fallback_linescore
                linescore_source = "BoxScoreSummaryV2"
                print(f"Using BoxScoreSummaryV2 fallback for {game_id}")

        if game_linescore is None or game_linescore.empty:
            print(f"No line score data available for {game_id}")
            return {
                "homeTeam": {
                    "teamId": int(home_team_id),
                    "teamTricode": "",
                    "teamName": "",
                    "score": "0",
                    "periods": [],
                },
                "awayTeam": {
                    "teamId": int(visitor_team_id),
                    "teamTricode": "",
                    "teamName": "",
                    "score": "0",
                    "periods": [],
                },
                "gameStatusText": "Scheduled",
                "period": 0,
            }

        def build_periods(row):
            periods = []
            for q in range(1, 5):
                col_name = f"PTS_QTR{q}"
                if col_name in row.index:
                    score = row[col_name]
                    if (
                        score is not None
                        and str(score) != "nan"
                        and str(score) != ""
                        and str(score) != "None"
                    ):
                        try:
                            periods.append(
                                {"period": q, "score": str(int(float(score)))}
                            )
                        except (ValueError, TypeError):
                            pass
            for ot in range(1, 11):
                col_name = f"PTS_OT{ot}"
                if col_name in row.index:
                    score = row[col_name]
                    if (
                        score is not None
                        and str(score) != "nan"
                        and str(score) != ""
                        and str(score) != "None"
                    ):
                        try:
                            score_int = int(float(score))
                            if score_int > 0:
                                periods.append(
                                    {"period": 4 + ot, "score": str(score_int)}
                                )
                        except (ValueError, TypeError):
                            pass
            return periods

        def get_game_status(status_id, period):
            if status_id == 3:
                if period > 4:
                    return f"Final/OT{period - 4}" if period > 5 else "Final/OT"
                return "Final"
            elif status_id == 2:
                if period > 4:
                    return f"OT{period - 4}"
                return f"Q{period}"
            else:
                return "Scheduled"

        home_row = game_linescore[game_linescore["TEAM_ID"] == home_team_id].iloc[0]
        away_row = game_linescore[game_linescore["TEAM_ID"] == visitor_team_id].iloc[0]

        home_pts = home_row.get("PTS", 0)
        away_pts = away_row.get("PTS", 0)

        def safe_score(pts):
            if pts is None or str(pts) == "nan" or str(pts) == "None" or str(pts) == "":
                return "0"
            try:
                return str(int(float(pts)))
            except (ValueError, TypeError):
                return "0"

        def get_team_name(row):
            city = row.get("TEAM_CITY_NAME", "")
            nickname = (
                row.get("TEAM_NAME")
                if "TEAM_NAME" in row.index
                else row.get("TEAM_NICKNAME", "")
            )
            return f"{city} {nickname}".strip()

        return {
            "homeTeam": {
                "teamId": int(home_row["TEAM_ID"]),
                "teamTricode": home_row["TEAM_ABBREVIATION"],
                "teamName": get_team_name(home_row),
                "score": safe_score(home_pts),
                "periods": build_periods(home_row),
            },
            "awayTeam": {
                "teamId": int(away_row["TEAM_ID"]),
                "teamTricode": away_row["TEAM_ABBREVIATION"],
                "teamName": get_team_name(away_row),
                "score": safe_score(away_pts),
                "periods": build_periods(away_row),
            },
            "gameStatusText": get_game_status(
                game_status_id, int(live_period) if live_period else 0
            ),
            "period": int(live_period) if live_period else 0,
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching game summary for {game_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch game summary: {str(e)}"
        )


@app.get("/debug/linescore/{game_date}")
def debug_linescore(game_date: str):
    """Debug endpoint - shows what columns ScoreboardV2 returns"""
    sb = scoreboardv2.ScoreboardV2(game_date=game_date)
    linescore_df = sb.line_score.get_data_frame()

    return {
        "columns": list(linescore_df.columns),
        "first_row": linescore_df.iloc[0].to_dict() if not linescore_df.empty else None,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
