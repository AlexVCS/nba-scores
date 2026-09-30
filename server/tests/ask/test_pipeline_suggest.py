import datetime as dt

from server.ask.eval import builders as b
from server.ask.models.common import NEW_YORK
from server.ask.resolvers.games import ResolvedGame
from server.ask.suggest import AskSuggester


class Lookup:
    def lookup(self, question, context):
        return b.lookup_result([b.team(1610612752, "NYK", "New York Knicks")])


def _game(game_id):
    away = b.team(1610612752, "NYK", "New York Knicks").value.team
    home = b.team(1610612738, "BOS", "Boston Celtics").value.team
    return ResolvedGame(dt.date(2026, 4, 20), {"gameId": game_id}, home, away)


def test_hidden_typeahead_omits_postseason_direct_match(monkeypatch):
    monkeypatch.setattr("server.ask.suggest.games._day_games", lambda day: [
        _game("0042500101"), _game("0022501200")])
    suggester = AskSuggester(lookup=Lookup(), clock=lambda: dt.datetime(2026, 4, 20, tzinfo=NEW_YORK))
    hidden = suggester.suggest("Knicks 2026-04-20", hidden=True)
    shown = suggester.suggest("Knicks 2026-04-20", hidden=False)
    assert [game.game_id for game in hidden.games] == ["0022501200"]
    assert [game.game_id for game in shown.games] == ["0042500101", "0022501200"]
    assert hidden.entities[0].team.tricode == "NYK"


def test_typeahead_never_carries_answer_values(monkeypatch):
    # The consent boundary is submission (ADR 0006): typeahead may name a game,
    # but never its score, status, or series standing, even with results shown.
    away = b.team(1610612752, "NYK", "New York Knicks").value.team
    home = b.team(1610612738, "BOS", "Boston Celtics").value.team
    played = {"gameId": "0022501200", "gameStatus": 3, "gameStatusText": "Final/OT",
              "seriesText": "NYK leads 3-1", "homeTeam": {"score": 199}, "awayTeam": {"score": 188}}
    monkeypatch.setattr("server.ask.suggest.games._day_games",
                        lambda day: [ResolvedGame(dt.date(2026, 4, 20), played, home, away)])
    suggester = AskSuggester(lookup=Lookup(), clock=lambda: dt.datetime(2026, 4, 20, tzinfo=NEW_YORK))
    for hidden in (True, False):
        dumped = suggester.suggest("Knicks 2026-04-20", hidden=hidden).model_dump_json()
        assert "0022501200" in dumped
        for value in ("199", "188", "Final", "leads", "\"score\""):
            assert value not in dumped
