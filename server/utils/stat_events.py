"""NBA.com's rule for linking boxscore counting stats to its event pages.

Mirrors the box-score stat link component (chunk 78871-15eeb23af882c3f1.js,
module 35677) and the game-ID helper in _app-f31363c7185906d8.js, retrieved
2026-09-29. See docs/verification/stat-event-links-2026-09-29/ for excerpts.
The rule decides link eligibility only; it does not prove footage exists.
"""

SHOT_MEASURES = ("FGM", "FGA", "FG3M", "FG3A")
VIDEO_MEASURES = SHOT_MEASURES + ("OREB", "DREB", "REB", "AST", "STL", "BLK", "TOV")

# The Cup final (006) has no season type on NBA.com, so its links carry an
# empty SeasonType. Play-in drops the space NBA.com's own label uses.
SEASON_TYPES = {1: "Pre Season", 2: "Regular Season", 3: "All Star", 4: "Playoffs", 5: "PlayIn"}

VIDEO_FIRST_YEAR = 2014
SHOT_FIRST_YEAR = 2001
# Preseason shot charts start with 2017-18.
PRESEASON_SHOT_AFTER_YEAR = 2016

REGULATION_END_RANGE = 28800
OVERTIME_RANGE = 3000

VIDEO_FLAG = 1
SHOT_FLAG = 2


def _loosely_equals_one(value) -> bool:
    """Mirror JavaScript's ``value == 1`` for JSON values; never raises.

    Numbers and booleans compare by value and numeric strings are coerced.
    null, objects and arrays are treated as unequal (JS would coerce a
    one-element array, which NBA.com never sends).
    """
    if isinstance(value, (bool, int, float)):
        return value == 1
    if isinstance(value, str):
        # Python's float() also accepts digit separators, which JS rejects.
        if "_" in value:
            return False
        try:
            return float(value.strip()) == 1
        except ValueError:
            return False
    return False


def stat_events(game_id: str, wh_status, video_available_flag, overtime_periods: int) -> dict | None:
    """Return the event-page parameters shared by a game's stat links, or None.

    ``measures`` maps each linkable measure to NBA.com's ``flag`` (1 video,
    2 shot chart, 3 both) and omits measures without either.
    """
    # JS strict equality: 1.0 passes, "1" and True do not.
    if isinstance(wh_status, bool) or not isinstance(wh_status, (int, float)) or wh_status != 1 or not isinstance(game_id, str) or len(game_id) != 10 or not game_id.isdigit():
        return None
    if not game_id.startswith("00"):
        return None

    season_type_id = int(game_id[2])
    yy = int(game_id[3:5])
    year = 1900 + yy if yy >= 45 else 2000 + yy
    preseason = season_type_id == 1
    # NBA.com compares whStatus strictly but coerces videoAvailableFlag.
    has_video = _loosely_equals_one(video_available_flag) and year >= VIDEO_FIRST_YEAR
    has_shots = year >= SHOT_FIRST_YEAR and (not preseason or year > PRESEASON_SHOT_AFTER_YEAR)

    measures = {}
    for measure in VIDEO_MEASURES:
        flag = (VIDEO_FLAG if has_video else 0) + (SHOT_FLAG if has_shots and measure in SHOT_MEASURES else 0)
        if flag:
            measures[measure] = flag
    if not measures:
        return None

    return {
        "season": f"{year}-{str(year + 1)[-2:]}",
        "seasonType": SEASON_TYPES.get(season_type_id, ""),
        "endRange": REGULATION_END_RANGE + OVERTIME_RANGE * max(overtime_periods, 0),
        "measures": measures,
    }
