"""Venue candidates (ADR 0011): "games in New York" -> Knicks and Nets home games.

Only a known city directly after "in" or "at" becomes a location, so "Boston games"
stays a team question while "games in Boston" filters by venue. The matched text is
masked so the same words do not also become a team candidate. Each city lists which
franchises were based there and when (the Nets in New Jersey until 2012, the
SuperSonics in Seattle until 2008), so a dated search only matches the team that
actually played home games there then. Defunct franchises are not covered.

A city inside a "when they were in New Jersey" clause says where the team was based,
not where the games were played, so it is masked without becoming a venue.
"""
from __future__ import annotations

import datetime as dt
import re
from functools import lru_cache

from nba_api.stats.static import teams as static_teams

from server.ask.candidates.types import Hit, Mention
from server.ask.models.candidates import LocationCandidateValue
from server.ask.models.common import GameLocation, HomeTenure, TeamRef

# A tenure is (tricode, name then, first season, last season or None). Seasons are
# start years; a tenure runs July 1 of the first through June 30 after the last.
# Metro areas count: the Knicks and Nets are both "New York", the Clippers' Intuit
# Dome is also "Los Angeles".
Tenure = tuple[str, str, int, int | None]

# Candidate key -> (city label, tenures, folded phrases).
CITIES: dict[str, tuple[str, tuple[Tenure, ...], tuple[str, ...]]] = {
    "new_york": ("New York", (("NYK", "New York Knicks", 1946, None), ("BKN", "Brooklyn Nets", 2012, None)),
                 ("new york city", "new york", "nyc")),
    "manhattan": ("Manhattan", (("NYK", "New York Knicks", 1946, None),),
                  ("manhattan", "madison square garden", "msg")),
    "brooklyn": ("Brooklyn", (("BKN", "Brooklyn Nets", 2012, None),), ("brooklyn", "barclays center")),
    "new_jersey": ("New Jersey", (("BKN", "New Jersey Nets", 1977, 2011),), ("new jersey",)),
    "los_angeles": ("Los Angeles", (("LAL", "Los Angeles Lakers", 1960, None),
                                    ("LAC", "Los Angeles Clippers", 1984, None)), ("los angeles", "l.a.", "la")),
    "inglewood": ("Inglewood", (("LAL", "Los Angeles Lakers", 1967, 1998),
                                ("LAC", "Los Angeles Clippers", 2024, None)), ("inglewood",)),
    "atlanta": ("Atlanta", (("ATL", "Atlanta Hawks", 1968, None),), ("atlanta",)),
    "boston": ("Boston", (("BOS", "Boston Celtics", 1946, None),), ("boston",)),
    "cleveland": ("Cleveland", (("CLE", "Cleveland Cavaliers", 1970, None),), ("cleveland",)),
    "new_orleans": ("New Orleans", (("NOP", "New Orleans Hornets", 2002, 2004), ("NOP", "New Orleans Pelicans", 2007, None),
                                    ("UTA", "New Orleans Jazz", 1974, 1978)), ("new orleans",)),
    "chicago": ("Chicago", (("CHI", "Chicago Bulls", 1966, None), ("WAS", "Chicago Zephyrs", 1961, 1962)), ("chicago",)),
    "dallas": ("Dallas", (("DAL", "Dallas Mavericks", 1980, None),), ("dallas",)),
    "denver": ("Denver", (("DEN", "Denver Nuggets", 1976, None),), ("denver",)),
    "san_francisco": ("San Francisco", (("GSW", "San Francisco Warriors", 1962, 1970),
                                        ("GSW", "Golden State Warriors", 2019, None)), ("san francisco",)),
    "oakland": ("Oakland", (("GSW", "Golden State Warriors", 1971, 2018),), ("oakland",)),
    "bay_area": ("the Bay Area", (("GSW", "Golden State Warriors", 1962, None),), ("the bay area", "bay area")),
    "houston": ("Houston", (("HOU", "Houston Rockets", 1971, None),), ("houston",)),
    "miami": ("Miami", (("MIA", "Miami Heat", 1988, None),), ("miami",)),
    "milwaukee": ("Milwaukee", (("MIL", "Milwaukee Bucks", 1968, None),), ("milwaukee",)),
    "minneapolis": ("Minneapolis", (("MIN", "Minnesota Timberwolves", 1989, None),
                                    ("LAL", "Minneapolis Lakers", 1948, 1959)), ("minneapolis", "minnesota")),
    "orlando": ("Orlando", (("ORL", "Orlando Magic", 1989, None),), ("orlando",)),
    "indianapolis": ("Indianapolis", (("IND", "Indiana Pacers", 1976, None),), ("indianapolis",)),
    "philadelphia": ("Philadelphia", (("PHI", "Philadelphia 76ers", 1963, None),
                                      ("GSW", "Philadelphia Warriors", 1946, 1961)), ("philadelphia", "philly")),
    "phoenix": ("Phoenix", (("PHX", "Phoenix Suns", 1968, None),), ("phoenix",)),
    "portland": ("Portland", (("POR", "Portland Trail Blazers", 1970, None),), ("portland",)),
    "sacramento": ("Sacramento", (("SAC", "Sacramento Kings", 1985, None),), ("sacramento",)),
    "san_antonio": ("San Antonio", (("SAS", "San Antonio Spurs", 1976, None),), ("san antonio",)),
    "oklahoma_city": ("Oklahoma City", (("OKC", "Oklahoma City Thunder", 2008, None),
                                        ("NOP", "New Orleans/Oklahoma City Hornets", 2005, 2006)),
                      ("oklahoma city", "okc")),
    "toronto": ("Toronto", (("TOR", "Toronto Raptors", 1995, None),), ("toronto",)),
    "salt_lake_city": ("Salt Lake City", (("UTA", "Utah Jazz", 1979, None),), ("salt lake city", "salt lake", "utah")),
    "memphis": ("Memphis", (("MEM", "Memphis Grizzlies", 2001, None),), ("memphis",)),
    "washington": ("Washington, D.C.", (("WAS", "Washington Wizards", 1973, None),),
                   ("washington d.c.", "washington dc", "washington", "d.c.", "dc")),
    "detroit": ("Detroit", (("DET", "Detroit Pistons", 1957, None),), ("detroit",)),
    "charlotte": ("Charlotte", (("CHA", "Charlotte Hornets", 1988, 2001), ("CHA", "Charlotte Hornets", 2004, None)),
                  ("charlotte",)),
    # Former NBA cities of current franchises.
    "seattle": ("Seattle", (("OKC", "Seattle SuperSonics", 1967, 2007),), ("seattle",)),
    "vancouver": ("Vancouver", (("MEM", "Vancouver Grizzlies", 1995, 2000),), ("vancouver",)),
    "san_diego": ("San Diego", (("LAC", "San Diego Clippers", 1978, 1983), ("HOU", "San Diego Rockets", 1967, 1970)),
                  ("san diego",)),
    "kansas_city": ("Kansas City", (("SAC", "Kansas City Kings", 1972, 1984),), ("kansas city",)),
    "buffalo": ("Buffalo", (("LAC", "Buffalo Braves", 1970, 1977),), ("buffalo",)),
    "baltimore": ("Baltimore", (("WAS", "Baltimore Bullets", 1963, 1972),), ("baltimore",)),
    "st_louis": ("St. Louis", (("ATL", "St. Louis Hawks", 1955, 1967),), ("st. louis", "st louis", "saint louis")),
    "syracuse": ("Syracuse", (("PHI", "Syracuse Nationals", 1949, 1962),), ("syracuse",)),
    "cincinnati": ("Cincinnati", (("SAC", "Cincinnati Royals", 1957, 1971),), ("cincinnati",)),
}


# "when they were in", "while the Nets were still based in": franchise history, not a venue.
_HISTORY_CLAUSE = re.compile(
    r"\b(?:when|while)\s+(?:[\w.'’]+\s+){1,3}?(?:was|were)\s+(?:still\s+)?(?:based\s+|located\s+)?$")


@lru_cache(maxsize=1)
def _team_ids() -> dict[str, int]:
    return {t["abbreviation"]: t["id"] for t in static_teams.get_teams()}


@lru_cache(maxsize=1)
def _pattern() -> tuple[re.Pattern[str], dict[str, str]]:
    phrase_to_key = {phrase: key for key, (_, _, phrases) in CITIES.items() for phrase in phrases}
    alternation = "|".join(re.escape(p) for p in sorted(phrase_to_key, key=len, reverse=True))
    # "in Boston's game" names the team, not the venue.
    return re.compile(rf"\b(?:in|at)\s+(?:the\s+)?({alternation})(?!\w)(?!['’]s\b)"), phrase_to_key


def location_value(key: str) -> LocationCandidateValue:
    city, tenures, _ = CITIES[key]
    ids = _team_ids()
    homes = [HomeTenure(team=TeamRef(team_id=ids[tricode], tricode=tricode, name=name),
                        start=dt.date(first, 7, 1), end=dt.date(last + 1, 6, 30) if last is not None else None)
             for tricode, name, first, last in tenures]
    return LocationCandidateValue(location=GameLocation(city=city, homes=homes))


def _label(key: str) -> str:
    city, tenures, _ = CITIES[key]
    parts = []
    for _, name, first, last in tenures:
        span = f"{first}–{last + 1}" if last is not None else f"since {first}" if first > 1950 else ""
        parts.append(f"{name} {span}".strip())
    return f"{city}: home games of {'; '.join(parts)}"[:120]


def mentions(masked: str, original: str) -> tuple[list[Mention], str]:
    pattern, phrase_to_key = _pattern()
    out: list[Mention] = []
    for m in pattern.finditer(masked):
        start, end = m.span(1)
        key = phrase_to_key[m.group(1)]
        masked = masked[:start] + " " * (end - start) + masked[end:]
        if _HISTORY_CLAUSE.search(masked, 0, m.start()):
            continue
        hit = Hit(field="location", key=key, label=_label(key), source="pattern", score=1.0,
                  value=location_value(key))
        out.append(Mention(field="location", start=start, end=end, text=original[start:end],
                           hits=[hit], total=1))
    return out, masked
