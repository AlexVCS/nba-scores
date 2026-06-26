from bs4 import BeautifulSoup, Comment
from fastapi import HTTPException
import requests
from nba_api.stats.endpoints import boxscoresummaryv2, boxscoretraditionalv3


BREF_TEAM_CODE_OVERRIDES = {
    "HUS": "TRH",
    "BOM": "STB",
    "DEF": "DTF",
    "WAS": "WSC",
}

BREF_REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    )
}

BREF_REQUEST_TIMEOUT_SECONDS = 2
BREF_LINE_SCORE_CACHE: dict[tuple[str, str], dict | None] = {}


def safe_score(pts):
    if (
        pts is None
        or str(pts) == "nan"
        or str(pts) == "None"
        or str(pts) == ""
    ):
        return "0"
    try:
        return str(int(float(pts)))
    except (ValueError, TypeError):
        return "0"


def safe_int(value):
    if (
        value is None
        or str(value) == "nan"
        or str(value) == "None"
        or str(value) == ""
    ):
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


def to_bref_team_code(team_tricode):
    return BREF_TEAM_CODE_OVERRIDES.get(str(team_tricode), str(team_tricode))


def from_bref_team_code(team_code):
    reverse_overrides = {v: k for k, v in BREF_TEAM_CODE_OVERRIDES.items()}
    return reverse_overrides.get(str(team_code), str(team_code))


def build_bref_boxscore_url(game_date_est, home_team_tricode):
    date_key = str(game_date_est)[:10].replace("-", "")
    return (
        "https://www.basketball-reference.com/boxscores/"
        f"{date_key}0{to_bref_team_code(home_team_tricode)}.html"
    )


def extract_bref_line_score(html):
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", id="line_score")

    if table is None:
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            if 'id="line_score"' not in comment:
                continue
            comment_soup = BeautifulSoup(comment, "html.parser")
            table = comment_soup.find("table", id="line_score")
            if table is not None:
                break

    if table is None:
        return None

    scores = {}
    for row in table.select("tbody tr"):
        team_cell = row.find(["th", "td"], attrs={"data-stat": "team"})
        if team_cell is None:
            continue

        team_code = from_bref_team_code(team_cell.get_text(strip=True))
        periods = []
        total = None

        for cell in row.find_all("td"):
            data_stat = cell.get("data-stat")
            score = safe_int(cell.get_text(strip=True))
            if data_stat == "T":
                total = score
                break
            if score is None:
                continue
            periods.append({"period": len(periods) + 1, "score": str(score)})

        if team_code and periods:
            scores[team_code] = {"periods": periods, "total": total}

    return scores or None


def fetch_bref_line_score(game_date_est, home_team_tricode):
    cache_key = (str(game_date_est)[:10], str(home_team_tricode))
    if cache_key in BREF_LINE_SCORE_CACHE:
        return BREF_LINE_SCORE_CACHE[cache_key]

    url = build_bref_boxscore_url(game_date_est, home_team_tricode)
    response = requests.get(
        url, headers=BREF_REQUEST_HEADERS, timeout=BREF_REQUEST_TIMEOUT_SECONDS
    )
    response.raise_for_status()
    line_score = extract_bref_line_score(response.text)
    BREF_LINE_SCORE_CACHE[cache_key] = line_score
    return line_score


def build_reliable_nba_periods(home_row, away_row, is_final=True):
    if is_final:
        home_periods = build_complete_periods(home_row)
        away_periods = build_complete_periods(away_row)
    else:
        home_periods = build_available_periods(home_row)
        away_periods = build_available_periods(away_row)

    if not period_sets_match(home_periods, away_periods):
        return None, None

    if period_scores_match_total(home_row, home_periods) and period_scores_match_total(
        away_row, away_periods
    ):
        return home_periods, away_periods

    return None, None


def build_complete_periods(row):
    periods = []
    for q in range(1, 5):
        score = safe_int(row.get(f"PTS_QTR{q}"))
        if score is None:
            return []
        periods.append({"period": q, "score": str(score)})

    for ot in range(1, 11):
        score = safe_int(row.get(f"PTS_OT{ot}"))
        if score is None or score == 0:
            continue
        if score < 0:
            return []
        periods.append({"period": 4 + ot, "score": str(score)})

    return periods


def build_available_periods(row):
    periods = []
    for q in range(1, 5):
        score = safe_int(row.get(f"PTS_QTR{q}"))
        if score is None:
            continue
        periods.append({"period": q, "score": str(score)})

    for ot in range(1, 11):
        score = safe_int(row.get(f"PTS_OT{ot}"))
        if score is None or score == 0:
            continue
        if score < 0:
            return []
        periods.append({"period": 4 + ot, "score": str(score)})

    return periods


def period_sets_match(home_periods, away_periods):
    if not home_periods or len(home_periods) != len(away_periods):
        return False
    return all(
        period["period"] == away_periods[index]["period"]
        for index, period in enumerate(home_periods)
    )


def period_scores_match_total(row, periods):
    total = safe_int(row.get("PTS"))
    if total is None or not periods:
        return False

    period_total = sum(safe_int(period["score"]) or 0 for period in periods)
    return period_total == total


def bref_period_scores_match_total(expected_total, bref_team_score):
    total = safe_int(expected_total)
    if total is None or not bref_team_score:
        return False

    periods = bref_team_score.get("periods")
    if not periods:
        return False

    period_total = 0
    for period in periods:
        score = safe_int(period.get("score"))
        if score is None:
            return False
        period_total += score

    if period_total != total:
        return False

    bref_total = bref_team_score.get("total")
    if bref_total is not None and safe_int(bref_total) != total:
        return False

    return True


def build_reliable_bref_periods(home_row, away_row, bref_line_score):
    if not bref_line_score:
        return None, None

    home_bref = bref_line_score.get(home_row["TEAM_ABBREVIATION"])
    away_bref = bref_line_score.get(away_row["TEAM_ABBREVIATION"])
    if not home_bref or not away_bref:
        return None, None

    home_periods = home_bref.get("periods")
    away_periods = away_bref.get("periods")
    if not period_sets_match(home_periods, away_periods):
        return None, None

    if bref_period_scores_match_total(
        home_row.get("PTS"), home_bref
    ) and bref_period_scores_match_total(away_row.get("PTS"), away_bref):
        return home_periods, away_periods

    return None, None


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


def get_status_period(status_id, live_period, home_periods, away_periods):
    period = safe_int(live_period) or 0

    if status_id != 3:
        return period

    if period_sets_match(home_periods, away_periods):
        return max(safe_int(period_score.get("period")) or 0 for period_score in home_periods)

    return period


def get_team_name(row):
    city = row.get("TEAM_CITY_NAME", "")
    nickname = (
        row.get("TEAM_NAME")
        if "TEAM_NAME" in row.index
        else row.get("TEAM_NICKNAME", "")
    )
    return f"{city} {nickname}".strip()


def make_scheduled_response(home_id, away_id):
    return {
        "homeTeam": {
            "teamId": int(home_id),
            "teamTricode": "",
            "teamName": "",
            "score": "0",
            "periods": [],
        },
        "awayTeam": {
            "teamId": int(away_id),
            "teamTricode": "",
            "teamName": "",
            "score": "0",
            "periods": [],
        },
        "gameStatusText": "Scheduled",
        "period": 0,
        "periodScoreSource": "unavailable",
        "periodScoreType": "quarters",
    }


def fetch_boxscoretraditional(game_id: str):
    box = boxscoretraditionalv3.BoxScoreTraditionalV3(
        game_id=game_id,
        range_type=0,
        start_period=0,
        end_period=10,
        start_range=0,
        end_range=0,
    )
    data = box.get_dict()
    game = data.get("boxScoreTraditional")
    if not game or not game.get("homeTeam") or not game.get("awayTeam"):
        raise ValueError("BoxscoreTraditionalV3 returned no usable game data")
    return game


def fetch_game_summary(game_id: str):
    summary = boxscoresummaryv2.BoxScoreSummaryV2(game_id=game_id)
    game_summary_df = summary.game_summary.get_data_frame()
    if game_summary_df.empty:
        raise HTTPException(status_code=404, detail="Game not found")

    game_meta = game_summary_df.iloc[0]
    home_team_id = game_meta["HOME_TEAM_ID"]
    visitor_team_id = game_meta["VISITOR_TEAM_ID"]
    live_period = game_meta["LIVE_PERIOD"]
    game_status_id = game_meta["GAME_STATUS_ID"]
    fallback_linescore = summary.line_score.get_data_frame()
    game_linescore = fallback_linescore if not fallback_linescore.empty else None

    if game_linescore is None or game_linescore.empty:
        return make_scheduled_response(home_team_id, visitor_team_id)

    home_filtered = game_linescore[game_linescore["TEAM_ID"] == home_team_id]
    away_filtered = game_linescore[game_linescore["TEAM_ID"] == visitor_team_id]
    if home_filtered.empty or away_filtered.empty:
        return make_scheduled_response(home_team_id, visitor_team_id)

    home_row = home_filtered.iloc[0]
    away_row = away_filtered.iloc[0]
    home_pts = home_row.get("PTS", 0)
    away_pts = away_row.get("PTS", 0)
    home_periods, away_periods = build_reliable_nba_periods(
        home_row, away_row, game_status_id == 3
    )
    period_score_source = "nba"

    if home_periods is None or away_periods is None:
        period_score_source = "unavailable"
        home_periods = []
        away_periods = []
        try:
            bref_line_score = fetch_bref_line_score(
                game_meta["GAME_DATE_EST"], home_row["TEAM_ABBREVIATION"]
            )
            home_bref_periods, away_bref_periods = build_reliable_bref_periods(
                home_row, away_row, bref_line_score
            )
            if home_bref_periods is not None and away_bref_periods is not None:
                home_periods = home_bref_periods
                away_periods = away_bref_periods
                period_score_source = "basketball-reference"
        except Exception as e:
            print(f"Basketball-Reference fallback failed for {game_id}: {e}")

    return {
        "homeTeam": {
            "teamId": int(home_row["TEAM_ID"]),
            "teamTricode": home_row["TEAM_ABBREVIATION"],
            "teamName": get_team_name(home_row),
            "score": safe_score(home_pts),
            "periods": home_periods,
        },
        "awayTeam": {
            "teamId": int(away_row["TEAM_ID"]),
            "teamTricode": away_row["TEAM_ABBREVIATION"],
            "teamName": get_team_name(away_row),
            "score": safe_score(away_pts),
            "periods": away_periods,
        },
        "gameStatusText": get_game_status(
            game_status_id,
            get_status_period(game_status_id, live_period, home_periods, away_periods),
        ),
        "period": int(live_period) if live_period else 0,
        "periodScoreSource": period_score_source,
        "periodScoreType": "quarters",
    }
