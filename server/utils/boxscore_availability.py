def is_valid_nba_game_id(game_id: str | None) -> bool:
    return isinstance(game_id, str) and game_id.isdigit() and len(game_id) == 10


def is_boxscore_available_metadata(
    game_id: str | None,
    game_date: str | None,
    game_status: int | None,
) -> bool:
    if not is_valid_nba_game_id(game_id):
        return False
    if game_status is None:
        return False
    if game_status == 1:
        return False
    return True
