"""Check recorded manual evidence; missing/blocked evidence never passes."""
import argparse
import hashlib
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--filter', choices=('visual', 'quality'), required=True)
args = parser.parse_args()
feature = Path(__file__).resolve().parent
root = feature.parents[2]
record = json.loads((feature / f'{args.filter}-evidence.json').read_text())
assert record['status'] == 'PASS', f"{args.filter} evidence {record['status']}: {record.get('reason', '')}"
assert record['browser'] and record['observed_at']
if args.filter == 'visual':
    expected = {(surface, width, state) for surface in ('page', 'fab') for width in (1440, 390) for state in ('recording', 'transcribing', 'review')}
    assert {(r['surface'], r['width'], r['state']) for r in record['captures']} == expected
    for row in record['captures']:
        path = root / row['path']
        assert path.is_file(), f'Missing capture: {path}'
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row['sha256'], f'Changed capture: {path}'
        assert row['reference'] and row['copy'] == 'PASS' and row['arrangement'] == 'PASS'
        assert row['observation']
else:
    assert record['native'] is True and record['process_locally'] is False and record['language'] == 'pt-BR'
    assert {r['category'] for r in record['samples']} == {'short question', 'negation', 'number', 'programming term', 'pause', 'moderate noise'}
    assert len(record['samples']) == 6
    for row in record['samples']:
        assert row['reference'].strip() and isinstance(row['transcript'], str) and row['limitations'].strip()
        assert row['outcome'] in ('recognized', 'native-error') and row['errors'] is not None
print(f'{args.filter}: PASS')
