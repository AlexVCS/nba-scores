import pandas as pd

from server.services import nba_schedule


def test_parse_schedule_v2_passes_no_timeout(monkeypatch):
    calls = []

    class FakeScheduleLeagueV2:
        def __init__(self, *args, **kwargs):
            calls.append({"args": args, "kwargs": kwargs})

        def get_data_frames(self):
            return [pd.DataFrame([{"GAME_DATE": "2024-11-01"}])]

    monkeypatch.setattr(nba_schedule, "ScheduleLeagueV2", FakeScheduleLeagueV2)

    assert nba_schedule._parse_schedule_v2("2024-25") == {"2024-11-01"}
    assert calls == [
        {"args": (), "kwargs": {"season": "2024-25", "timeout": None}}
    ]


def test_parse_game_log_fallback_passes_no_timeout(monkeypatch):
    calls = []

    class FakeLeagueGameLog:
        def __init__(self, *args, **kwargs):
            calls.append({"args": args, "kwargs": kwargs})

        def get_data_frames(self):
            return [pd.DataFrame([{"GAME_DATE": "2024-11-01"}])]

    monkeypatch.setattr(nba_schedule, "LeagueGameLog", FakeLeagueGameLog)

    assert nba_schedule._parse_game_log_fallback("2024-25") == {"2024-11-01"}
    assert calls == [
        {
            "args": (),
            "kwargs": {
                "season": "2024-25",
                "season_type_all_star": "Regular Season",
                "timeout": None,
            },
        }
    ]
