"""Offline fixture audit. Does not import candidate lookup or call providers."""
import collections
import datetime as dt
import difflib
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from server.ask.eval.runner import LabeledCase

FIXTURE = ROOT / 'server/tests/ask/fixtures/eval/unseen-two-2026-09-29.json'
OUT = ROOT / 'docs/verification/ask-unseen-two-2026-09-29-preflight.json'

def norm(text):
    return ' '.join(re.sub(r'[^\w\s]', ' ', text.casefold()).split())

def questions(value):
    if isinstance(value, dict):
        for key in ('question', 'utterance'):
            if isinstance(value.get(key), str):
                yield value[key]
        for child in value.values():
            yield from questions(child)
    elif isinstance(value, list):
        for child in value:
            yield from questions(child)

raw = json.loads(FIXTURE.read_text())['cases']
cases = [LabeledCase.from_json(c) for c in raw]
assert len(cases) == len({c.id for c in cases}) == len({norm(c.question) for c in cases}) == 100
assert all(0 < len(c.question) <= 300 and c.candidates is None and not c.also_accept for c in cases)
assert all('reference_time' in c and not c.get('candidates') for c in raw)
families = ('game_search', 'boxscore_stat', 'playoff_series', 'postseason_summary')
family_counts = {family: sum(family in c.tags for c in cases) for family in families}
assert all(count == 25 for count in family_counts.values())
assert collections.Counter(c.action for c in cases) == {'accept': 65, 'clarify': 25, 'unsupported': 10}
players = {row[0]: row[1] for row in json.loads((ROOT / 'server/ask/data/player_catalog.json').read_text())['players']}
teams = {row['team_id'] for row in json.loads((ROOT / 'server/ask/data/franchise_history.json').read_text())['franchises']}

def check_refs(value):
    if isinstance(value, dict):
        if 'player_id' in value:
            assert players[value['player_id']] == value['name'], value
        if 'team_id' in value:
            assert value['team_id'] in teams, value
        for child in value.values():
            check_refs(child)
    elif isinstance(value, list):
        for child in value:
            check_refs(child)

for case in raw:
    check_refs(case['expected'])
prior = {}
source_counts = {}
for folder in ('server/tests/ask/fixtures', 'server/tests/fixtures', 'docs/verification'):
    for path in sorted((ROOT / folder).rglob('*.json')):
        if path == FIXTURE or 'unseen-two-2026-09-29' in path.name:
            continue
        try:
            texts = list(questions(json.loads(path.read_text())))
        except (ValueError, UnicodeError):
            continue
        if texts:
            source_counts[str(path.relative_to(ROOT))] = len(texts)
        for question in texts:
            prior.setdefault(norm(question), str(path.relative_to(ROOT)))
exact, near, nearest = [], [], []
for case in cases:
    question = norm(case.question)
    if question in prior:
        exact.append({'case_id': case.id, 'source': prior[question]})
    matches = sorted(((difflib.SequenceMatcher(None, question, p).ratio(), p) for p in prior), reverse=True)
    ratio, match = matches[0]
    item = {'case_id': case.id, 'similarity': round(ratio, 4), 'source': prior[match]}
    nearest.append(item)
    if ratio >= .9:
        near.append(item)
within = []
for i, case in enumerate(cases):
    for other in cases[i+1:]:
        ratio = difflib.SequenceMatcher(None, norm(case.question), norm(other.question)).ratio()
        if ratio >= .9:
            within.append({'case_ids': [case.id, other.id], 'similarity': round(ratio,4)})
report = {
    'purpose': 'Pre-live schema, coverage and overlap audit; no candidate lookup or provider calls',
    'generated_at': dt.datetime.now(dt.timezone.utc).isoformat(),
    'fixture_sha256': hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),
    'prior_questions_examined': len(prior), 'source_question_counts': source_counts,
    'exact_duplicates': exact, 'similarity_at_least_0_9': near,
    'nearest_prior_by_case': nearest, 'within_set_similarity_at_least_0_9': within,
    'method': 'Casefold, replace punctuation with spaces, collapse whitespace, compare exact text and difflib.SequenceMatcher at 0.9. Lexical screening does not prove semantic novelty. A new author with no inherited conversation supplied labels without access to old cases, implementation or outputs.',
    'expected_actions': dict(collections.Counter(c.action for c in cases)),
    'family_counts': family_counts,
    'entity_references_valid': True,
    'label_audit': 'Parent reviewed all 100 labels before provider calls. Author replaced one near-duplicate unsupported question and three questions with multiple defensible clarification fields, added two former-home clauses by replacing two accepted game-search questions, and removed redundant context reference_time values. Labels were not adapted to candidate lookup or interpreter output.',
    'tag_counts': dict(sorted(collections.Counter(t for c in cases for t in c.tags).items())),
    'all_100_schema_valid': True,
}
OUT.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ('fixture_sha256','prior_questions_examined','exact_duplicates','similarity_at_least_0_9','within_set_similarity_at_least_0_9','expected_actions','tag_counts')},indent=2))
