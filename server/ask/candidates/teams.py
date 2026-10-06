"""Team names resolved against dated franchise name records.

Each name in ``server/ask/data/franchise_history.json`` is valid only for the
seasons it was in use. When the question fixes a season (explicitly or through
a date), names that were not in use then are dropped, not mapped to whatever
the franchise is called today. Nothing here consults rosters.
"""
from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable

from server.ask.candidates.aliases import DATA_DIR, AliasMapping, get_alias_mapping
from server.ask.candidates.text import name_key
from server.ask.candidates.types import Hit
from server.ask.models.candidates import TeamCandidateValue
from server.ask.models.common import TeamRef

FRANCHISE_PATH = DATA_DIR / "franchise_history.json"


def season_label(start_year: int) -> str:
    return f"{start_year}-{(start_year + 1) % 100:02d}"


@dataclass(frozen=True)
class NameRecord:
    team_id: int
    city: str
    nickname: str
    abbreviation: str
    first_season: int
    last_season: int | None

    @property
    def full_name(self) -> str:
        return f"{self.city} {self.nickname}"

    def in_use(self, start_year: int) -> bool:
        return self.first_season <= start_year and (self.last_season is None or start_year <= self.last_season)

    @property
    def valid_from(self) -> dt.date:
        # A season "belongs" to July 1 of its start year through June 30.
        return dt.date(self.first_season, 7, 1)

    @property
    def valid_to(self) -> dt.date | None:
        return None if self.last_season is None else dt.date(self.last_season + 1, 6, 30)


@dataclass(frozen=True)
class TeamIndex:
    current: dict[int, NameRecord]
    phrases: dict[str, tuple[tuple[NameRecord, str, str | None], ...]]
    """Phrase key -> (record, match kind, alias text)."""
    caps_only: frozenset[str]
    """Keys that only count when written in capitals (tricodes, short aliases)."""
    max_phrase_tokens: int


def load_records(path=FRANCHISE_PATH) -> tuple[NameRecord, ...]:
    data = json.loads(path.read_text())
    return tuple(
        NameRecord(
            team_id=int(franchise["team_id"]),
            city=name["city"],
            nickname=name["nickname"],
            abbreviation=name["abbreviation"],
            first_season=int(name["first_season"]),
            last_season=None if name["last_season"] is None else int(name["last_season"]),
        )
        for franchise in data["franchises"]
        for name in franchise["names"]
    )


def build_index(records: Iterable[NameRecord], aliases: AliasMapping) -> TeamIndex:
    records = tuple(records)
    phrases: dict[str, list[tuple[NameRecord, str, str | None]]] = {}
    caps_only: set[str] = set()

    def add(key: str, record: NameRecord, kind: str, alias: str | None = None) -> None:
        entry = (record, kind, alias)
        if key and entry not in phrases.setdefault(key, []):
            phrases[key].append(entry)

    by_full: dict[str, list[NameRecord]] = {}
    by_city: dict[str, list[NameRecord]] = {}
    for record in records:
        by_full.setdefault(name_key(record.full_name), []).append(record)
        add(name_key(record.full_name), record, "full_name")
        add(name_key(record.nickname), record, "nickname")
        for city in record.city.split("/"):
            by_city.setdefault(name_key(city), []).append(record)
            add(name_key(city), record, "city")
            add(name_key(f"{city} {record.nickname}"), record, "full_name")
        add(name_key(record.abbreviation), record, "abbreviation")
        caps_only.add(name_key(record.abbreviation))

    for table, targets_by, label in ((aliases.teams, by_full, "alias"), (aliases.cities, by_city, "city")):
        for alias, target in table.items():
            targets = targets_by.get(name_key(target))
            if not targets:
                raise ValueError(f"Alias {alias!r} points at unknown name {target!r}")
            key = name_key(alias)
            for record in targets:
                add(key, record, label, alias)
            if alias == alias.upper():  # "OKC", "LA", "NY": only when written in capitals
                caps_only.add(key)

    return TeamIndex(
        current={r.team_id: r for r in records if r.last_season is None},
        phrases={k: tuple(v) for k, v in phrases.items()},
        caps_only=frozenset(caps_only),
        max_phrase_tokens=max(len(k.split()) for k in phrases),
    )


@lru_cache(maxsize=1)
def get_team_index() -> TeamIndex:
    return build_index(load_records(), get_alias_mapping())


_KIND = {  # kind -> (rank, score, source)
    "full_name": (0, 1.0, "team_catalog"),
    "alias": (1, 0.95, "alias"),
    "nickname": (2, 0.9, "team_catalog"),
    "abbreviation": (3, 0.9, "team_catalog"),
    "city": (4, 0.7, "team_catalog"),
}


def resolve_phrase(index: TeamIndex, key: str, seasons: frozenset[int]) -> tuple[list[Hit], str | None]:
    """Team hits for one phrase, keeping only names in use in ``seasons`` (start years).

    Returns (hits, note). No hits with a note means the name exists but was not
    in use in the requested season(s); the franchise's other names are not offered.
    """
    by_team: dict[int, list[tuple[NameRecord, str, str | None]]] = {}
    for entry in index.phrases.get(key, ()):
        by_team.setdefault(entry[0].team_id, []).append(entry)

    ranked: list[tuple[tuple, Hit]] = []
    dropped: list[str] = []
    for team_id, entries in by_team.items():
        if seasons:
            in_use = [e for e in entries if any(e[0].in_use(s) for s in seasons)]
            if not in_use:
                dropped.extend(sorted({e[0].full_name for e in entries}))
                continue
            entries = in_use
        record, kind, alias = min(entries, key=lambda e: (_KIND[e[1]][0], -e[0].first_season))
        rank, score, source = _KIND[kind]
        historical = record.last_season is not None
        if historical and kind != "alias":
            source = "historical_team_name"
        current = index.current[team_id]
        span = season_label(record.first_season) + (
            "" if record.last_season is None else f" to {season_label(record.last_season)}"
        )
        label = record.full_name if not historical else f"{record.full_name} ({span}; now {current.full_name})"
        hit = Hit(
            field="team",
            key=str(team_id),
            label=label,
            source=source,  # type: ignore[arg-type]
            score=score,
            alias=alias,
            value=TeamCandidateValue(
                team=TeamRef(team_id=team_id, tricode=record.abbreviation, name=record.full_name),
                valid_from=record.valid_from,
                valid_to=record.valid_to,
            ),
        )
        ranked.append(((0 if not historical else 1, rank, -record.first_season), hit))
    ranked.sort(key=lambda pair: pair[0])
    note = f"not in use in the requested season: {', '.join(dropped)}" if dropped and not ranked else None
    return [h for _, h in ranked], note
