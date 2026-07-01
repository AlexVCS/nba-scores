import pandas as pd
import pytest

from server import main
from server.services import game_summary


HUS = 1610610035
NYK = 1610612752

BREF_LINE_SCORE_HTML = """
<!--
<table id="line_score">
  <tbody>
    <tr><th data-stat="team">NYK</th>
      <td data-stat="1">16</td><td data-stat="2">21</td>
      <td data-stat="3">6</td><td data-stat="4">25</td>
      <td data-stat="T"><strong>68</strong></td></tr>
    <tr><th data-stat="team">TRH</th>
      <td data-stat="1">12</td><td data-stat="2">17</td>
      <td data-stat="3">19</td><td data-stat="4">18</td>
      <td data-stat="T"><strong>66</strong></td></tr>
  </tbody>
</table>
-->
"""


class _FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def get_data_frame(self):
        return pd.DataFrame(self.rows)


class _FakeSummary:
    def __init__(self, game_summary_rows, line_score_rows):
        self.game_summary = _FakeResult(game_summary_rows)
        self.line_score = _FakeResult(line_score_rows)


class _FakeResponse:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        pass


def _game_summary_row(**overrides):
    row = {
        "GAME_DATE_EST": "1946-11-01T00:00:00",
        "GAMECODE": "19461101/NYKTRH",
        "HOME_TEAM_ID": HUS,
        "VISITOR_TEAM_ID": NYK,
        "LIVE_PERIOD": 5,
        "GAME_STATUS_ID": 3,
    }
    row.update(overrides)
    return row


def _line_score_row(team_id, tricode, city, nickname, pts, qtrs=None, ot1=None):
    row = {
        "TEAM_ID": team_id,
        "TEAM_ABBREVIATION": tricode,
        "TEAM_CITY_NAME": city,
        "TEAM_NICKNAME": nickname,
        "PTS": pts,
    }
    qtrs = qtrs if qtrs is not None else [None, None, None, None]
    for index, score in enumerate(qtrs, start=1):
        row[f"PTS_QTR{index}"] = score
    for index in range(1, 11):
        row[f"PTS_OT{index}"] = ot1 if index == 1 else None
    return row


def _patch_summary(monkeypatch, game_summary_rows, line_score_rows):
    class FakeBoxScoreSummaryV2:
        def __init__(self, *args, **kwargs):
            self._summary = _FakeSummary(game_summary_rows, line_score_rows)
            self.game_summary = self._summary.game_summary
            self.line_score = self._summary.line_score

    monkeypatch.setattr(
        game_summary.boxscoresummaryv2, "BoxScoreSummaryV2", FakeBoxScoreSummaryV2
    )


def _bref_score(period_scores, total):
    return {
        "periods": [
            {"period": period, "score": str(score)}
            for period, score in enumerate(period_scores, start=1)
        ],
        "total": total,
    }


def _patch_invalid_nba_period_summary(monkeypatch):
    _patch_summary(
        monkeypatch,
        [_game_summary_row()],
        [
            _line_score_row(HUS, "HUS", "Toronto", "Huskies", 66, ot1=18),
            _line_score_row(NYK, "NYK", "New York", "Knicks", 68, ot1=24),
        ],
    )


def _assert_no_period_fallback(result):
    assert result["periodScoreSource"] == "unavailable"
    assert result["homeTeam"]["periods"] == []
    assert result["awayTeam"]["periods"] == []


def test_game_summary_fetch_passes_no_timeout(monkeypatch):
    calls = []

    class FakeBoxScoreSummaryV2:
        def __init__(self, *args, **kwargs):
            calls.append({"args": args, "kwargs": kwargs})
            self.game_summary = _FakeResult([])
            self.line_score = _FakeResult([])

    monkeypatch.setattr(
        game_summary.boxscoresummaryv2, "BoxScoreSummaryV2", FakeBoxScoreSummaryV2
    )

    with pytest.raises(game_summary.HTTPException):
        game_summary.fetch_game_summary("0024600206")

    assert calls == [{"args": (), "kwargs": {"game_id": "0024600206", "timeout": None}}]


def test_bref_fetch_does_not_pass_timeout(monkeypatch):
    calls = []
    monkeypatch.setattr(game_summary, "BREF_LINE_SCORE_CACHE", {})

    def fake_get(*args, **kwargs):
        calls.append({"args": args, "kwargs": kwargs})
        return _FakeResponse(BREF_LINE_SCORE_HTML)

    monkeypatch.setattr(game_summary.requests, "get", fake_get)

    game_summary.fetch_bref_line_score("1946-11-01T00:00:00", "HUS")

    assert "timeout" not in calls[0]["kwargs"]


def test_bref_fetch_caches_successful_parse(monkeypatch):
    calls = []
    monkeypatch.setattr(game_summary, "BREF_LINE_SCORE_CACHE", {})

    def fake_get(*args, **kwargs):
        calls.append((args, kwargs))
        return _FakeResponse(BREF_LINE_SCORE_HTML)

    monkeypatch.setattr(game_summary.requests, "get", fake_get)

    first = game_summary.fetch_bref_line_score("1946-11-01T00:00:00", "HUS")
    second = game_summary.fetch_bref_line_score("1946-11-01T00:00:00", "HUS")

    assert len(calls) == 1
    assert first == second
    assert [period["score"] for period in second["HUS"]["periods"]] == [
        "12",
        "17",
        "19",
        "18",
    ]


def test_bref_fetch_caches_missing_line_score(monkeypatch):
    calls = []
    monkeypatch.setattr(game_summary, "BREF_LINE_SCORE_CACHE", {})

    def fake_get(*args, **kwargs):
        calls.append((args, kwargs))
        return _FakeResponse("<html></html>")

    monkeypatch.setattr(game_summary.requests, "get", fake_get)

    first = game_summary.fetch_bref_line_score("1946-11-01T00:00:00", "HUS")
    second = game_summary.fetch_bref_line_score("1946-11-01T00:00:00", "HUS")

    assert first is None
    assert second is None
    assert len(calls) == 1


def test_bref_fetch_does_not_cache_transport_failure(monkeypatch):
    calls = []
    monkeypatch.setattr(game_summary, "BREF_LINE_SCORE_CACHE", {})

    def fake_get(*args, **kwargs):
        calls.append((args, kwargs))
        if len(calls) == 1:
            raise game_summary.requests.exceptions.Timeout("timed out")
        return _FakeResponse(BREF_LINE_SCORE_HTML)

    monkeypatch.setattr(game_summary.requests, "get", fake_get)

    with pytest.raises(game_summary.requests.exceptions.Timeout):
        game_summary.fetch_bref_line_score("1946-11-01T00:00:00", "HUS")

    result = game_summary.fetch_bref_line_score("1946-11-01T00:00:00", "HUS")

    assert len(calls) == 2
    assert result["HUS"]["total"] == 66


def test_invalid_nba_period_data_uses_bref_fallback(monkeypatch):
    calls = []
    _patch_invalid_nba_period_summary(monkeypatch)

    def fake_bref(game_date_est, home_team_tricode):
        calls.append((game_date_est, home_team_tricode))
        return {
            "HUS": _bref_score([12, 17, 19, 18], 66),
            "NYK": _bref_score([16, 21, 6, 25], 68),
        }

    monkeypatch.setattr(game_summary, "fetch_bref_line_score", fake_bref)

    result = main.get_game_summary("0024600001")

    assert calls == [("1946-11-01T00:00:00", "HUS")]
    assert result["periodScoreSource"] == "basketball-reference"
    assert result["gameStatusText"] == "Final"
    assert [period["score"] for period in result["homeTeam"]["periods"]] == [
        "12",
        "17",
        "19",
        "18",
    ]
    assert [period["score"] for period in result["awayTeam"]["periods"]] == [
        "16",
        "21",
        "6",
        "25",
    ]


def test_bref_fallback_rejects_period_sum_mismatch(monkeypatch):
    _patch_invalid_nba_period_summary(monkeypatch)
    monkeypatch.setattr(
        game_summary,
        "fetch_bref_line_score",
        lambda *args, **kwargs: {
            "HUS": _bref_score([12, 17, 19, 17], 65),
            "NYK": _bref_score([16, 21, 6, 25], 68),
        },
    )

    result = main.get_game_summary("0024600001")

    _assert_no_period_fallback(result)


def test_bref_fallback_rejects_parsed_total_mismatch(monkeypatch):
    _patch_invalid_nba_period_summary(monkeypatch)
    monkeypatch.setattr(
        game_summary,
        "fetch_bref_line_score",
        lambda *args, **kwargs: {
            "HUS": _bref_score([12, 17, 19, 18], 67),
            "NYK": _bref_score([16, 21, 6, 25], 68),
        },
    )

    result = main.get_game_summary("0024600001")

    _assert_no_period_fallback(result)


def test_bref_fallback_rejects_mismatched_period_sets(monkeypatch):
    _patch_invalid_nba_period_summary(monkeypatch)
    monkeypatch.setattr(
        game_summary,
        "fetch_bref_line_score",
        lambda *args, **kwargs: {
            "HUS": _bref_score([12, 17, 19, 18], 66),
            "NYK": _bref_score([16, 21, 6, 20, 5], 68),
        },
    )

    result = main.get_game_summary("0024600001")

    _assert_no_period_fallback(result)


def test_bref_parser_extracts_commented_line_score():
    result = game_summary.extract_bref_line_score(BREF_LINE_SCORE_HTML)

    assert [period["score"] for period in result["NYK"]["periods"]] == [
        "16",
        "21",
        "6",
        "25",
    ]
    assert [period["score"] for period in result["HUS"]["periods"]] == [
        "12",
        "17",
        "19",
        "18",
    ]
    assert result["NYK"]["total"] == 68
    assert result["HUS"]["total"] == 66


def test_valid_nba_period_data_does_not_call_bref(monkeypatch):
    _patch_summary(
        monkeypatch,
        [_game_summary_row()],
        [
            _line_score_row(HUS, "HUS", "Toronto", "Huskies", 66, [12, 17, 19, 18]),
            _line_score_row(NYK, "NYK", "New York", "Knicks", 68, [16, 21, 6, 25]),
        ],
    )
    monkeypatch.setattr(
        game_summary,
        "fetch_bref_line_score",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("unexpected")),
    )

    result = main.get_game_summary("0024600001")

    assert result["periodScoreSource"] == "nba"
    assert result["gameStatusText"] == "Final"
    assert [period["score"] for period in result["homeTeam"]["periods"]] == [
        "12",
        "17",
        "19",
        "18",
    ]


def test_final_overtime_status_uses_validated_periods(monkeypatch):
    _patch_summary(
        monkeypatch,
        [_game_summary_row()],
        [
            _line_score_row(
                HUS, "HUS", "Toronto", "Huskies", 84, [12, 17, 19, 18], ot1=18
            ),
            _line_score_row(
                NYK, "NYK", "New York", "Knicks", 92, [16, 21, 6, 25], ot1=24
            ),
        ],
    )
    monkeypatch.setattr(
        game_summary,
        "fetch_bref_line_score",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("unexpected")),
    )

    result = main.get_game_summary("0024600001")

    assert result["periodScoreSource"] == "nba"
    assert result["gameStatusText"] == "Final/OT"
    assert [period["period"] for period in result["homeTeam"]["periods"]] == [
        1,
        2,
        3,
        4,
        5,
    ]


def test_fallback_failure_returns_no_periods(monkeypatch):
    _patch_summary(
        monkeypatch,
        [_game_summary_row()],
        [
            _line_score_row(HUS, "HUS", "Toronto", "Huskies", 66, ot1=18),
            _line_score_row(NYK, "NYK", "New York", "Knicks", 68, ot1=24),
        ],
    )
    monkeypatch.setattr(
        game_summary,
        "fetch_bref_line_score",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("offline")),
    )

    result = main.get_game_summary("0024600001")

    assert result["periodScoreSource"] == "unavailable"
    assert result["homeTeam"]["periods"] == []
    assert result["awayTeam"]["periods"] == []


def test_scheduled_empty_linescore_does_not_call_bref(monkeypatch):
    _patch_summary(
        monkeypatch,
        [_game_summary_row(GAME_STATUS_ID=1, LIVE_PERIOD=0)],
        [],
    )
    monkeypatch.setattr(
        game_summary,
        "fetch_bref_line_score",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("unexpected")),
    )

    result = main.get_game_summary("0024600001")

    assert result["gameStatusText"] == "Scheduled"
    assert result["periodScoreSource"] == "unavailable"


def test_final_empty_linescore_uses_bref_fallback(monkeypatch):
    calls = []
    _patch_summary(
        monkeypatch,
        [_game_summary_row(LIVE_PERIOD=4)],
        [],
    )

    def fake_bref(game_date_est, home_team_tricode):
        calls.append((game_date_est, home_team_tricode))
        return {
            "HUS": _bref_score([12, 17, 19, 18], 66),
            "NYK": _bref_score([16, 21, 6, 25], 68),
        }

    monkeypatch.setattr(game_summary, "fetch_bref_line_score", fake_bref)

    result = main.get_game_summary("0024600001")

    assert calls == [("1946-11-01T00:00:00", "HUS")]
    assert result["periodScoreSource"] == "basketball-reference"
    assert result["gameStatusText"] == "Final"
    assert result["homeTeam"]["score"] == "66"
    assert result["awayTeam"]["score"] == "68"
    assert [period["score"] for period in result["homeTeam"]["periods"]] == [
        "12",
        "17",
        "19",
        "18",
    ]
    assert [period["score"] for period in result["awayTeam"]["periods"]] == [
        "16",
        "21",
        "6",
        "25",
    ]


def test_final_sparse_linescore_uses_bref_fallback(monkeypatch):
    calls = []
    _patch_summary(
        monkeypatch,
        [_game_summary_row(LIVE_PERIOD=4)],
        [_line_score_row(HUS, "HUS", "Toronto", "Huskies", 66)],
    )

    def fake_bref(game_date_est, home_team_tricode):
        calls.append((game_date_est, home_team_tricode))
        return {
            "HUS": _bref_score([12, 17, 19, 18], 66),
            "NYK": _bref_score([16, 21, 6, 25], 68),
        }

    monkeypatch.setattr(game_summary, "fetch_bref_line_score", fake_bref)

    result = main.get_game_summary("0024600001")

    assert calls == [("1946-11-01T00:00:00", "HUS")]
    assert result["periodScoreSource"] == "basketball-reference"
    assert result["homeTeam"]["teamName"] == "Toronto Huskies"
    assert result["homeTeam"]["score"] == "66"
    assert result["awayTeam"]["teamTricode"] == "NYK"
    assert result["awayTeam"]["score"] == "68"
    assert [period["score"] for period in result["awayTeam"]["periods"]] == [
        "16",
        "21",
        "6",
        "25",
    ]


def test_final_empty_linescore_bref_failure_is_not_scheduled(monkeypatch):
    _patch_summary(
        monkeypatch,
        [_game_summary_row(LIVE_PERIOD=4)],
        [],
    )
    monkeypatch.setattr(
        game_summary,
        "fetch_bref_line_score",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("offline")),
    )

    result = main.get_game_summary("0024600001")

    assert result["gameStatusText"] == "Final"
    assert result["periodScoreSource"] == "unavailable"
    assert result["homeTeam"]["periods"] == []
    assert result["awayTeam"]["periods"] == []


def test_bref_url_uses_historical_home_team_mapping():
    assert game_summary.build_bref_boxscore_url(
        "1946-11-01T00:00:00", "HUS"
    ) == "https://www.basketball-reference.com/boxscores/194611010TRH.html"


def test_bref_url_preserves_modern_wizards_home_team_code():
    assert game_summary.build_bref_boxscore_url(
        "2024-01-31T00:00:00", "WAS"
    ) == "https://www.basketball-reference.com/boxscores/202401310WAS.html"


def test_bref_parser_preserves_modern_wizards_team_code():
    assert game_summary.from_bref_team_code("WAS") == "WAS"
