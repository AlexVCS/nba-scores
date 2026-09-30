"""The single maintained Ask alias mapping.

Every consumer (interpreter adapters, Python validation, candidate lookup)
must load aliases through :func:`get_alias_mapping` so they all agree, and
should include :func:`alias_version` in cache keys.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
ALIAS_PATH = DATA_DIR / "aliases.json"


@dataclass(frozen=True)
class AliasMapping:
    teams: Mapping[str, str]
    """Alias -> dated team name record (``"Sonics"`` -> ``"Seattle SuperSonics"``)."""
    cities: Mapping[str, str]
    """City shorthand -> city in the dated records (``"LA"`` -> ``"Los Angeles"``)."""
    players: Mapping[str, tuple[int, ...]]
    """Alias -> nba_api player IDs."""
    version: str


def _parse(raw: bytes) -> AliasMapping:
    data = json.loads(raw)
    teams = data.get("teams")
    cities = data.get("cities", {})
    players = data.get("players")
    if not isinstance(teams, dict) or not isinstance(players, dict) or not isinstance(cities, dict):
        raise ValueError("Alias file needs 'teams', 'cities' and 'players' objects")
    for alias, target in (*teams.items(), *cities.items()):
        if not isinstance(alias, str) or not isinstance(target, str) or not alias.strip():
            raise ValueError(f"Invalid team or city alias entry: {alias!r}")
    parsed_players: dict[str, tuple[int, ...]] = {}
    for alias, ids in players.items():
        if not isinstance(ids, list) or not ids or not all(isinstance(i, int) and not isinstance(i, bool) for i in ids):
            raise ValueError(f"Invalid player alias entry: {alias!r}")
        parsed_players[alias] = tuple(ids)
    return AliasMapping(
        teams=MappingProxyType(dict(teams)),
        cities=MappingProxyType(dict(cities)),
        players=MappingProxyType(parsed_players),
        version=hashlib.sha256(raw).hexdigest()[:12],
    )


@lru_cache(maxsize=1)
def get_alias_mapping() -> AliasMapping:
    return _parse(ALIAS_PATH.read_bytes())


@lru_cache(maxsize=1)
def alias_version() -> str:
    """Version of everything that shapes candidates: aliases, dated team names, player catalog.

    Include it in cache keys; it changes whenever any of those files changes.
    """
    parts = [get_alias_mapping().version[:10]]
    for name in ("franchise_history.json", "player_catalog.json"):
        parts.append(hashlib.sha256((DATA_DIR / name).read_bytes()).hexdigest()[:8])
    return ".".join(parts)
