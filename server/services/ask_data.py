"""Fetch authoritative NBA records and pass them to pure basketball functions."""
from __future__ import annotations

from datetime import date, datetime, timedelta
import re

from server.services import nba_stats_client
from server.services.game_summary import fetch_boxscoretraditional
from server.services.playoffs import get_playoff_games_and_series
from server.utils.boxscore_availability import is_boxscore_available_metadata
from server.services.ask_basketball import (
    AskResolutionError, ResolvedRequest, calculate_boxscore_stats,
    calculate_postseason_summary, calculate_series_result,
)


def _empty(status, message):
    return {'status': status, 'message': message, 'items': []}, False


def _game_link(game_id: str, game_date: str | None = None) -> dict:
    if not re.fullmatch(r'\d+', game_id):
        raise ValueError('Invalid game ID')
    suffix = f'?date={date.fromisoformat(game_date[:10]).isoformat()}' if game_date else ''
    return {'label': 'Game details', 'path': f'/games/{game_id}/boxscore{suffix}', 'spoiler': True}


def _matches(game: dict, request: ResolvedRequest) -> bool:
    ids = {(game.get(side) or {}).get('teamId', (game.get(side) or {}).get('id')) for side in ('homeTeam', 'awayTeam')}
    return set(request.team_ids).issubset(ids)


def _search_games(request: ResolvedRequest) -> list[dict]:
    if not request.start_date:
        raise AskResolutionError('needs_clarification', 'Specify a date for the game search.')
    last = request.end_date or request.start_date
    if not 0 <= (last-request.start_date).days <= 6:
        raise AskResolutionError('needs_clarification', 'Please search at most seven consecutive days.')
    found = []
    day = request.start_date
    while day <= last:
        board = nba_stats_client.fetch_scoreboard_v3(day.isoformat())
        for game in board.get('games', []):
            if not _matches(game, request):
                continue
            normalized = {**game, 'gameDate': day.isoformat()}
            found.append(normalized)
        day += timedelta(days=1)
    return found


def _game_item(game: dict) -> dict:
    game = dict(game)
    if not isinstance(game.get('boxscoreAvailable'), bool):
        game['boxscoreAvailable'] = is_boxscore_available_metadata(
            game.get('gameId'), game.get('gameStatus'))
    home, away = game.get('homeTeam') or {}, game.get('awayTeam') or {}
    fields = [
        {'label': 'Date', 'value': game['gameDate'], 'spoiler': False},
        {'label': 'Status', 'value': game.get('gameStatusText') or game.get('gameStatus'), 'spoiler': True},
        {'label': 'Away', 'value': away.get('teamTricode') or away.get('teamName'), 'spoiler': True},
        {'label': 'Home', 'value': home.get('teamTricode') or home.get('teamName'), 'spoiler': True},
    ]
    if game.get('gameStatus') in (2, 3):
        for team, label in ((away, 'Away score'), (home, 'Home score')):
            fields.append({'label': label, 'value': team.get('score'), 'spoiler': True})
    return {'kind': 'game', 'title': 'NBA game', 'title_spoiler': False, 'fields': fields,
            'links': [_game_link(str(game['gameId']), game['gameDate'])],
            'context': _calendar_context(game.get('gameDate')),
            'teams': [value for team in (away, home) if (value := _team(team))],
            'game': game}


def _team(team: dict) -> dict | None:
    team_id = team.get('teamId', team.get('id'))
    if isinstance(team_id, bool) or not re.fullmatch(r'\d+', str(team_id or '')):
        return None
    name = ' '.join(filter(None, [team.get('teamCity'), team.get('teamName')])) or team.get('name') or team.get('teamTricode') or team.get('tricode') or 'Team'
    return {'id': int(team_id), 'tricode': str(team.get('teamTricode') or team.get('tricode') or ''), 'name': name}


def _calendar_context(value: str | None) -> str | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value[:10])
    except ValueError:
        return value
    return f"{parsed.strftime('%b')} {parsed.day}, {parsed.year}"


def _boxscore_context(resolved: ResolvedRequest, game: dict) -> str | None:
    if resolved.season and resolved.game_number is not None:
        year = int(resolved.season[:4]) + 1
        round_name = 'NBA Finals' if resolved.round_mention == 'finals' else (resolved.round_mention or 'playoffs').title()
        return f"Game {resolved.game_number} · {year} {round_name}"
    return _calendar_context(game.get('gameDate'))


def _series_link(season: str, series: dict) -> dict:
    year = str(int(season[:4]) + 1)
    if series.get('isFinals') or series.get('round') == 4:
        slug = 'the-finals'
    elif series.get('bracketGroupId') and series.get('seriesKey'):
        key = re.sub(r'[^a-z0-9]+', '-', str(series['seriesKey']).casefold()).strip('-')
        slug = f'series-{key}'
    else:
        return {'label': 'Playoff bracket', 'path': f'/playoffs?season={season}', 'spoiler': True}
    return {'label': 'Series', 'path': f'/playoffs/{year}/{slug}', 'spoiler': True}


def _matching_series(request, payload):
    series = payload.get('series', [])
    if request.team_ids:
        series = [item for item in series if set(request.team_ids).issubset({team['id'] for team in item.get('teams', [])})]
    mention = request.round_mention
    if mention:
        if mention == 'finals':
            series = [item for item in series if item.get('isFinals') or item.get('round') == 4]
        else:
            series = [item for item in series if not item.get('isFinals') and mention in str(item.get('roundName', '')).casefold()]
    return series


def _playoff_game(request):
    candidates = _matching_series(request, get_playoff_games_and_series(request.season))
    if not candidates:
        raise AskResolutionError('not_found', 'No matching playoff series was recorded.')
    if len(candidates) != 1:
        raise AskResolutionError('needs_clarification', 'Specify both teams and a unique playoff round.')
    games = sorted(candidates[0].get('games', []), key=lambda game: (str(game.get('date', '')), str(game.get('gameId', ''))))
    if request.game_number is None:
        raise AskResolutionError('needs_clarification', 'Which game of the series do you mean?')
    if not 1 <= request.game_number <= len(games):
        raise AskResolutionError('not_found', 'That series game was not found.')
    game = games[request.game_number-1]
    return {**game, 'gameDate': str(game.get('date', ''))[:10]}


def retrieve_answer(resolved: ResolvedRequest) -> tuple[dict, bool]:
    try:
        if resolved.intent == 'game_search':
            games = _search_games(resolved)
            if not games:
                return _empty('not_found', 'No matching games found.')
            return {'status': 'ok', 'items': [_game_item(game) for game in games]}, all(game.get('gameStatus') == 3 for game in games)
        if resolved.intent == 'boxscore_stats':
            games = [_playoff_game(resolved)] if resolved.season else _search_games(resolved)
            if not games:
                return _empty('not_found', 'No matching game found.')
            if not resolved.season and resolved.operation == 'player_stats' and not resolved.team_ids:
                from server.services.ask_player_lookup import find_player_game_id
                game_id = find_player_game_id(resolved.player_name, resolved.start_date)
                games = [game for game in games if str(game.get('gameId')) == game_id]
                if not games:
                    return _empty('not_found', 'The player’s game was not found on that date’s scoreboard.')
            if len(games) != 1:
                raise AskResolutionError('needs_clarification', 'More than one game matches. Specify a date and both teams.')
            game = games[0]
            if game.get('gameStatus') == 1 or game.get('boxscoreAvailable') is False:
                return _empty('not_found', 'A boxscore is not available for this game.')
            boxscore = fetch_boxscoretraditional(str(game['gameId']))
            items = calculate_boxscore_stats(boxscore, resolved.statistics, resolved.player_name,
                                             operation=resolved.operation, team_ids=resolved.team_ids,
                                             context=_boxscore_context(resolved, game))
            for item in items:
                item['links'] = [_game_link(str(game['gameId']), game.get('gameDate'))]
            return {'status': 'ok', 'items': items}, not resolved.season and game.get('gameStatus') == 3
        if resolved.intent in {'playoff_series', 'postseason_summary'}:
            payload = get_playoff_games_and_series(resolved.season)
            series = _matching_series(resolved, payload)
            if not series:
                return _empty('not_found', 'No matching postseason records found.')
            if resolved.intent == 'playoff_series':
                if len(series) != 1:
                    raise AskResolutionError('needs_clarification', 'Several series match. Include the round or both teams.')
                item = calculate_series_result(series[0])
                item['links'] = [_series_link(resolved.season, series[0])]
                return {'status': 'ok', 'items': [item]}, False
            games = [game for item in series for game in item.get('games', [])]
            context = f"{int(resolved.season[:4]) + 1} NBA playoffs"
            items = calculate_postseason_summary(games, series, team_ids=resolved.team_ids,
                                                 context=context)
            if not items:
                return _empty('not_found', 'No postseason game results were recorded.')
            for item in items:
                item['links'] = [{'label': 'Playoff bracket', 'path': f'/playoffs?season={resolved.season}', 'spoiler': True}]
            # Existing historical playoff records lack explicit completion status.
            return {'status': 'ok', 'items': items}, False
        return _empty('unsupported', 'This request is not supported.')
    except AskResolutionError as error:
        return _empty(error.status, error.message)
    except (nba_stats_client.UpstreamUnavailableError, nba_stats_client.UpstreamBadResponseError):
        return _empty('unavailable', 'NBA data is temporarily unavailable. Please try again shortly.')
    except ValueError:
        return _empty('not_found', 'The requested NBA record is unavailable.')
