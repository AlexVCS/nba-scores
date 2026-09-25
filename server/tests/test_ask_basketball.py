from datetime import date, datetime, timezone
from pathlib import Path
import json

import pytest

from server.services.ask_basketball import (
    AskResolutionError, calculate_boxscore_stats, calculate_postseason_summary,
    calculate_series_result, resolve_request,
)

NOW = datetime(2026, 9, 11, 1, tzinfo=timezone.utc)
BOS, DAL = 1610612738, 1610612742


def request(intent='game_search', **kwargs):
    return {'intent': intent, 'operation': 'list', 'mentions': [],
            'date_expressions': [{'text': 'yesterday', 'kind': 'relative'}],
            'round_mention': None, 'game_number': None, 'statistics': [],
            'ambiguities': [], 'unsupported_reason': None, **kwargs}


@pytest.mark.parametrize('round_name', ['Conference Semifinals', 'Eastern Conference Semi-Finals'])
def test_conference_semifinals_are_not_resolved_as_conference_finals(round_name):
    result = resolve_request(request(
        'playoff_series', operation='series_result', round_mention=round_name,
        date_expressions=[{'text': '2024', 'kind': 'season'}],
    ), NOW)
    assert result.round_mention == 'semifinals'


@pytest.mark.parametrize(('text', 'start', 'end'), [
    ('today', date(2026,9,10), date(2026,9,10)),
    ('last night', date(2026,9,9), date(2026,9,9)),
    ('last week', date(2026,8,31), date(2026,9,6)),
    ('this week', date(2026,9,7), date(2026,9,13)),
    ('last Friday', date(2026,9,4), date(2026,9,4)),
    ('March 3, 2025', date(2025,3,3), date(2025,3,3)),
    ('Jun 17 2024', date(2024,6,17), date(2024,6,17)),
])
def test_ny_relative_and_calendar_dates(text, start, end):
    result = resolve_request(request(date_expressions=[{'text':text,'kind':'relative'}]), NOW)
    assert (result.start_date, result.end_date) == (start,end)


def test_previous_calendar_week_across_dst_and_year():
    result = resolve_request(request(date_expressions=[{'text':'last week','kind':'relative'}]), datetime(2026,3,9,4,1,tzinfo=timezone.utc))
    assert (result.start_date,result.end_date) == (date(2026,3,2),date(2026,3,8))
    result = resolve_request(request(date_expressions=[{'text':'last week','kind':'relative'}]), datetime(2026,1,2,tzinfo=timezone.utc))
    assert (result.start_date,result.end_date) == (date(2025,12,22),date(2025,12,28))


@pytest.mark.parametrize('text', ['2024', '2023-24', '2023-2024', '2024 playoffs', '2023–24', '2023—24', '2023‑24'])
def test_playoff_year_conversion(text):
    result = resolve_request(request('postseason_summary',operation='summary',date_expressions=[{'text':text,'kind':'season'}]), NOW)
    assert result.season == '2023-24'
    assert result.start_date is None


@pytest.mark.parametrize('text', ['2024-06-07 to 2024-06-01', '2024-06-01 to 2024-06-08', '2024-02-30', 'March 3'])
def test_invalid_dates_abstain(text):
    with pytest.raises(AskResolutionError):
        resolve_request(request(date_expressions=[{'text':text,'kind':'range' if ' to ' in text else 'calendar_date'}]), NOW)


def test_aliases_resolve_to_same_id_and_cache_key():
    one = resolve_request(request(mentions=[{'kind':'team','text':'Cavs'}]),NOW)
    two = resolve_request(request(mentions=[{'kind':'team','text':'Cleveland Cavaliers'}]),NOW)
    assert one.team_ids == (1610612739,)
    assert one.normalized_key == two.normalized_key


def test_ambiguous_city_requires_clarification():
    with pytest.raises(AskResolutionError):
        resolve_request(request(mentions=[{'kind':'team','text':'LA'}]),NOW)


def test_missing_date_never_defaults_to_today():
    with pytest.raises(AskResolutionError):
        resolve_request(request(mentions=[{'kind':'team','text':'Lakers'}],date_expressions=[]),NOW)


@pytest.mark.parametrize('intent', ['game_search', 'needs_clarification'])
def test_known_team_and_date_satisfy_stale_team_ambiguity(intent):
    result = resolve_request(request(
        intent,
        mentions=[{'kind': 'team', 'text': 'Thunder'}],
        date_expressions=[{'kind': 'calendar_date', 'text': 'January 2, 2024'}],
        ambiguities=[{'field': 'team', 'reason': 'Which team do you mean?'}],
    ), NOW)
    assert result.intent == 'game_search'
    assert result.team_ids == (1610612760,)
    assert result.start_date == date(2024, 1, 2)


def test_missing_team_ambiguity_still_clarifies():
    with pytest.raises(AskResolutionError, match='include a team and date'):
        resolve_request(request(
            'needs_clarification', mentions=[],
            date_expressions=[{'kind': 'calendar_date', 'text': 'January 2, 2024'}],
            ambiguities=[{'field': 'team', 'reason': 'Which team do you mean?'}],
        ), NOW)


def test_team_ambiguity_is_not_discarded_for_other_intents():
    with pytest.raises(AskResolutionError, match='include a team and date'):
        resolve_request(request(
            'boxscore_stats', operation='team_stats',
            mentions=[{'kind': 'team', 'text': 'Thunder'}],
            date_expressions=[{'kind': 'calendar_date', 'text': 'January 2, 2024'}],
            statistics=['points'],
            ambiguities=[{'field': 'team', 'reason': 'Which team do you mean?'}],
        ), NOW)


def test_playoff_boxscore_resolves_selectors_without_game_id_guess():
    result = resolve_request(request('boxscore_stats',operation='leaders',statistics=['points'],
         mentions=[{'kind':'team','text':'Celtics'}],date_expressions=[{'kind':'season','text':'2024'}],
         round_mention='2024 Finals',game_number=4),NOW)
    assert result.team_ids == (BOS,)
    assert result.season == '2023-24'
    assert result.round_mention == 'finals'
    assert result.game_number == 4
    assert result.game_id is None


def test_model_abstention_reason_never_becomes_answer_prose():
    with pytest.raises(AskResolutionError) as caught:
        resolve_request(request('unsupported',unsupported_reason='Boston won 120-100'),NOW)
    assert '120' not in caught.value.message


def box():
    return {'homeTeam':{'teamId':BOS,'teamName':'Celtics','players':[
        {'firstName':'Jayson','familyName':'Tatum','personId':1,'statistics':{'points':30,'assists':5}},
        {'firstName':'Jaylen','familyName':'Brown','personId':2,'statistics':{'points':30,'assists':2}},
    ],'statistics':{'points':107}},'awayTeam':{'teamId':DAL,'teamName':'Mavericks','players':[
        {'firstName':'Luka','familyName':'Dončić','personId':3,'statistics':{'points':40,'assists':8}},
    ],'statistics':{'points':95}}}


def test_player_stats_match_names_and_all_requested_fields():
    items = calculate_boxscore_stats(box(),('points','assists'),'Tatum')
    assert len(items) == 1
    assert items[0]['title'] == 'Jayson Tatum'
    assert [field['value'] for field in items[0]['fields']] == [30,5]
    assert all(field['label'] not in ('Tatum','Jayson') for field in items[0]['fields'])
    assert items[0]['player_id'] == 1
    assert [team['id'] for team in items[0]['teams']] == [BOS]
    with pytest.raises(AskResolutionError):
        calculate_boxscore_stats(box(),('points','blocks'),'Tatum')


def test_accentless_player_name():
    assert calculate_boxscore_stats(box(),('points',),'Doncic')[0]['fields'][0]['value'] == 40


def test_leaders_rank_only_requested_team_and_preserve_ties():
    items = calculate_boxscore_stats(box(),('points',),operation='leaders',team_ids=(BOS,))
    assert {item['title'] for item in items} == {'Jayson Tatum','Jaylen Brown'}
    assert all(item['title_spoiler'] for item in items)
    assert calculate_boxscore_stats(box(),('points',),operation='leaders')[0]['title'] == 'Luka Dončić'


def test_team_totals_use_team_statistics():
    item = calculate_boxscore_stats(box(),('points',),operation='team_stats',team_ids=(BOS,))[0]
    assert item['fields'][0]['value'] == 107


def test_ambiguous_player_suffix_never_picks_first():
    game = box()
    game['awayTeam']['players'].append({'firstName':'Other','familyName':'Tatum','statistics':{'points':2}})
    with pytest.raises(AskResolutionError) as caught:
        calculate_boxscore_stats(game,('points',),'Tatum')
    assert caught.value.status == 'needs_clarification'


def test_real_repository_boxscore_statistics_shape():
    game = json.loads((Path(__file__).parents[2]/'exampleBoxScoreResponse.json').read_text())['game']
    leaders = calculate_boxscore_stats(game,('points',),operation='leaders')
    maximum = max(player['statistics']['points'] for side in ('homeTeam','awayTeam') for player in game[side]['players'])
    assert leaders and all(item['fields'][0]['value'] == maximum for item in leaders)


def test_series_labels_do_not_leak_team_names_or_assume_missing_wins_zero():
    item = calculate_series_result({'teams':[{'id':BOS,'name':'Celtics'},{'id':DAL,'name':'Mavericks'}],
         'wins':{str(BOS):4},'winnerTeamTricode':'BOS'})
    assert [f['label'] for f in item['fields']] == ['Team 1','Team 1 wins','Team 2','Team 2 wins','Series winner']
    assert item['fields'][3]['value'] is None
    assert all(f['spoiler'] for f in item['fields'])
    assert item['teams'] == [
        {'id': BOS, 'tricode': '', 'name': 'Celtics'},
        {'id': DAL, 'tricode': '', 'name': 'Mavericks'},
    ]
    assert all('winner' not in team for team in item['teams'])


def test_series_team_metadata_preserves_positions_or_abstains():
    item = calculate_series_result({'teams': [{'id': str(BOS), 'name': 'Celtics'}, {'name': 'Unknown'}]})
    assert item['teams'] == []


def test_postseason_deduplicates_games_and_separates_unrecorded_results():
    games = [{'gameId':'1','homeTeam':{'id':BOS,'name':'Celtics'},'awayTeam':{'id':DAL,'name':'Mavericks'},'winnerTeamId':BOS},
             {'gameId':'2','homeTeam':{'id':BOS,'name':'Celtics'},'awayTeam':{'id':DAL,'name':'Mavericks'},'winnerTeamId':None}]
    item = calculate_postseason_summary([*games,games[0]],team_ids=(BOS,), context='2024 NBA playoffs')[0]
    assert [f['value'] for f in item['fields']] == [1,0,1]
    assert item['context'] == '2024 NBA playoffs'
    assert item['teams'][0]['id'] == BOS


@pytest.mark.parametrize('player', ['Shai Gilgeous-Alexander', 'Shai Gilgeous–Alexander'])
def test_player_and_date_do_not_require_a_team(player):
    result = resolve_request(request('boxscore_stats', operation='player_stats',
        mentions=[{'kind': 'player', 'text': player}],
        date_expressions=[{'kind': 'calendar_date', 'text': 'January 2, 2024'}],
        statistics=['points']), NOW)
    assert result.team_ids == ()
    assert result.player_name == player
    assert result.start_date == result.end_date == date(2024, 1, 2)


def test_player_without_team_needs_one_date_not_a_week():
    with pytest.raises(AskResolutionError, match='one game date'):
        resolve_request(request('boxscore_stats', operation='player_stats',
            mentions=[{'kind': 'player', 'text': 'Shai Gilgeous-Alexander'}],
            date_expressions=[{'kind': 'relative', 'text': 'last week'}], statistics=['points']), NOW)
