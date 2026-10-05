"""Small, model-free typeahead over candidate lookup and verified scoreboards."""

from __future__ import annotations

import datetime as dt
import re

from server.ask import links
from server.ask.cache import AskCache, CacheValue
from server.ask.models.request import AskContext
from server.ask.models.response import AskSuggestResponse, SuggestEntity, SuggestGame, Suggestion
from server.ask.resolvers import games
from server.ask.resolvers.errors import ResolverError
from server.ask.candidates.lookup import CandidateLookupService
from server.ask.models.common import NEW_YORK

_DATE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")


class AskSuggester:
    def __init__(self, *, lookup=None, cache=None, clock=None):
        self.lookup = lookup or CandidateLookupService()
        self.cache = cache if cache is not None else AskCache(max_entries=128)
        self.clock = clock or (lambda: dt.datetime.now(NEW_YORK))

    def suggest(self, query: str, hidden: bool = True) -> AskSuggestResponse:
        query = query.strip()[:300]
        if len(query) < 2:
            return AskSuggestResponse(query=query)
        today = self.clock().astimezone(NEW_YORK).date()
        key = ("suggest-1", query.casefold(), hidden, today.isoformat())

        def load():
            context = AskContext(reference_time=self.clock())
            found = self.lookup.lookup(query, context)
            entities = []
            for field in ("player", "team"):
                for candidate in found.sets[field].candidates:
                    value = candidate.value
                    if field == "player":
                        entities.append(SuggestEntity(kind="player", label=candidate.label[:80],
                                                      player_id=value.player.player_id))
                    else:
                        entities.append(SuggestEntity(kind="team", label=candidate.label[:80], team=value.team))
                    if len(entities) >= 5:
                        break
                if len(entities) >= 5:
                    break
            direct = []
            date = _DATE.search(query)
            if date:
                try:
                    day = dt.date.fromisoformat(date[1])
                    team_ids = {c.value.team.team_id for c in found.sets["team"].candidates}
                    for game in games._day_games(day):
                        if team_ids and not team_ids.intersection(game.team_ids):
                            continue
                        # A postseason participant inferred from a dated result
                        # reveals advancement, even before its score is shown.
                        if hidden and game.game_id[2] in ("4", "5"):
                            continue
                        direct.append(SuggestGame(game_id=game.game_id, date=day, away=game.away,
                                                  home=game.home,
                                                  label=f"{game.away.tricode} @ {game.home.tricode} · {day:%b} {day.day}",
                                                  link=links.boxscore_link(game.game_id, day)))
                        if len(direct) == 5:
                            break
                except (ValueError, ResolverError):
                    pass
            questions = []
            for candidate in found.sets["team"].candidates[:2]:
                if candidate.source == "app_context":
                    continue
                questions.append(Suggestion(question=f"{candidate.value.team.name} games on {today.isoformat()}?",
                                            category="games"))
            return CacheValue(AskSuggestResponse(query=query, games=direct, entities=entities,
                                                 questions=questions), 30)

        return self.cache.get_or_load("suggest", key, load).value
