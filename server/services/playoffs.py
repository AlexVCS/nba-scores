import json
import time
from collections import defaultdict
from datetime import date, timedelta
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

# (season, source) -> (fetched_at_monotonic, df)
_df_cache: dict = {}
_CURRENT_SEASON_TTL_SECONDS = 5 * 60

# game_id -> {team_id: points}, cached so each defensive repair is only fetched once.
_linescore_cache: dict = {}


def get_playoff_end_year(season: str) -> int:
    """Return the calendar year that contains the playoffs for a season."""
    if not isinstance(season, str):
        raise ValueError("Season must be a string in YYYY-YY format")

    parts = season.split("-")
    if len(parts) != 2 or not all(parts):
        raise ValueError(f"Invalid season format: {season!r}. Expected YYYY-YY")

    start_year, end_year_suffix = parts
    if (
        len(start_year) != 4
        or len(end_year_suffix) != 2
        or not start_year.isdigit()
        or not end_year_suffix.isdigit()
    ):
        raise ValueError(f"Invalid season format: {season!r}. Expected YYYY-YY")

    return int(start_year) + 1


def get_playoff_format(season: str, finals_round: int | None = None):
    playoff_year = get_playoff_end_year(season)

    if playoff_year <= 1948:
        era = "baa-runners-up-bracket"
        bracket_type = "hybrid"
        exact = False
        notes = ["Early BAA runners-up bracket; rendered as grouped historical rounds."]
    elif playoff_year == 1950:
        era = "three-division-transitional"
        bracket_type = "multi-division"
        exact = False
        notes = ["Three-division transitional format; exact source bracket can be ambiguous."]
    elif playoff_year == 1951:
        era = "1951-two-division-eight-team"
        bracket_type = "multi-division"
        exact = True
        notes = [
            "Two-division eight-team format with two-win first round targets and three-win division finals targets."
        ]
    elif playoff_year == 1952:
        era = "1952-two-division-eight-team"
        bracket_type = "multi-division"
        exact = True
        notes = [
            "Two-division eight-team format with two-win first round targets and three-win division finals targets."
        ]
    elif playoff_year == 1953:
        era = "1953-two-division-eight-team"
        bracket_type = "multi-division"
        exact = True
        notes = [
            "Two-division eight-team format with two-win first round targets and three-win division finals targets."
        ]
    elif playoff_year == 1954:
        era = "six-team-round-robin"
        bracket_type = "round-robin-plus-finals"
        exact = False
        notes = ["Division round-robin format; connectors are shown only when derivable."]
    elif 1955 <= playoff_year <= 1966:
        era = "six-team-bye"
        bracket_type = "multi-division"
        exact = True
        notes = ["Six-team format with first-place division byes."]
    elif 1967 <= playoff_year <= 1970:
        era = "eight-team-division"
        bracket_type = "multi-division"
        exact = True
        notes = ["Eight-team division format before conference naming."]
    elif 1971 <= playoff_year <= 1974:
        era = "eight-team-conference"
        bracket_type = "single-elimination"
        exact = True
        notes = ["Eight-team conference playoff format."]
    elif 1975 <= playoff_year <= 1976:
        era = "ten-team-bye"
        bracket_type = "single-elimination"
        exact = True
        notes = ["Ten-team playoff format with first-round byes."]
    elif 1977 <= playoff_year <= 1983:
        era = "twelve-team-bye"
        bracket_type = "single-elimination"
        exact = True
        notes = ["Twelve-team playoff format with first-round byes."]
    elif 1984 <= playoff_year <= 2002:
        era = "sixteen-team-best-of-five-first-round"
        bracket_type = "single-elimination"
        exact = True
        notes = ["Sixteen-team bracket with a best-of-five first round."]
    elif 2003 <= playoff_year <= 2019:
        era = "sixteen-team-best-of-seven"
        bracket_type = "single-elimination"
        exact = True
        notes = ["Sixteen-team bracket with all rounds best-of-seven."]
    elif playoff_year >= 2020:
        era = "modern-play-in-era"
        bracket_type = "single-elimination"
        exact = True
        notes = ["Play-in games are outside this playoff series endpoint."]
    else:
        era = "two-division-eight-team"
        bracket_type = "multi-division"
        exact = True
        notes = ["Two-division historical playoff format."]

    return {
        "era": era,
        "playoffYear": playoff_year,
        "finalsRound": finals_round,
        "bracketType": bracket_type,
        "supportsExactBracket": exact,
        "notes": notes,
    }


def get_target_wins(playoff_year: int, round_number: int, is_finals: bool):
    if playoff_year == 1954 and not is_finals:
        return None
    if is_finals:
        return 4
    if playoff_year <= 1950:
        return 2
    if 1951 <= playoff_year <= 1953:
        return 2 if round_number == 1 else 3
    if 1955 <= playoff_year <= 1960:
        return 2 if round_number == 1 else 4
    if 1961 <= playoff_year <= 1967:
        return 3 if round_number == 1 else 4
    if 1975 <= playoff_year <= 1983 and round_number == 1:
        return 2
    if 1984 <= playoff_year <= 2002 and round_number == 1:
        return 3
    return 4


def get_current_season(today: date | None = None) -> str:
    today = today or date.today()
    return get_nba_season(today.year, today.month)


def should_use_active_playoff_source(season: str, today: date | None = None) -> bool:
    current_season = get_current_season(today) if today else get_current_season()
    today = today or date.today()

    return season == current_season and today.month in {4, 5, 6}


def get_playoff_data_source(season: str, today: date | None = None) -> str:
    if should_use_active_playoff_source(season, today):
        return "league_game_finder"

    return "league_game_log"


def fetch_playoff_team_games_df(season: str, today: date | None = None):
    source = get_playoff_data_source(season, today)
    cache_key = (season, source)

    if cache_key in _df_cache:
        fetched_at, cached_df = _df_cache[cache_key]
        current_season = get_current_season(today) if today else get_current_season()
        if season != current_season:
            return cached_df

        age = time.monotonic() - fetched_at
        if age < _CURRENT_SEASON_TTL_SECONDS:
            return cached_df

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

    _df_cache[cache_key] = (time.monotonic(), df)
    return df


def get_round_name(round_number: int):
    return {
        1: "First Round",
        2: "Conference Semifinals",
        3: "Conference Finals",
        4: "NBA Finals",
    }.get(round_number, f"Round {round_number}")


def get_series_dates(series):
    games = series.get("games") or []
    if not games:
        return ("", "")
    dates = sorted(game["date"] for game in games)
    return (dates[0], dates[-1])


def get_finals_round(playoff_series):
    if not playoff_series:
        return None

    by_round = defaultdict(list)
    for series in playoff_series:
        by_round[series["round"]].append(series)

    max_round = max(by_round.keys())
    if len(by_round[max_round]) == 1:
        return max_round

    return None


def get_group_for_series(series, playoff_year: int, is_finals: bool):
    if is_finals:
        return {
            "id": "finals",
            "label": "NBA Finals",
            "kind": "finals",
            "sortOrder": 99,
        }

    conf = _get_series_conference(series)
    if conf in {"East", "West"}:
        if playoff_year < 1971:
            label = "Eastern Division" if conf == "East" else "Western Division"
            suffix = "division"
        else:
            label = "Eastern Conference" if conf == "East" else "Western Conference"
            suffix = "conference"
        return {
            "id": f"{conf.lower()}-{suffix}",
            "label": label,
            "kind": "division" if suffix == "division" else "conference",
            "sortOrder": 10 if conf == "West" else 20,
        }

    return {
        "id": "league",
        "label": "League Bracket",
        "kind": "league",
        "sortOrder": 30,
    }


def get_round_definitions(playoff_series):
    rounds = {}
    for series in playoff_series:
        round_number = series["round"]
        rounds[round_number] = {
            "round": round_number,
            "label": series.get("roundName") or get_round_name(round_number),
            "sortOrder": round_number,
            "defaultRevealed": round_number == 1,
        }

    return [rounds[key] for key in sorted(rounds)]


def get_advancement_edges(playoff_series):
    edges = []
    series_team_ids = {
        series["seriesKey"]: {team["id"] for team in series.get("teams", [])}
        for series in playoff_series
    }

    for source in playoff_series:
        winner_id = source.get("winnerTeamId")
        if not winner_id:
            continue

        _, source_end = get_series_dates(source)
        candidates = []

        for target in playoff_series:
            if target["seriesKey"] == source["seriesKey"]:
                continue
            if target["round"] <= source["round"]:
                continue
            if winner_id not in series_team_ids.get(target["seriesKey"], set()):
                continue

            target_start, _ = get_series_dates(target)
            if source_end and target_start and target_start < source_end:
                continue

            candidates.append(target)

        if not candidates:
            continue

        target = min(
            candidates,
            key=lambda series: (
                series["round"],
                get_series_dates(series)[0],
                series["seriesKey"],
            ),
        )
        edges.append(
            {
                "sourceSeriesKey": source["seriesKey"],
                "targetSeriesKey": target["seriesKey"],
                "winnerTeamId": winner_id,
            }
        )

    return edges


def enrich_playoff_bracket_response(season: str, playoff_series):
    finals_round = get_finals_round(playoff_series)
    playoff_format = get_playoff_format(season, finals_round)
    playoff_year = playoff_format["playoffYear"]
    groups_by_id = {}
    enriched_series = []

    for series in playoff_series:
        series_copy = {
            **series,
            "teams": list(series.get("teams", [])),
            "wins": dict(series.get("wins", {})),
            "games": list(series.get("games", [])),
        }
        is_finals = finals_round is not None and series_copy["round"] == finals_round
        group = get_group_for_series(series_copy, playoff_year, is_finals)
        groups_by_id[group["id"]] = group

        if is_finals:
            series_copy["roundName"] = "NBA Finals"

        series_copy["bracketGroupId"] = group["id"]
        series_copy["bracketGroupLabel"] = group["label"]
        series_copy["bracketGroupKind"] = group["kind"]
        series_copy["targetWins"] = get_target_wins(
            playoff_year,
            series_copy["round"],
            is_finals,
        )
        series_copy["isFinals"] = is_finals
        enriched_series.append(series_copy)

    grouped_positions = defaultdict(int)
    enriched_series.sort(
        key=lambda series: (
            series["round"],
            groups_by_id[series["bracketGroupId"]]["sortOrder"],
            get_series_dates(series)[0],
            series["seriesKey"],
        )
    )

    for series in enriched_series:
        key = (series["bracketGroupId"], series["round"])
        series["bracketOrder"] = grouped_positions[key]
        grouped_positions[key] += 1

    groups = sorted(groups_by_id.values(), key=lambda group: group["sortOrder"])

    return {
        "format": playoff_format,
        "groups": groups,
        "rounds": get_round_definitions(enriched_series),
        "edges": (
            get_advancement_edges(enriched_series)
            if playoff_format["supportsExactBracket"]
            else []
        ),
        "series": enriched_series,
    }


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
    # Only extract position for game IDs where round is encoded.
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


def get_game_team_id_pair(game):
    return tuple(
        sorted(
            [
                game["homeTeam"]["id"],
                game["awayTeam"]["id"],
            ]
        )
    )


def get_series_team_id_pair(series):
    return tuple(sorted(team["id"] for team in series.get("teams", [])))


def series_wins_for_games(games):
    wins = defaultdict(int)

    for game in games:
        winner_id = game.get("winnerTeamId")
        if winner_id is not None:
            wins[winner_id] += 1

    return dict(wins)


def get_series_target_wins_for_round(season, round_number, is_finals):
    playoff_year = get_playoff_end_year(season)
    return get_target_wins(playoff_year, round_number, is_finals)


def _date_from_iso(date_value):
    return date.fromisoformat(date_value)


def _series_start_date(series):
    return get_series_dates(series)[0]


def is_valid_orphan_merge(season, orphan_series, target_series, all_series):
    if get_series_team_id_pair(orphan_series) != get_series_team_id_pair(target_series):
        return False

    if orphan_series["gameCount"] != 1:
        return False

    if target_series["gameCount"] < 1:
        return False

    if target_series["round"] <= orphan_series["round"]:
        return False

    if target_series["round"] - orphan_series["round"] > 2:
        return False

    orphan_games = orphan_series.get("games", [])
    target_games = target_series.get("games", [])
    if len(orphan_games) != 1 or not target_games:
        return False

    orphan_game = orphan_games[0]
    team_pair = set(get_series_team_id_pair(target_series))
    if orphan_game.get("winnerTeamId") not in team_pair:
        return False

    target_start, target_end = get_series_dates(target_series)
    if not target_start or not target_end:
        return False

    orphan_date = _date_from_iso(orphan_game["date"])
    start_date = _date_from_iso(target_start)
    end_date = _date_from_iso(target_end)
    tolerance = timedelta(days=3)

    if orphan_date < start_date - tolerance or orphan_date > end_date + tolerance:
        return False

    initial_finals_round = get_finals_round(all_series)
    is_target_finals = (
        initial_finals_round is not None
        and target_series["round"] == initial_finals_round
    )
    target_wins = get_series_target_wins_for_round(
        season,
        target_series["round"],
        is_target_finals,
    )

    if target_wins is None:
        return False

    merged_games = orphan_games + target_games
    merged_count = len(merged_games)
    if merged_count > (2 * target_wins - 1):
        return False

    merged_wins = series_wins_for_games(merged_games)
    if not merged_wins or max(merged_wins.values()) != target_wins:
        return False

    win_values = list(merged_wins.values())
    if len(win_values) == 2 and win_values[0] == win_values[1]:
        return False

    return True


def _orphan_target_sort_key(orphan_series, target_series):
    orphan_start = _date_from_iso(_series_start_date(orphan_series))
    target_start = _date_from_iso(_series_start_date(target_series))
    date_distance = abs((target_start - orphan_start).days)

    return (
        target_series["round"],
        date_distance,
        target_series["seriesKey"],
    )


def find_orphan_series_merges(season, playoff_series):
    by_team_pair = defaultdict(list)

    for series in playoff_series:
        by_team_pair[get_series_team_id_pair(series)].append(series)

    orphan_round_updates = {}

    for same_pair_series in by_team_pair.values():
        if len(same_pair_series) < 2:
            continue

        ordered_series = sorted(
            same_pair_series,
            key=lambda series: (
                series["round"],
                _series_start_date(series),
                series["seriesKey"],
            ),
        )

        for orphan_series in ordered_series:
            if orphan_series["gameCount"] != 1:
                continue

            valid_targets = [
                target_series
                for target_series in ordered_series
                if is_valid_orphan_merge(
                    season,
                    orphan_series,
                    target_series,
                    playoff_series,
                )
            ]

            if not valid_targets:
                continue

            target_series = min(
                valid_targets,
                key=lambda series: _orphan_target_sort_key(orphan_series, series),
            )
            orphan_round_updates[orphan_series["seriesKey"]] = target_series["round"]

    return orphan_round_updates


def reconcile_duplicate_matchup_rounds(season, games):
    playoff_series = derive_playoff_series(games)
    orphan_round_updates = find_orphan_series_merges(season, playoff_series)

    if not orphan_round_updates:
        return games

    reconciled_games = []

    for game in games:
        series_key = get_series_key(game)

        if series_key not in orphan_round_updates:
            reconciled_games.append(game)
            continue

        round_num = orphan_round_updates[series_key]
        game_copy = game.copy()
        game_copy["round"] = round_num
        game_copy["roundName"] = get_round_name(round_num)
        reconciled_games.append(game_copy)

    return sorted(
        reconciled_games,
        key=lambda game: (game["date"], game["gameId"]),
    )


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
    games = reconcile_duplicate_matchup_rounds(season, games)

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
    games = reconcile_duplicate_matchup_rounds(season, games)
    playoff_series = derive_playoff_series(games)
    bracket = enrich_playoff_bracket_response(season, playoff_series)

    return {
        "season": season,
        "teamGameRowCount": len(df),
        "gameCount": len(games),
        "seriesCount": len(playoff_series),
        "format": bracket["format"],
        "groups": bracket["groups"],
        "rounds": bracket["rounds"],
        "edges": bracket["edges"],
        "series": bracket["series"],
    }


def get_playoff_games_and_series(season: str):
    df = fetch_playoff_team_games_df(season)
    games = normalize_playoff_games(df)
    games = correct_game_scores(games)
    games = apply_rounds_to_games(games)
    games = reconcile_duplicate_matchup_rounds(season, games)
    playoff_series = derive_playoff_series(games)
    bracket = enrich_playoff_bracket_response(season, playoff_series)

    return {
        "season": season,
        "teamGameRowCount": len(df),
        "gameCount": len(games),
        "seriesCount": len(playoff_series),
        "games": games,
        "format": bracket["format"],
        "groups": bracket["groups"],
        "rounds": bracket["rounds"],
        "edges": bracket["edges"],
        "series": bracket["series"],
    }
