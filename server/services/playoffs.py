from collections import defaultdict

from nba_api.stats.endpoints import leaguegamefinder


def fetch_playoff_team_games_df(season: str):
    games = leaguegamefinder.LeagueGameFinder(
        season_nullable=season,
        season_type_nullable="Playoffs",
        league_id_nullable="00",
    )

    return games.get_data_frames()[0]


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

        winner_team = home_team if home_score > away_score else away_team

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


def get_series_key(game):
    team_ids = sorted(
        [
            game["homeTeam"]["id"],
            game["awayTeam"]["id"],
        ]
    )

    return f"R{game['round']}-{team_ids[0]}-{team_ids[1]}"


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

        playoff_series.append(
            {
                "seriesKey": series_key,
                "round": series["round"],
                "roundName": series["roundName"],
                "teams": list(series["teams"].values()),
                "wins": wins,
                "winnerTeamId": winner_team_id,
                "winnerTeamTricode": winner_team_tricode,
                "gameCount": len(series["games"]),
                "games": sorted(
                    series["games"],
                    key=lambda game: (game["date"], game["gameId"]),
                ),
            }
        )

    return sorted(
        playoff_series,
        key=lambda series: (
            series["round"],
            min(game["date"] for game in series["games"]),
            series["seriesKey"],
        ),
    )


def get_normalized_playoff_games(season: str):
    df = fetch_playoff_team_games_df(season)
    games = normalize_playoff_games(df)
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