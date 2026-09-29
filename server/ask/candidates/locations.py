"""Venue candidates (ADR 0011): "games in New York" -> Knicks and Nets home games.

Only a known city directly after "in" or "at" becomes a location, so "Boston games"
stays a team question while "games in Boston" filters by venue. The matched text is
masked so the same words do not also become a team candidate. Current franchises
only; historical venues (Seattle, New Jersey, Vancouver) produce no candidate.
"""
from __future__ import annotations

import re
from functools import lru_cache

from nba_api.stats.static import teams as static_teams

from server.ask.candidates.types import Hit, Mention
from server.ask.models.candidates import LocationCandidateValue
from server.ask.models.common import GameLocation, TeamRef

# Candidate key -> (city label, home team tricodes, folded phrases).
CITIES: dict[str, tuple[str, tuple[str, ...], tuple[str, ...]]] = {
    "new_york": ("New York", ("NYK", "BKN"), ("new york city", "new york", "nyc")),
    "manhattan": ("Manhattan", ("NYK",), ("manhattan", "madison square garden", "msg")),
    "brooklyn": ("Brooklyn", ("BKN",), ("brooklyn", "barclays center")),
    "los_angeles": ("Los Angeles", ("LAL", "LAC"), ("los angeles", "l.a.", "la")),
    "inglewood": ("Inglewood", ("LAC",), ("inglewood",)),
    "atlanta": ("Atlanta", ("ATL",), ("atlanta",)),
    "boston": ("Boston", ("BOS",), ("boston",)),
    "cleveland": ("Cleveland", ("CLE",), ("cleveland",)),
    "new_orleans": ("New Orleans", ("NOP",), ("new orleans",)),
    "chicago": ("Chicago", ("CHI",), ("chicago",)),
    "dallas": ("Dallas", ("DAL",), ("dallas",)),
    "denver": ("Denver", ("DEN",), ("denver",)),
    "san_francisco": ("San Francisco", ("GSW",), ("san francisco", "the bay area", "bay area")),
    "houston": ("Houston", ("HOU",), ("houston",)),
    "miami": ("Miami", ("MIA",), ("miami",)),
    "milwaukee": ("Milwaukee", ("MIL",), ("milwaukee",)),
    "minneapolis": ("Minneapolis", ("MIN",), ("minneapolis", "minnesota")),
    "orlando": ("Orlando", ("ORL",), ("orlando",)),
    "indianapolis": ("Indianapolis", ("IND",), ("indianapolis",)),
    "philadelphia": ("Philadelphia", ("PHI",), ("philadelphia", "philly")),
    "phoenix": ("Phoenix", ("PHX",), ("phoenix",)),
    "portland": ("Portland", ("POR",), ("portland",)),
    "sacramento": ("Sacramento", ("SAC",), ("sacramento",)),
    "san_antonio": ("San Antonio", ("SAS",), ("san antonio",)),
    "oklahoma_city": ("Oklahoma City", ("OKC",), ("oklahoma city", "okc")),
    "toronto": ("Toronto", ("TOR",), ("toronto",)),
    "salt_lake_city": ("Salt Lake City", ("UTA",), ("salt lake city", "salt lake", "utah")),
    "memphis": ("Memphis", ("MEM",), ("memphis",)),
    "washington": ("Washington, D.C.", ("WAS",), ("washington d.c.", "washington dc", "washington", "d.c.", "dc")),
    "detroit": ("Detroit", ("DET",), ("detroit",)),
    "charlotte": ("Charlotte", ("CHA",), ("charlotte",)),
}


@lru_cache(maxsize=1)
def _team_refs() -> dict[str, TeamRef]:
    return {t["abbreviation"]: TeamRef(team_id=t["id"], tricode=t["abbreviation"], name=t["full_name"])
            for t in static_teams.get_teams()}


@lru_cache(maxsize=1)
def _pattern() -> tuple[re.Pattern[str], dict[str, str]]:
    phrase_to_key = {phrase: key for key, (_, _, phrases) in CITIES.items() for phrase in phrases}
    alternation = "|".join(re.escape(p) for p in sorted(phrase_to_key, key=len, reverse=True))
    # "in Boston's game" names the team, not the venue.
    return re.compile(rf"\b(?:in|at)\s+(?:the\s+)?({alternation})(?!\w)(?!['’]s\b)"), phrase_to_key


def location_value(key: str) -> LocationCandidateValue:
    city, tricodes, _ = CITIES[key]
    refs = _team_refs()
    return LocationCandidateValue(location=GameLocation(city=city, teams=[refs[t] for t in tricodes]))


def mentions(masked: str, original: str) -> tuple[list[Mention], str]:
    pattern, phrase_to_key = _pattern()
    out: list[Mention] = []
    for m in pattern.finditer(masked):
        start, end = m.span(1)
        key = phrase_to_key[m.group(1)]
        value = location_value(key)
        homes = " and ".join(t.name for t in value.location.teams)
        hit = Hit(field="location", key=key, label=f"{CITIES[key][0]} ({homes} home games)",
                  source="pattern", score=1.0, value=value)
        out.append(Mention(field="location", start=start, end=end, text=original[start:end],
                           hits=[hit], total=1))
        masked = masked[:start] + " " * (end - start) + masked[end:]
    return out, masked
