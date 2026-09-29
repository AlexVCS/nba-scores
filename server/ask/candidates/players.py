"""Historical player catalog and its lookup indexes.

The catalog is a snapshot (``server/ask/data/player_catalog.json``) of every
NBA player with their first and last season, so lookup never touches the
network. It deliberately stores no team: current rosters say nothing about
which team a player was on for a past game. Refresh with::

    server/venv/bin/python -m server.ask.candidates.players --refresh
"""
from __future__ import annotations

import datetime as dt
import difflib
import json
import sys
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable, Mapping

from server.ask.candidates.aliases import DATA_DIR, AliasMapping, get_alias_mapping
from server.ask.candidates.text import name_key, strip_suffix

CATALOG_PATH = DATA_DIR / "player_catalog.json"


@dataclass(frozen=True)
class CatalogPlayer:
    player_id: int
    full_name: str
    first_name: str
    last_name: str
    from_year: int | None
    to_year: int | None
    played: bool
    active: bool

    def span_label(self) -> str:
        if self.from_year is None:
            return ""
        if self.active:
            return f"{season_label(self.from_year)} to present"
        if self.from_year == self.to_year or self.to_year is None:
            return season_label(self.from_year)
        return f"{season_label(self.from_year)} to {season_label(self.to_year)}"


def season_label(start_year: int) -> str:
    return f"{start_year}-{(start_year + 1) % 100:02d}"


@dataclass(frozen=True)
class PlayerIndex:
    players: Mapping[int, CatalogPlayer]
    full: Mapping[str, tuple[int, ...]]
    aliases: Mapping[str, tuple[int, ...]]
    caps_only_aliases: frozenset[str]
    last: Mapping[str, tuple[int, ...]]
    first: Mapping[str, tuple[int, ...]]
    full_keys: tuple[str, ...]
    last_keys: tuple[str, ...]
    max_phrase_tokens: int

    def fuzzy(self, key: str, *, full: bool, cutoff: float, limit: int = 3) -> list[tuple[int, float]]:
        """(player_id, similarity) for close spellings of ``key``."""
        pool = self.full_keys if full else self.last_keys
        table = self.full if full else self.last
        out: list[tuple[int, float]] = []
        for close in difflib.get_close_matches(key, pool, n=limit, cutoff=cutoff):
            ratio = difflib.SequenceMatcher(None, key, close).ratio()
            out.extend((i, ratio) for i in table[close] if i not in {p for p, _ in out})
        return out


def load_catalog(path=CATALOG_PATH) -> list[CatalogPlayer]:
    data = json.loads(path.read_text())
    return [
        CatalogPlayer(
            player_id=row[0], full_name=row[1], first_name=row[2], last_name=row[3],
            from_year=row[4], to_year=row[5], played=bool(row[6]), active=bool(row[7]),
        )
        for row in data["players"]
    ]


def build_index(catalog: Iterable[CatalogPlayer], aliases: AliasMapping) -> PlayerIndex:
    players: dict[int, CatalogPlayer] = {}
    full: dict[str, list[int]] = {}
    last: dict[str, list[int]] = {}
    first: dict[str, list[int]] = {}

    def add(table: dict[str, list[int]], key: str, player_id: int) -> None:
        if key and player_id not in table.setdefault(key, []):
            table[key].append(player_id)

    for player in catalog:
        players[player.player_id] = player
        key = name_key(player.full_name)
        add(full, key, player.player_id)
        add(full, strip_suffix(key), player.player_id)
        last_key = name_key(player.last_name)
        add(last, last_key, player.player_id)
        add(last, strip_suffix(last_key), player.player_id)
        add(first, name_key(player.first_name), player.player_id)

    alias_ids: dict[str, tuple[int, ...]] = {}
    caps_only: set[str] = set()
    for alias, ids in aliases.players.items():
        missing = [i for i in ids if i not in players]
        if missing:
            raise ValueError(f"Player alias {alias!r} points at unknown IDs {missing}")
        key = name_key(alias)
        alias_ids[key] = tuple(dict.fromkeys((*alias_ids.get(key, ()), *ids)))
        if alias == alias.upper():  # acronyms such as "KD" or "AI" must be written in capitals
            caps_only.add(key)

    longest = max((len(k.split()) for k in (*full, *alias_ids)), default=1)
    return PlayerIndex(
        players=players,
        full={k: tuple(v) for k, v in full.items()},
        aliases=alias_ids,
        caps_only_aliases=frozenset(caps_only),
        last={k: tuple(v) for k, v in last.items()},
        first={k: tuple(v) for k, v in first.items()},
        full_keys=tuple(full),
        last_keys=tuple(k for k in last if len(k) >= 4),
        max_phrase_tokens=min(longest, 5),
    )


@lru_cache(maxsize=1)
def get_player_index() -> PlayerIndex:
    return build_index(load_catalog(), get_alias_mapping())


def refresh_snapshot(path=CATALOG_PATH) -> int:
    """Rebuild the snapshot from stats.nba.com CommonAllPlayers plus nba_api's static list."""
    from nba_api.stats.endpoints import commonallplayers
    from nba_api.stats.static import players as static_players

    from server.services.nba_stats_client import NBA_STATS_HEADERS
    from server.utils.season import current_nba_season

    response = commonallplayers.CommonAllPlayers(
        is_only_current_season=0, league_id="00", season=current_nba_season(),
        headers=NBA_STATS_HEADERS, timeout=30,
    )
    rows = response.get_normalized_dict()["CommonAllPlayers"]
    static = {p["id"]: p for p in static_players.get_players()}
    out: dict[int, list] = {}
    for row in rows:
        player_id = int(row["PERSON_ID"])
        name = str(row["DISPLAY_FIRST_LAST"]).strip()
        known = static.get(player_id)
        if known:
            first, last = known["first_name"], known["last_name"]
        elif ", " in row["DISPLAY_LAST_COMMA_FIRST"]:
            last, first = row["DISPLAY_LAST_COMMA_FIRST"].split(", ", 1)
        else:
            first, last = "", name
        out[player_id] = [
            player_id, name, first, last,
            int(row["FROM_YEAR"]) if str(row["FROM_YEAR"]).isdigit() else None,
            int(row["TO_YEAR"]) if str(row["TO_YEAR"]).isdigit() else None,
            1 if row["GAMES_PLAYED_FLAG"] == "Y" else 0,
            1 if row["ROSTERSTATUS"] == 1 else 0,
        ]
    for player_id, p in static.items():
        out.setdefault(player_id, [player_id, p["full_name"], p["first_name"], p["last_name"], None, None, 1, int(p["is_active"])])
    payload = {
        "_comment": (
            "Historical NBA player catalog for Ask candidate lookup. Rows are "
            "[player_id, full_name, first_name, last_name, first_season_start_year, "
            "last_season_start_year, played_a_game, on_a_roster_at_snapshot]. No team is stored on purpose. "
            "Regenerate with: server/venv/bin/python -m server.ask.candidates.players --refresh"
        ),
        "source": "stats.nba.com CommonAllPlayers (IsOnlyCurrentSeason=0) + nba_api static players",
        "generated": dt.date.today().isoformat(),
        "players": sorted(out.values(), key=lambda r: r[0]),
    }
    lines = ",\n".join("    " + json.dumps(r, ensure_ascii=False) for r in payload["players"])
    head = {k: v for k, v in payload.items() if k != "players"}
    text = json.dumps(head, indent=2, ensure_ascii=False)[:-2] + ',\n  "players": [\n' + lines + "\n  ]\n}\n"
    path.write_text(text)
    return len(out)


if __name__ == "__main__":
    if "--refresh" in sys.argv:
        print(f"wrote {refresh_snapshot()} players to {CATALOG_PATH}")
    else:
        print(__doc__)
