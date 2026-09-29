"""Offline fixtures for the resolver tests: scoreboards, boxscores, player game
logs and playoff game logs. Holds no tests; the file name keeps it inside the
#201 test prefix."""

from datetime import date, timedelta

import pandas as pd
import pytest

from server.ask.models.response import AskResponse
from server.ask.resolvers import data
from server.services import nba_stats_client
from server.services import playoffs as playoffs_service

TEAMS = {
    "BOS": (1610612738, "Boston", "Celtics"),
    "MIA": (1610612748, "Miami", "Heat"),
    "CLE": (1610612739, "Cleveland", "Cavaliers"),
    "IND": (1610612754, "Indiana", "Pacers"),
    "DAL": (1610612742, "Dallas", "Mavericks"),
    "LAC": (1610612746, "LA", "Clippers"),
    "OKC": (1610612760, "Oklahoma City", "Thunder"),
    "MIN": (1610612750, "Minnesota", "Timberwolves"),
    "NYK": (1610612752, "New York", "Knicks"),
}


def tid(tricode):
    return TEAMS[tricode][0]


def sb_team(tricode, score=0):
    team_id, city, name = TEAMS[tricode]
    return {"teamId": team_id, "teamCity": city, "teamName": name, "teamTricode": tricode, "score": score}


def sb_game(game_id, home, away, *, status=3, home_score=110, away_score=100, period=4, status_text=None,
            label="", series_number="", series_text=""):
    return {
        "gameId": game_id,
        "gameCode": "",
        "gameStatus": status,
        "gameStatusText": status_text or {1: "7:30 pm ET", 2: "Q3 5:12", 3: "Final"}[status],
        "period": period if status != 1 else 0,
        "gameLabel": label,
        "gameSubLabel": "",
        "seriesGameNumber": series_number,
        "seriesText": series_text,
        "homeTeam": sb_team(home, home_score if status != 1 else 0),
        "awayTeam": sb_team(away, away_score if status != 1 else 0),
    }


class FakeScoreboards:
    """Stands in for nba_stats_client.fetch_scoreboard_v3 and records calls."""

    def __init__(self, boards=None, failing=()):
        self.boards = dict(boards or {})
        self.failing = set(failing)
        self.calls = []

    def __call__(self, game_date, league_id="00"):
        self.calls.append(game_date)
        if game_date in self.failing:
            raise nba_stats_client.UpstreamUnavailableError("ScoreboardV3", "Timeout", 10)
        return {"games": list(self.boards.get(game_date, []))}


def player(person_id, first, family, minutes="30:00", comment="", status="ACTIVE", **stats):
    return {"personId": person_id, "firstName": first, "familyName": family, "nameI": f"{first[0]}. {family}",
            "comment": comment, "status": status, "statistics": {"minutes": minutes, **stats}}


def boxscore(game_id, home, away, home_players, away_players, home_stats=None, away_stats=None):
    def side(tricode, players, stats):
        team_id, city, name = TEAMS[tricode]
        return {"teamId": team_id, "teamCity": city, "teamName": name, "teamTricode": tricode,
                "players": players, "statistics": stats or {}}

    return {"gameId": game_id, "homeTeam": side(home, home_players, home_stats),
            "awayTeam": side(away, away_players, away_stats)}


class FakeBoxscores:
    def __init__(self, games=None, failing=()):
        self.games = dict(games or {})
        self.failing = set(failing)
        self.calls = []

    def __call__(self, game_id):
        self.calls.append(game_id)
        if game_id in self.failing:
            raise nba_stats_client.UpstreamUnavailableError("BoxScoreTraditionalV3", "Timeout", 10)
        return {"boxScoreTraditional": self.games.get(game_id)}


class FakeFinder:
    """Stands in for fetch_league_game_finder; rows keyed by (player ID, MM/DD/YYYY)."""

    def __init__(self, rows=None, error=None):
        self.rows = dict(rows or {})
        self.error = error
        self.calls = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        rows = self.rows.get((kwargs["player_id_nullable"], kwargs["date_from_nullable"]), [])

        class Response:
            def get_normalized_dict(self):
                return {"LeagueGameFinderResults": rows}

        return Response()


def playoff_rows(series_specs, season_code="23", start=date(2024, 4, 20)):
    """LeagueGameLog-style team rows. Each spec is
    (round, position, team_a, team_b, results_for_a, first_day_offset).
    Team A hosts games 1, 2, 5 and 7; the winner scores 110, the loser 100."""
    rows = []
    for round_number, position, team_a, team_b, results, offset in series_specs:
        for index, result in enumerate(results):
            game_id = playoff_game_id(round_number, position, index + 1, season_code)
            day = (start + timedelta(days=offset + 2 * index)).isoformat()
            home, away = (team_a, team_b) if index in (0, 1, 4, 6) else (team_b, team_a)
            for tricode, is_home in ((home, True), (away, False)):
                won = (tricode == team_a) == (result == "W")
                opponent = away if is_home else home
                rows.append({
                    "GAME_ID": game_id,
                    "GAME_DATE": day,
                    "MATCHUP": f"{tricode} vs. {opponent}" if is_home else f"{tricode} @ {opponent}",
                    "TEAM_ID": tid(tricode),
                    "TEAM_ABBREVIATION": tricode,
                    "TEAM_NAME": " ".join(TEAMS[tricode][1:]),
                    "WL": "W" if won else "L",
                    "PTS": 110 if won else 100,
                })
    columns = ["GAME_ID", "GAME_DATE", "MATCHUP", "TEAM_ID", "TEAM_ABBREVIATION", "TEAM_NAME", "WL", "PTS"]
    return pd.DataFrame(rows, columns=columns)


def playoff_game_id(round_number, position, game_number, season_code="23"):
    return f"004{season_code}00{round_number}{position}{game_number}"


def playoff_day(offset, game_number, start=date(2024, 4, 20)):
    return start + timedelta(days=offset + 2 * (game_number - 1))


# A complete 2024 postseason: Boston beats Dallas 4-1 in the Finals.
PLAYOFFS_2024 = [
    (1, 0, "BOS", "MIA", "WLWWW", 0),
    (1, 4, "DAL", "LAC", "WLLWWW", 0),
    (2, 0, "BOS", "CLE", "WLWWW", 14),
    (2, 2, "DAL", "OKC", "LWWLWW", 14),
    (3, 0, "BOS", "IND", "WWWW", 28),
    (3, 1, "DAL", "MIN", "WWWLW", 28),
    (4, 0, "BOS", "DAL", "WWWLW", 42),
]


@pytest.fixture
def clear_player_games():
    data._player_game_cache.clear()
    yield
    data._player_game_cache.clear()


def install_playoffs(monkeypatch, specs=PLAYOFFS_2024, current_season="2025-26", **kwargs):
    frame = playoff_rows(specs, **kwargs)
    monkeypatch.setattr(playoffs_service, "fetch_playoff_team_games_df", lambda season, today=None: frame)
    monkeypatch.setattr(playoffs_service, "get_current_season", lambda today=None: current_season)
    return frame


def assert_fits_answer(output, intent):
    """The resolver output drops into a contract AskResponse and round-trips."""
    response = AskResponse(
        request_id="test",
        outcome="answer",
        question="test question",
        interpretation={"intent": intent, "reference_time": "2026-09-29T12:00:00-04:00"},
        result=output.result,
        links=list(output.links),
        sources=list(output.sources),
        interpreter={"model_called": False},
    )
    assert AskResponse.model_validate_json(response.model_dump_json()) == response
