"""Check recorded manual evidence; missing/blocked evidence never passes."""
import argparse
import hashlib
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--filter', choices=('visual',), required=True)
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
print(f'{args.filter}: PASS')
