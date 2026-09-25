from types import SimpleNamespace

from server.services import nba_schedule


def schedule_payload(dates, *, date_format="iso"):
    """Build a ScheduleLeagueV2 get_dict() payload with one game per date."""
    game_dates = []
    for index, day in enumerate(sorted(dates)):
        if date_format == "iso":
            game = {"gameId": f"00225{index:05d}", "gameDateEst": f"{day}T00:00:00Z"}
            day_label = None
        else:
            year, month, dom = day.split("-")
            game = {"gameId": f"00225{index:05d}"}
            day_label = f"{month}/{dom}/{year} 00:00:00"
        game_dates.append({"gameDate": day_label, "games": [game]})
    return {"leagueSchedule": {"gameDates": game_dates}}


def schedule_endpoint(dates, **kwargs):
    payload = schedule_payload(dates, **kwargs)
    return SimpleNamespace(get_dict=lambda: payload)


def season_schedule(dates, season="2025-26", source=nba_schedule.SOURCE_SCHEDULE):
    return nba_schedule.SeasonSchedule(season, source, frozenset(dates))
