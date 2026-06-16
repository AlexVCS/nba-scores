import json
import time
from collections import defaultdict
from datetime import date
from pathlib import Path

from fastapi import HTTPException
from nba_api.stats.endpoints import LeagueGameLog, boxscoresummaryv2, leaguegamefinder
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import ReadTimeout

from server.utils.season import get_nba_season

_CONFERENCES_JSON = (
    Path(__file__).resolve().parent.parent / "constants" / "nbaConferences.json"
)

with open(_CONFERENCES_JSON) as _f:
    CONFERENCES = json.load(_f)


EAST_TEAM_IDS: frozenset[int] = frozenset(CONFERENCES["east"])
WEST_TEAM_IDS: frozenset[int] = frozenset(CONFERENCES["west"])

# season -> (fetched_at_monotonic, df)
_df_cache: dict = {}

# game_id -> {team_id: points}, cached so each defensive repair is only fetched once.
_linescore_cache: dict = {}


def should_use_active_playoff_source(season: str, today: date | None = None) -> bool:
    today = today or date.today()
    current_season = get_nba_season(today.year, today.month)

    return season == current_season and today.month in {4, 5, 6}


def get_playoff_data_source(season: str, today: date | None = None) -> str:
    if should_use_active_playoff_source(season, today):
        return "league_game_finder"

    return "league_game_log"


def fetch_playoff_team_games_df(season: str, today: date | None = None):
    source = get_playoff_data_source(season, today)
    cache_key = (season, source)

    if cache_key in _df_cache:
        return _df_cache[cache_key]

    try:
        if source == "league_game_finder":
            games = leaguegamefinder.LeagueGameFinder(
                season_nullable=season,
                season_type_nullable="Playoffs",
                league_id_nullable="00",
            )
        else:
            games = LeagueGameLog(
                season=season,
                season_type_all_star="Playoffs",
                league_id="00",
            )
        df = games.get_data_frames()[0]
    except (ReadTimeout, RequestsConnectionError) as e:
        raise HTTPException(
            status_code=503,
            detail=f"NBA Stats API unavailable: {e}",
        ) from e

    _df_cache[cache_key] = df
    return df


def get_round_name(round_number: int):
    return {
        1: "First Round",
        2: "Conference Semifinals",
        3: "Conference Finals",
        4: "NBA Finals",
    }.get(round_number, f"Round {round_number}")


def get_matchup_key(game):
    """Create an order-independent key for a matchup."""
    tricodes = sorted(
        [
            game["homeTeam"]["tricode"],
            game["awayTeam"]["tricode"],
        ]
    )

    return "-".join(tricodes)


def get_matchup_team_id_key(game):
    """Create an order-independent team-id key for a matchup."""
    team_ids = sorted(
        [
            game["homeTeam"]["id"],
            game["awayTeam"]["id"],
        ]
    )

    return f"{team_ids[0]}-{team_ids[1]}"


def infer_round_from_game_id(game_id: str):
    """
    Extract playoff round from NBA playoff GAME_ID when possible.

    Some modern playoff GAME_ID values encode the round in positions 6:8.

    Examples:
        0042500101 -> round 1
        0042500211 -> round 2
        0042500311 -> round 3
        0042500401 -> round 4

    But older seasons may use IDs like:
        0040000001
        0040000087

    For those seasons, this function returns None.
    """
    try:
        round_code = int(game_id[6:8])
    except (TypeError, ValueError):
        return None

    if round_code in {1, 2, 3, 4}:
        return round_code

    return None


def infer_bracket_position_from_game_id(game_id: str):
    """
    Extract series bracket position from modern NBA playoff GAME_ID.

    Modern game IDs encode the series number within the round at position [8].
    This number reflects bracket order (e.g. 1v8 top, 4v5, 3v6, 2v7 bottom).
    Both conferences use separate numbering within the same round, so sorting
    by this value within each conference gives the correct bracket order.

    Returns None if the game ID is not a modern format (old sequential IDs
    like 0040000001 do not encode series position and should not use this).
    """
    # Only extract position for modern game IDs where round is encoded
    if infer_round_from_game_id(game_id) is None:
        return None

    try:
        return int(game_id[8])
    except (TypeError, ValueError, IndexError):
        return None


def can_use_game_id_round_code(games):
    """
    Check if GAME_ID round extraction works for all playoff games.

    Important:
    This intentionally returns False for seasons like 2000-01 where IDs are
    sequential-looking values such as 0040000001 and do not encode the round.
    """
    if not games:
        return False

    inferred_rounds = []

    for game in games:
        round_num = infer_round_from_game_id(game.get("gameId"))

        if round_num is None:
            return False

        inferred_rounds.append(round_num)

    # Basic sanity check:
    # A full NBA playoff dataset should usually include multiple rounds.
    # This avoids accidentally accepting a malformed GAME_ID pattern.
    return len(set(inferred_rounds)) > 1


def group_games_by_matchup(games):
    """Group games by unique matchup/series."""
    groups = {}

    for game in games:
        key = get_matchup_key(game)

        if key not in groups:
            groups[key] = []

        groups[key].append(game)

    return groups


def summarize_series(games):
    """
    Group games into playoff series and summarize teams, dates, wins, and winner.

    This function does not require 4 wins because older NBA first rounds were
    best-of-5, including the 2000-01 season.
    """
    matchup_groups = group_games_by_matchup(games)
    summaries = {}

    for matchup_key, series_games in matchup_groups.items():
        sorted_games = sorted(
            series_games,
            key=lambda game: (game["date"], game["gameId"]),
        )

        team_ids = set()

        for game in sorted_games:
            team_ids.add(game["homeTeam"]["id"])
            team_ids.add(game["awayTeam"]["id"])

        wins = defaultdict(int)

        for game in sorted_games:
            wins[game["winnerTeamId"]] += 1

        winner_team_id = None

        if wins:
            winner_team_id = max(wins.items(), key=lambda item: item[1])[0]

        summaries[matchup_key] = {
            "matchupKey": matchup_key,
            "games": sorted_games,
            "teamIds": team_ids,
            "wins": dict(wins),
            "winnerTeamId": winner_team_id,
            "startDate": sorted_games[0]["date"],
            "endDate": sorted_games[-1]["date"],
            "gameCount": len(sorted_games),
        }

    return summaries


def infer_rounds_from_bracket_progression(games):
    """
    Infer playoff rounds by following winners through the bracket.

    This fallback is meant for seasons where GAME_ID does not encode the round.

    Rule:
      - A series with no previous winning series feeding into it is Round 1.
      - If a series includes the winner of an earlier series, it must be after
        that earlier series.
      - Round = 1 + max(rounds of previous series whose winners appear in this
        series).

    Example for 2000-01:
      PHI beats IND in Round 1.
      TOR beats NYK in Round 1.
      PHI vs TOR is then inferred as Round 2.
    """
    if not games:
        return {}

    series_summaries = summarize_series(games)

    sorted_series = sorted(
        series_summaries.values(),
        key=lambda series: (
            series["startDate"],
            series["endDate"],
            series["matchupKey"],
        ),
    )

    round_assignments = {}

    for current_series in sorted_series:
        predecessor_rounds = []

        for previous_series in sorted_series:
            previous_key = previous_series["matchupKey"]

            if previous_key == current_series["matchupKey"]:
                continue

            if previous_key not in round_assignments:
                continue

            previous_winner_id = previous_series["winnerTeamId"]

            if previous_winner_id is None:
                continue

            previous_ended_before_current_started = (
                previous_series["endDate"] < current_series["startDate"]
            )

            previous_winner_in_current_series = (
                previous_winner_id in current_series["teamIds"]
            )

            if previous_ended_before_current_started and previous_winner_in_current_series:
                predecessor_rounds.append(round_assignments[previous_key])

        if predecessor_rounds:
            round_num = max(predecessor_rounds) + 1
        else:
            round_num = 1

        # Clamp to normal NBA playoff round range.
        # This protects against odd historical data without creating Round 5+.
        if round_num > 4:
            round_num = 4

        round_assignments[current_series["matchupKey"]] = round_num

    return round_assignments


def apply_rounds_to_games(games):
    """Infer and apply rounds to normalized playoff games."""
    if not games:
        return games

    games_with_rounds = []

    if can_use_game_id_round_code(games):
        for game in games:
            round_num = infer_round_from_game_id(game["gameId"])

            game_copy = game.copy()
            game_copy["round"] = round_num
            game_copy["roundName"] = get_round_name(round_num)

            games_with_rounds.append(game_copy)

        return games_with_rounds

    round_assignments = infer_rounds_from_bracket_progression(games)

    for game in games:
        matchup_key = get_matchup_key(game)
        round_num = round_assignments.get(matchup_key, 0)

        game_copy = game.copy()
        game_copy["round"] = round_num
        game_copy["roundName"] = get_round_name(round_num)

        games_with_rounds.append(game_copy)

    return sorted(
        games_with_rounds,
        key=lambda game: (game["date"], game["gameId"]),
    )


def determine_winner(home_team, away_team, home_score, away_score):
    """
    Determine the winning team for a game.

    The NBA Stats API exposes both a ``WL`` (win/loss) flag and ``PTS`` for each
    team. ``WL`` is the authoritative result, while score rows can occasionally
    be inconsistent depending on the NBA Stats source. We therefore prefer
    ``WL`` and only fall back to comparing scores when the flag is missing (it
    can be null for some very old or in-progress games).
    """
    home_wl = home_team.get("WL")
    away_wl = away_team.get("WL")

    if home_wl == "W" or away_wl == "L":
        return home_team
    if away_wl == "W" or home_wl == "L":
        return away_team

    return home_team if home_score > away_score else away_team


def normalize_playoff_games(df):
    normalized_games = []

    for game_id, group in df.groupby("GAME_ID"):
        if len(group) != 2:
            continue

        rows = group.to_dict(orient="records")
        first_team = rows[0]
        second_team = rows[1]

        if " vs. " in first_team["MATCHUP"]:
            home_team = first_team
            away_team = second_team
        else:
            home_team = second_team
            away_team = first_team

        home_score = int(home_team["PTS"])
        away_score = int(away_team["PTS"])

        winner_team = determine_winner(home_team, away_team, home_score, away_score)

        normalized_games.append(
            {
                "gameId": str(game_id),
                "date": home_team["GAME_DATE"],
                "round": 0,
                "roundName": "Round 0",
                "homeTeam": {
                    "id": int(home_team["TEAM_ID"]),
                    "tricode": home_team["TEAM_ABBREVIATION"],
                    "name": home_team["TEAM_NAME"],
                    "score": home_score,
                },
                "awayTeam": {
                    "id": int(away_team["TEAM_ID"]),
                    "tricode": away_team["TEAM_ABBREVIATION"],
                    "name": away_team["TEAM_NAME"],
                    "score": away_score,
                },
                "winnerTeamId": int(winner_team["TEAM_ID"]),
                "winnerTeamAbbreviation": winner_team["TEAM_ABBREVIATION"],
            }
        )

    return sorted(
        normalized_games,
        key=lambda game: (game["date"], game["gameId"]),
    )


def game_scores_disagree_with_winner(game):
    """
    True when a game's displayed scores contradict its (WL-derived) winner.

    LeagueGameLog is the normal historical/completed source and should already
    have correct final scores. This defensive check protects the active playoff
    window source, or any future source inconsistency, where a score row may
    contradict the WL flag.
    """
    winner_id = game.get("winnerTeamId")
    home = game["homeTeam"]
    away = game["awayTeam"]

    if winner_id == home["id"]:
        return home["score"] <= away["score"]
    if winner_id == away["id"]:
        return away["score"] <= home["score"]

    return False


def fetch_corrected_team_scores(game_id):
    """
    Fetch authoritative per-team final scores from boxscoresummaryv2.

    Returns ``{team_id: points}`` or ``None`` when the data is unavailable. Used
    only as a temporary defensive repair when the selected source's PTS values
    disagree with WL. Historical/completed playoff data normally comes from
    LeagueGameLog and should not need this correction.
    """
    if game_id in _linescore_cache:
        return _linescore_cache[game_id]

    try:
        line_score = boxscoresummaryv2.BoxScoreSummaryV2(
            game_id=game_id
        ).line_score.get_data_frame()
    except (ReadTimeout, RequestsConnectionError):
        return None

    scores = {}
    for _, row in line_score.iterrows():
        try:
            scores[int(row["TEAM_ID"])] = int(row["PTS"])
        except (TypeError, ValueError):
            continue

    if not scores:
        return None

    _linescore_cache[game_id] = scores
    return scores


def correct_game_scores(games):
    """
    Repair displayed scores for games whose PTS disagrees with the WL winner.

    Mutates and returns ``games``. The WL-derived ``winnerTeamId`` is left intact;
    only the points are overwritten with the real linescore. Games whose scores
    already agree with the winner are untouched, so the normal LeagueGameLog path
    makes zero extra API calls.
    """
    for game in games:
        if not game_scores_disagree_with_winner(game):
            continue

        corrected = fetch_corrected_team_scores(game["gameId"])
        if not corrected:
            continue

        for side in ("homeTeam", "awayTeam"):
            team = game[side]
            if team["id"] in corrected:
                team["score"] = corrected[team["id"]]

    return games


def get_series_key(game):
    team_ids = sorted(
        [
            game["homeTeam"]["id"],
            game["awayTeam"]["id"],
        ]
    )

    return f"R{game['round']}-{team_ids[0]}-{team_ids[1]}"


def _get_series_conference(series):
    """Determine which conference a series belongs to from team IDs."""
    for team in series.get("teams", []):
        tid = team.get("id")
        if tid in EAST_TEAM_IDS:
            return "East"
        if tid in WEST_TEAM_IDS:
            return "West"
    return "Finals"


def _game_id_sort_key(series, use_game_id_position):
    """
    Primary sort key for a series: bracket-position digit from game ID when
    available, otherwise earliest game date (string sort is fine here).
    """
    if use_game_id_position and series.get("games"):
        pos = infer_bracket_position_from_game_id(series["games"][0]["gameId"])
        if pos is not None:
            return (0, pos, "")
    earliest = (
        min(g["date"] for g in series["games"]) if series.get("games") else ""
    )
    return (1, 0, earliest + series.get("seriesKey", ""))


def _sort_series(series_list, use_game_id_position):
    return sorted(
        series_list,
        key=lambda s: _game_id_sort_key(s, use_game_id_position),
    )


def sort_by_bracket_progression(playoff_series, use_game_id_position):
    """
    Return playoff_series sorted so that within each conference/round, series
    that feed into the same next-round match are placed adjacent (correct
    visual bracket pairing).

    Algorithm (per conference, highest round down to round 1):
    - Highest round: sort by game_id bracket-position digit (or date).
    - Lower rounds: bucket each series by which next-round series its winner
      advanced into, order buckets by that next-round series' position, sort
      within each bucket by game_id bracket-position digit.
    - Unresolved series (no winner yet) are sorted by game_id and appended.
    """
    # Group by conference and round
    conf_round = defaultdict(lambda: defaultdict(list))
    for s in playoff_series:
        conf = "Finals" if s["round"] == 4 else _get_series_conference(s)
        conf_round[conf][s["round"]].append(s)

    # series_key -> set of participant team IDs; used to detect which next-round
    # series a winner advanced into (team membership is stable before a winner exists).
    series_team_ids = {
        s["seriesKey"]: {t["id"] for t in s["teams"]}
        for s in playoff_series
    }

    # conf -> {series_key -> visual position within its round}; consumed by
    # _sort_key to establish final bracket order across all conferences.
    conf_positions = {}

    for conf in ("West", "East", "Finals"):
        rounds_desc = sorted(conf_round[conf].keys(), reverse=True)
        if not rounds_desc:
            continue

        round_pos = {}  # series_key → position within round for THIS conference

        for round_num in rounds_desc:
            round_series = conf_round[conf][round_num]

            if round_num == rounds_desc[0]:
                # Top round: no parent series exists, so position comes solely from
                # the game_id bracket-position digit or earliest game date.
                ordered = _sort_series(round_series, use_game_id_position)
            else:
                # Group current-round series by which next-round series contains
                # their winner, then order those groups by the next-round position.
                next_round_series = conf_round[conf].get(round_num + 1, [])
                # bucket_key = the parent next-round series' position; keeps the two
                # feeder series visually adjacent beneath their parent in the bracket.
                buckets = defaultdict(list)
                # Series with no winner yet (or winner not matched in any next-round
                # series) are collected here and appended last.
                unassigned = []

                for s in round_series:
                    winner_id = s.get("winnerTeamId")
                    placed = False
                    if winner_id:
                        # Walk next-round series to find which one the winner joined.
                        for ns in next_round_series:
                            if winner_id in series_team_ids.get(ns["seriesKey"], set()):
                                # 999 is a sentinel: parent not yet positioned → sort bucket last.
                                bucket_key = round_pos.get(ns["seriesKey"], 999)
                                buckets[bucket_key].append(s)
                                placed = True
                                break
                    if not placed:
                        unassigned.append(s)

                ordered = []
                for bk in sorted(buckets.keys()):
                    ordered.extend(_sort_series(buckets[bk], use_game_id_position))
                # Unassigned series trail positioned buckets; sorted so their relative
                # order is still deterministic rather than arbitrary.
                ordered.extend(_sort_series(unassigned, use_game_id_position))

            for i, s in enumerate(ordered):
                # Record position so the next (lower) round can use it as a bucket
                # key to keep bracket alignment consistent across rounds.
                round_pos[s["seriesKey"]] = i

        conf_positions[conf] = round_pos

    def _sort_key(s):
        conf = "Finals" if s["round"] == 4 else _get_series_conference(s)
        pos = conf_positions.get(conf, {}).get(s["seriesKey"], 999)
        return (s["round"], pos)

    return sorted(playoff_series, key=_sort_key)


def derive_playoff_series(games):
    series_map = defaultdict(
        lambda: {
            "round": None,
            "roundName": None,
            "teams": {},
            "games": [],
            "wins": defaultdict(int),
        }
    )

    for game in games:
        series_key = get_series_key(game)

        series = series_map[series_key]
        series["round"] = game["round"]
        series["roundName"] = game["roundName"]

        home_team = game["homeTeam"]
        away_team = game["awayTeam"]

        series["teams"][home_team["id"]] = {
            "id": home_team["id"],
            "tricode": home_team["tricode"],
            "name": home_team["name"],
        }

        series["teams"][away_team["id"]] = {
            "id": away_team["id"],
            "tricode": away_team["tricode"],
            "name": away_team["name"],
        }

        series["games"].append(game)
        series["wins"][game["winnerTeamId"]] += 1

    playoff_series = []

    for series_key, series in series_map.items():
        wins = dict(series["wins"])

        winner_team_id = None
        winner_team_tricode = None

        # Do not require 4 wins. Older first rounds were best-of-5.
        if wins:
            winner_team_id = max(wins.items(), key=lambda item: item[1])[0]
            team = series["teams"][winner_team_id]
            winner_team_tricode = team["tricode"]

        sorted_games = sorted(
            series["games"],
            key=lambda game: (game["date"], game["gameId"]),
        )

        playoff_series.append(
            {
                "seriesKey": series_key,
                "round": series["round"],
                "roundName": series["roundName"],
                "teams": list(series["teams"].values()),
                "wins": wins,
                "winnerTeamId": winner_team_id,
                "winnerTeamTricode": winner_team_tricode,
                "gameCount": len(sorted_games),
                "games": sorted_games,
            }
        )

    use_game_id_position = can_use_game_id_round_code(games)
    return sort_by_bracket_progression(playoff_series, use_game_id_position)


def get_normalized_playoff_games(season: str):
    df = fetch_playoff_team_games_df(season)
    games = normalize_playoff_games(df)
    games = correct_game_scores(games)
    games = apply_rounds_to_games(games)

    return {
        "season": season,
        "teamGameRowCount": len(df),
        "gameCount": len(games),
        "games": games,
    }


def get_playoff_series(season: str):
    df = fetch_playoff_team_games_df(season)
    games = normalize_playoff_games(df)
    games = correct_game_scores(games)
    games = apply_rounds_to_games(games)
    playoff_series = derive_playoff_series(games)

    return {
        "season": season,
        "teamGameRowCount": len(df),
        "gameCount": len(games),
        "seriesCount": len(playoff_series),
        "series": playoff_series,
    }


def get_playoff_games_and_series(season: str):
    df = fetch_playoff_team_games_df(season)
    games = normalize_playoff_games(df)
    games = correct_game_scores(games)
    games = apply_rounds_to_games(games)
    playoff_series = derive_playoff_series(games)

    return {
        "season": season,
        "teamGameRowCount": len(df),
        "gameCount": len(games),
        "seriesCount": len(playoff_series),
        "games": games,
        "series": playoff_series,
    }
