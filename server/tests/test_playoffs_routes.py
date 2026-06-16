import pytest
from fastapi import HTTPException

from server import main


def test_playoff_series_maps_invalid_season_to_client_error(monkeypatch):
    monkeypatch.setattr(
        main,
        "get_playoff_series",
        lambda season: (_ for _ in ()).throw(ValueError("Invalid season format")),
    )

    with pytest.raises(HTTPException) as exc:
        main.playoff_series("bad")

    assert exc.value.status_code == 400
    assert exc.value.detail == "Invalid season format"


def test_playoff_full_maps_invalid_season_to_client_error(monkeypatch):
    monkeypatch.setattr(
        main,
        "get_playoff_games_and_series",
        lambda season: (_ for _ in ()).throw(ValueError("Invalid season format")),
    )

    with pytest.raises(HTTPException) as exc:
        main.playoff_games_and_series("bad")

    assert exc.value.status_code == 400
    assert exc.value.detail == "Invalid season format"
