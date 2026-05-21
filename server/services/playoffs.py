from collections import defaultdict

from nba_api.stats.endpoints import leaguegamefinder


def fetch_playoff_team_games_df(season: str):
    games = leaguegamefinder.LeagueGameFinder(
        season_nullable=season,
        season_type_nullable="Playoffs",
        league_id_nullable="00",
    )

    return games.get_data_frames()[0]


def get_round_from_game_id(game_id):
    game_id = str(game_id)

    return int(game_id[5])


def get_round_name(round_number: int):
    return {
        1: "First Round",
        2: "Conference Semifinals",
        3: "Conference Finals",
        4: "NBA Finals",
    }.get(round_number, f"Round {round_number}")


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
        round_number = get_round_from_game_id(game_id)

        normalized_games.append(
            {
                "gameId": game_id,
                "date": home_team["GAME_DATE"],
                "round": round_number,
                "roundName": get_round_name(round_number),
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

        for team_id, win_count in wins.items():
            if win_count >= 4:
                winner_team_id = team_id

                team = series["teams"][team_id]
                winner_team_tricode = team["tricode"]

                break

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

    return {
        "season": season,
        "teamGameRowCount": len(df),
        "gameCount": len(games),
        "games": games,
    }


def get_playoff_series(season: str):
    df = fetch_playoff_team_games_df(season)
    games = normalize_playoff_games(df)
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
    playoff_series = derive_playoff_series(games)

    return {
        "season": season,
        "teamGameRowCount": len(df),
        "gameCount": len(games),
        "seriesCount": len(playoff_series),
        "games": games,
        "series": playoff_series,
    }