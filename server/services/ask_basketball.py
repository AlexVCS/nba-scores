"""Typed basketball functions, with no model, prompt, HTTP, or request dependency.

These resolvers and calculators consume plain dictionaries. Future model tools
can wrap them directly without importing the parser or a web framework.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
import json
import math
from pathlib import Path
import re
import unicodedata
from typing import Any
from zoneinfo import ZoneInfo

NY = ZoneInfo('America/New_York')
CONSTANTS = Path(__file__).parents[1] / 'constants'
TEAM_IDS = json.loads((CONSTANTS / 'ask_teams.json').read_text())


class AskResolutionError(ValueError):
    def __init__(self, status: str, message: str):
        super().__init__(message)
        self.status, self.message = status, message


@dataclass(frozen=True)
class ResolvedRequest:
    intent: str
    operation: str | None = None
    season: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    team_ids: tuple[int, ...] = ()
    team_names: tuple[str, ...] = ()
    player_name: str | None = None
    game_id: str | None = None
    game_number: int | None = None
    round_mention: str | None = None
    statistics: tuple[str, ...] = ()

    @property
    def normalized_key(self) -> tuple[Any, ...]:
        return (self.intent, self.operation, self.season, self.start_date, self.end_date,
                self.team_ids, self.team_names, _norm(self.player_name or ''), self.game_id,
                self.game_number, self.round_mention, self.statistics)


STAT_KEYS = {
    'points': 'points', 'rebounds': 'reboundsTotal', 'assists': 'assists',
    'steals': 'steals', 'blocks': 'blocks', 'turnovers': 'turnovers',
    'fouls': 'foulsPersonal', 'minutes': 'minutes', 'field_goals': 'fieldGoalsMade',
    'three_pointers': 'threePointersMade', 'free_throws': 'freeThrowsMade',
    'field_goal_percentage': 'fieldGoalsPercentage', 'three_point_percentage': 'threePointersPercentage',
    'free_throw_percentage': 'freeThrowsPercentage', 'plus_minus': 'plusMinusPoints',
}
STAT_LABELS = dict(zip(STAT_KEYS.values(), [
    'Points', 'Rebounds', 'Assists', 'Steals', 'Blocks', 'Turnovers', 'Personal fouls', 'Minutes',
    'Field goals made', 'Three-pointers made', 'Free throws made', 'Field goal percentage',
    'Three-point percentage', 'Free throw percentage', 'Plus/minus',
]))


def _norm(value: str) -> str:
    text = ''.join(c for c in unicodedata.normalize('NFKD', value.casefold()) if not unicodedata.combining(c))
    return ' '.join(re.sub(r'[^a-z0-9]+', ' ', text).split())


def normalize_statistics(statistics) -> tuple[str, ...]:
    if any(stat not in STAT_KEYS for stat in statistics):
        raise AskResolutionError('unsupported', 'That statistic is not supported yet. Try points, rebounds, assists, or shooting statistics for one game.')
    return tuple(sorted({STAT_KEYS[stat] for stat in statistics}))


def resolve_team_mentions(mentions, aliases=None, records=None):
    """Use maintained aliases and NBA static franchise IDs, never model IDs."""
    if aliases is None:
        aliases = json.loads((CONSTANTS / 'ask_team_aliases.json').read_text())
    resolved = {}
    for mention in mentions:
        if mention['kind'] != 'team':
            continue
        text = _norm(mention['text'])
        matches = [name for name, values in aliases.items() if text in {_norm(name), *map(_norm, values)}]
        if len(matches) != 1 or matches[0] not in TEAM_IDS:
            raise AskResolutionError('needs_clarification', 'Please use the full team name so we can identify it.')
        name = matches[0]
        resolved[name] = TEAM_IDS[name]
    return sorted(resolved.items())


def _parse_day(text, now):
    value = ' '.join(text.casefold().strip().split())
    today = now.astimezone(NY).date()
    if value in {'today', 'tonight'}:
        return today, today
    if value in {'yesterday', 'last night'}:
        return today - timedelta(days=1), today - timedelta(days=1)
    if value == 'tomorrow':
        return today + timedelta(days=1), today + timedelta(days=1)
    if value in {'last week', 'previous week'}:
        end = today - timedelta(days=today.weekday() + 1)
        return end - timedelta(days=6), end
    if value == 'this week':
        first = today - timedelta(days=today.weekday())
        return first, first + timedelta(days=6)
    if value in {'last 7 days', 'last seven days', 'past 7 days', 'past seven days'}:
        return today - timedelta(days=7), today - timedelta(days=1)
    weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    if value.startswith('last ') and value[5:] in weekdays:
        offset = (today.weekday() - weekdays.index(value[5:])) % 7 or 7
        return today - timedelta(days=offset), today - timedelta(days=offset)
    # Both endpoints need an explicit year. Do not guess a missing year.
    cleaned = re.sub(r'(?<=\d)(st|nd|rd|th)\b', '', value)
    for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%B %d, %Y', '%B %d %Y', '%b %d, %Y', '%b %d %Y', '%d %B %Y', '%d %b %Y'):
        try:
            day = datetime.strptime(cleaned, fmt).date()
            return day, day
        except ValueError:
            pass
    raise AskResolutionError('needs_clarification', 'Please give a full date with a year, or a relative date such as yesterday or last week.')


def _season(text, now):
    value = text.casefold().strip().translate(str.maketrans({char: '-' for char in '‐‑‒–—−'}))
    if value in {'this season', 'current season', 'last season', 'previous season'}:
        today = now.astimezone(NY).date()
        start = today.year if today.month >= 10 else today.year - 1
        if value in {'last season', 'previous season'}:
            start -= 1
    else:
        value = re.sub(r'\b(nba|baa|the|season|playoffs|postseason|finals)\b', '', value).strip()
        if re.fullmatch(r'\d{4}', value):
            start = int(value) - 1
        else:
            match = re.fullmatch(r'(\d{4})[-/](\d{2}|\d{4})', value)
            if not match or int(match[2]) != (int(match[1])+1) % (100 if len(match[2]) == 2 else 10000):
                raise AskResolutionError('needs_clarification', 'Use a playoff year such as 2024 or a season such as 2023-24.')
            start = int(match[1])
    if not 1946 <= start <= now.astimezone(NY).year:
        raise AskResolutionError('not_found', 'That season is outside the available NBA and BAA records.')
    return f'{start}-{(start+1)%100:02d}'


def resolve_date_expressions(expressions, now):
    if now.tzinfo is None:
        raise AskResolutionError('needs_clarification', 'A timezone-aware reference time is required.')
    if not expressions:
        return None, None, None
    seasons = [e for e in expressions if e['kind'] == 'season']
    if seasons:
        if len(expressions) != 1:
            raise AskResolutionError('needs_clarification', 'Use one playoff season or a single date range.')
        return None, None, _season(seasons[0]['text'], now)
    if len(expressions) > 2:
        raise AskResolutionError('needs_clarification', 'Please search one date range at a time.')
    text = expressions[0]['text']
    if len(expressions) == 1 and expressions[0]['kind'] == 'range':
        parts = re.split(r'\s+(?:to|through|until)\s+|\s*[–—]\s*', re.sub(r'^from\s+', '', text, flags=re.I), flags=re.I)
        if len(parts) != 2:
            raise AskResolutionError('needs_clarification', 'Give both dates with years, such as 2024-06-01 to 2024-06-07.')
        first, _ = _parse_day(parts[0], now)
        _, last = _parse_day(parts[1], now)
    else:
        first, last = _parse_day(text, now)
        if len(expressions) == 2:
            _, last = _parse_day(expressions[1]['text'], now)
    if not 0 <= (last-first).days <= 6:
        raise AskResolutionError('needs_clarification', 'Please limit a date search to seven consecutive days.')
    if first < date(1946, 11, 1):
        raise AskResolutionError('not_found', 'That date precedes the available NBA and BAA records.')
    return first, last, None


def _round(text):
    if not text:
        return None
    value = re.sub(r'\b\d{4}\b', '', text.casefold())
    if 'semifinal' in value or 'semi-final' in value or 'second round' in value:
        return 'semifinals'
    if 'conference' in value and 'final' in value:
        return 'conference finals'
    if 'first round' in value or '1st round' in value:
        return 'first round'
    if 'final' in value or 'championship' in value:
        return 'finals'
    raise AskResolutionError('needs_clarification', 'Please specify the first round, semifinals, conference finals, or NBA Finals.')


def resolve_request(interpretation, now, aliases=None, team_records=None):
    intent = interpretation['intent']
    if intent == 'unsupported':
        raise AskResolutionError(intent, 'This search supports games, single-game boxscore statistics, playoff series, and postseason summaries. Career stats and broad comparisons are not supported.')
    mentions = interpretation['mentions']
    if any(m['kind'] == 'unknown' for m in mentions):
        raise AskResolutionError('needs_clarification', 'Please use a full team or player name.')
    teams = resolve_team_mentions(mentions, aliases)
    players = [m['text'] for m in mentions if m['kind'] == 'player']
    if len(players) > 1 or len(teams) > 2:
        raise AskResolutionError('unsupported', 'Search for one player and at most two teams at a time.')
    first, last, season = resolve_date_expressions(interpretation['date_expressions'], now)
    operation = interpretation['operation']
    round_name = _round(interpretation['round_mention'])
    number = interpretation['game_number']
    stats = normalize_statistics(interpretation['statistics'])
    ambiguities = interpretation['ambiguities']
    complete_game_search = (operation == 'list' and teams and first and not players and
                            not stats and number is None and round_name is None and season is None)
    unresolved = [item for item in ambiguities
                  if not (complete_game_search and _norm(item['field']) in {'team', 'team name'})]
    if intent == 'needs_clarification' and complete_game_search and not unresolved:
        intent = 'game_search'
    elif intent == 'needs_clarification' or unresolved:
        raise AskResolutionError('needs_clarification', 'Please include a team and date, or a playoff year, round, and game number.')
    if intent == 'game_search':
        if operation != 'list' or players or stats or number or round_name or season:
            raise AskResolutionError('needs_clarification', 'For game searches, include a team and date or a date range of up to seven days.')
        if not first:
            raise AskResolutionError('needs_clarification', 'Which date or week do you mean?')
    elif intent == 'boxscore_stats':
        if operation not in {'player_stats', 'team_stats', 'leaders'} or not stats:
            raise AskResolutionError('needs_clarification', 'Specify a player, team total, or game leader and the statistic you want.')
        if operation == 'player_stats' and not players:
            raise AskResolutionError('needs_clarification', 'Which player do you mean?')
        if operation != 'player_stats' and players:
            raise AskResolutionError('needs_clarification', 'Ask for a player statistic or a game leader separately.')
        if operation == 'leaders' and (len(stats) != 1 or stats[0] == 'minutes'):
            raise AskResolutionError('unsupported', 'Choose one numeric statistic to find the game leader.')
        if season:
            if number is None or (not round_name and len(teams) < 2):
                raise AskResolutionError('needs_clarification', 'Include a playoff round or matchup and a game number.')
        elif not first:
            raise AskResolutionError('needs_clarification', 'Include a date for the game, or a playoff year, round, and game number.')
        elif not teams and operation != 'player_stats':
            raise AskResolutionError('needs_clarification', 'Which team’s game do you mean?')
        elif not teams and last != first:
            raise AskResolutionError('needs_clarification', 'Choose one game date for the player’s statistics.')
        elif number or round_name:
            raise AskResolutionError('needs_clarification', 'For a numbered playoff game, include its playoff year.')
    elif intent in {'playoff_series', 'postseason_summary'}:
        if not season:
            raise AskResolutionError('needs_clarification', 'Which playoff year do you mean?')
        if players or stats or number:
            raise AskResolutionError('unsupported', 'Postseason summaries cover team game and series results. Ask for player statistics in a specific game.')
        if intent == 'postseason_summary' and (operation != 'summary' or round_name):
            raise AskResolutionError('needs_clarification', 'Ask for a whole postseason summary or one playoff series.')
        if intent == 'playoff_series' and (operation != 'series_result' or not (teams or round_name)):
            raise AskResolutionError('needs_clarification', 'Include a team matchup or playoff round.')
    else:
        raise AskResolutionError('unsupported', 'This request is not supported.')
    return ResolvedRequest(intent=intent, operation=operation, season=season, start_date=first, end_date=last,
                           team_ids=tuple(sorted(t[1] for t in teams)), team_names=tuple(t[0] for t in teams),
                           player_name=players[0] if players else None, game_number=number,
                           round_mention=round_name, statistics=stats)


def _field(label, value, spoiler=True):
    return {'label': label, 'value': value, 'spoiler': spoiler}


def _team_id(team):
    return team.get('teamId', team.get('id'))


def _team_name(team):
    return ' '.join(filter(None, [team.get('teamCity'), team.get('teamName')])) or team.get('name') or team.get('tricode') or team.get('teamTricode') or 'Team'


def _ask_team(team):
    team_id = _team_id(team)
    if isinstance(team_id, bool) or not re.fullmatch(r'\d+', str(team_id or '')):
        return None
    return {'id': int(team_id),
            'tricode': str(team.get('teamTricode') or team.get('tricode') or ''),
            'name': _team_name(team)}


def _ask_teams(teams):
    values = [_ask_team(team) for team in teams]
    return values if all(values) else []


def _player_name(player):
    return player.get('name') or ' '.join(filter(None, [player.get('firstName'), player.get('familyName')])) or player.get('nameI') or 'Player'


def calculate_boxscore_stats(game, requested, player_name=None, operation='player_stats', team_ids=(), context=None):
    game_teams = [game.get('homeTeam') or {}, game.get('awayTeam') or {}]
    teams = game_teams
    if team_ids:
        teams = [team for team in teams if _team_id(team) in team_ids]
    if operation == 'team_stats':
        rows = [(team, _team_name(team), team) for team in teams]
    else:
        rows = [(player, _player_name(player), team) for team in teams for player in team.get('players', [])]
        if player_name:
            name = _norm(player_name)
            exact = [(row, label, team) for row, label, team in rows if _norm(label) == name]
            rows = exact or [(row, label, team) for row, label, team in rows if _norm(label).endswith(' '+name) or _norm(row.get('firstName', '')) == name]
            if len(rows) > 1:
                raise AskResolutionError('needs_clarification', 'Several players match that name. Please use the full name.')
    if not rows:
        raise AskResolutionError('not_found', 'No matching player or team statistics were recorded for this game.')
    def values(row):
        stats = row.get('statistics') or {}
        return [stats.get(stat) for stat in requested]
    def available(value):
        return value is not None and (not isinstance(value, float) or math.isfinite(value))
    if operation == 'leaders':
        if len(requested) != 1:
            raise AskResolutionError('unsupported', 'Choose one statistic to find a leader.')
        # Skip nonparticipants, but never rank a partial collection of recorded players.
        rows = [(row, label, team) for row, label, team in rows if row.get('played') not in {'0', False}]
        if not rows or any(not isinstance(values(row)[0], (float, int)) or not available(values(row)[0]) for row, _, _ in rows):
            raise AskResolutionError('not_found', 'Leader statistics are incomplete for this game.')
        maximum = max(values(row)[0] for row, _, _ in rows)
        rows = [(row, label, team) for row, label, team in rows if values(row)[0] == maximum]
    items = []
    for row, name, team in rows:
        recorded = values(row)
        if not all(available(value) for value in recorded):
            raise AskResolutionError('not_found', 'At least one requested statistic is unavailable for this game.')
        fields = []
        for stat, value in zip(requested, recorded):
            if stat.endswith('Percentage') and isinstance(value, (int, float)):
                value = f'{value * 100:.1f}%'
            fields.append(_field(STAT_LABELS.get(stat, stat), value))
        player_id = None if operation == 'team_stats' else row.get('personId', row.get('playerId', row.get('id')))
        if isinstance(player_id, bool) or not isinstance(player_id, int):
            player_id = None
        items.append({'kind': 'statistic', 'title': name, 'title_spoiler': True,
                      'fields': fields, 'links': [], 'context': context,
                      'teams': [value] if (value := _ask_team(team)) else [],
                      'player_id': player_id})
    return items


def calculate_series_result(series):
    fields = []
    for index, team in enumerate(series.get('teams', []), 1):
        team_id = _team_id(team)
        fields.extend([_field(f'Team {index}', _team_name(team)),
                       _field(f'Team {index} wins', (series.get('wins') or {}).get(str(team_id), (series.get('wins') or {}).get(team_id)))])
    winner = series.get('winnerTeamTricode')
    if winner:
        fields.append(_field('Series winner', winner))
    return {'kind': 'series', 'title': series.get('roundName') or 'Playoff series',
            'title_spoiler': True, 'fields': fields, 'links': [],
            'context': series.get('roundName') or 'Playoff series',
            'teams': _ask_teams(series.get('teams', []))}


def calculate_postseason_summary(games, series=None, team_ids=(), context=None):
    unique = {game['gameId']: game for game in games if game.get('gameId')}
    totals = {}
    for game in unique.values():
        for side in ('homeTeam', 'awayTeam'):
            team = game.get(side) or {}
            team_id = _team_id(team)
            if team_id is None or (team_ids and team_id not in team_ids):
                continue
            total = totals.setdefault(team_id, {'team': team, 'name': _team_name(team), 'wins': 0, 'losses': 0, 'unknown': 0})
            winner = game.get('winnerTeamId')
            if winner is None:
                total['unknown'] += 1
            elif winner == team_id:
                total['wins'] += 1
            else:
                total['losses'] += 1
    items = []
    for total in totals.values():
        fields = [_field('Game wins', total['wins']), _field('Game losses', total['losses'])]
        if total['unknown']:
            fields.append(_field('Games without a recorded result', total['unknown']))
        items.append({'kind': 'postseason', 'title': total['name'], 'title_spoiler': True,
                      'fields': fields, 'links': [],
                      'context': context,
                      'teams': [value] if (value := _ask_team(total['team'])) else []})
    return items
