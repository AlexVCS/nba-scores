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


@pytest.mark.parametrize(
    ("team_id", "expected_conference"),
    [
        pytest.param(1610612738, "East", id="celtics"),
        pytest.param(1610612748, "East", id="heat"),
        pytest.param(1610612747, "West", id="lakers"),
        pytest.param(1610612744, "West", id="warriors"),
    ],
)
def test_series_conference_for_known_team(team_id, expected_conference):
    from server.services.playoffs import _get_series_conference

    series = {"teams": [{"id": team_id}]}

    assert _get_series_conference(series) == expected_conference


def test_no_overlap_between_conferences(conferences_json):
    east = set(conferences_json["east"])
    west = set(conferences_json["west"])
    assert east.isdisjoint(west), f"Teams in both conferences: {east & west}"


def test_conference_sizes(conferences_json):
    assert len(conferences_json["east"]) == 15
    assert len(conferences_json["west"]) == 15


@pytest.mark.parametrize("conference", ["east", "west"])
def test_no_duplicate_ids_within_conference(conferences_json, conference):
    team_ids = conferences_json[conference]
    assert len(team_ids) == len(set(team_ids)), f"Duplicate team IDs in {conference}"
