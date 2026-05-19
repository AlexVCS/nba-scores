from nba_api.stats.endpoints import leaguegamefinder


def fetch_playoff_team_games_df(season: str):
    games = leaguegamefinder.LeagueGameFinder(
        season_nullable=season,
        season_type_nullable="Playoffs",
        league_id_nullable="00",
    )

    return games.get_data_frames()[0]


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
                "gameId": game_id,
                "date": home_team["GAME_DATE"],
                "homeTeam": {
                    "id": int(home_team["TEAM_ID"]),
                    "abbreviation": home_team["TEAM_ABBREVIATION"],
                    "name": home_team["TEAM_NAME"],
                    "score": home_score,
                },
                "awayTeam": {
                    "id": int(away_team["TEAM_ID"]),
                    "abbreviation": away_team["TEAM_ABBREVIATION"],
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


def get_normalized_playoff_games(season: str):
    df = fetch_playoff_team_games_df(season)
    games = normalize_playoff_games(df)

    return {
        "season": season,
        "teamGameRowCount": len(df),
        "gameCount": len(games),
        "games": games,
    }