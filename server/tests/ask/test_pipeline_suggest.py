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
