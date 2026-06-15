import json
from pathlib import Path

import pytest

_CONFERENCES_JSON = (
    Path(__file__).resolve().parents[1]
    / "constants"
    / "nbaConferences.json"
)


@pytest.fixture(scope="module")
def conferences_json():
    with open(_CONFERENCES_JSON) as f:
        return json.load(f)


def test_east_team_ids_match_json(conferences_json):
    from server.services.playoffs import EAST_TEAM_IDS

    assert EAST_TEAM_IDS == frozenset(conferences_json["east"])


def test_west_team_ids_match_json(conferences_json):
    from server.services.playoffs import WEST_TEAM_IDS

    assert WEST_TEAM_IDS == frozenset(conferences_json["west"])


def test_no_overlap_between_conferences(conferences_json):
    east = set(conferences_json["east"])
    west = set(conferences_json["west"])
    assert east.isdisjoint(west), f"Teams in both conferences: {east & west}"


def test_conference_sizes(conferences_json):
    assert len(conferences_json["east"]) == 15
    assert len(conferences_json["west"]) == 15