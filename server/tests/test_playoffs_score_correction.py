"""Tests for defensive playoff score repair.

These tests are offline: the boxscoresummaryv2 client is monkeypatched, so no
real API calls are made.
"""

import pandas as pd

from server.services import playoffs

PHX, UTA = 1610612756, 1610612762


def _game(winner_id, home_id, home_score, away_id, away_score, game_id="0048300051"):
    """Build a normalized game dict with the given winner and scores."""
    return {
        "gameId": game_id,
        "winnerTeamId": winner_id,
        "homeTeam": {"id": home_id, "score": home_score},
        "awayTeam": {"id": away_id, "score": away_score},
    }


def test_disagreement_detected_when_winner_has_fewer_points():
    """A source inconsistency can show the winner with fewer points."""
    game = _game(PHX, home_id=PHX, home_score=111, away_id=UTA, away_score=113)
    assert playoffs.game_scores_disagree_with_winner(game) is True


def test_no_disagreement_when_scores_match_winner():
    game = _game(PHX, home_id=PHX, home_score=111, away_id=UTA, away_score=110)
    assert playoffs.game_scores_disagree_with_winner(game) is False


def test_no_disagreement_when_winner_unknown():
    game = _game(None, home_id=PHX, home_score=111, away_id=UTA, away_score=113)
    assert playoffs.game_scores_disagree_with_winner(game) is False


def test_correct_game_scores_repairs_only_mismatched_game(monkeypatch):
    calls = []

    def fake_fetch(game_id):
        calls.append(game_id)
        return {PHX: 111, UTA: 110}

    monkeypatch.setattr(playoffs, "fetch_corrected_team_scores", fake_fetch)

    bad = _game(PHX, home_id=PHX, home_score=111, away_id=UTA, away_score=113,
                game_id="0048300051")
    good = _game(PHX, home_id=PHX, home_score=120, away_id=UTA, away_score=100,
                 game_id="0048300049")

    playoffs.correct_game_scores([bad, good])

    # Only the mismatched game triggered a fetch.
    assert calls == ["0048300051"]
    # The bad source score is repaired to the real line score; winner is untouched.
    assert bad["awayTeam"]["score"] == 110
    assert bad["homeTeam"]["score"] == 111
    assert bad["winnerTeamId"] == PHX
    # The consistent game is left exactly as-is.
    assert good["homeTeam"]["score"] == 120
    assert good["awayTeam"]["score"] == 100


def test_correct_game_scores_keeps_original_when_fetch_fails(monkeypatch):
    monkeypatch.setattr(playoffs, "fetch_corrected_team_scores", lambda gid: None)

    bad = _game(PHX, home_id=PHX, home_score=111, away_id=UTA, away_score=113)
    playoffs.correct_game_scores([bad])

    assert bad["homeTeam"]["score"] == 111
    assert bad["awayTeam"]["score"] == 113


def test_fetch_corrected_team_scores_parses_and_caches(monkeypatch):
    monkeypatch.setattr(playoffs, "_linescore_cache", {})

    calls = {"n": 0}

    class _FakeResult:
        def get_data_frame(self):
            return pd.DataFrame(
                [
                    {"TEAM_ID": PHX, "PTS": 111},
                    {"TEAM_ID": UTA, "PTS": 110},
                ]
            )

    class _FakeSummary:
        def __init__(self, *a, **k):
            calls["n"] += 1
            self.line_score = _FakeResult()

    monkeypatch.setattr(playoffs.boxscoresummaryv2, "BoxScoreSummaryV2", _FakeSummary)

    first = playoffs.fetch_corrected_team_scores("0048300051")
    assert first == {PHX: 111, UTA: 110}

    # Second call is served from cache (no new API construction).
    second = playoffs.fetch_corrected_team_scores("0048300051")
    assert second == {PHX: 111, UTA: 110}
    assert calls["n"] == 1
