"""Reproduce raw -> validate -> safe corrections -> clean/quarantine evidence.

Runs against a temporary database, never the database used by the web app.
"""
import hashlib
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app import Store, FIELDS


def issue_counts(report):
    return dict(Counter(i['code'] for r in report['products'] for i in r['issues']))


def main():
    original = ROOT/'data/raw/products.csv'
    provenance = json.loads((ROOT/'data/raw/PROVENANCE.json').read_text(encoding='utf-8'))
    digest_before = hashlib.sha256(original.read_bytes()).hexdigest()
    if digest_before != provenance['sha256']:
        raise ValueError('Original CSV checksum differs from recorded source; stop for review.')

    with tempfile.TemporaryDirectory() as temp:
        store = Store(Path(temp)/'pipeline.sqlite3')
        before = store.report()
        corrections = store.normalize()
        after = store.report()
        exported = store.export()
        after_by_id = {r['id']: r for r in after['products']}
        evidence = []
        for row in before['products']:
            if not row['issues']:
                continue
            updated = after_by_id[row['id']]
            evidence.append({
                'row_id': row['id'], 'product_id': row['product_id'], 'source': row['source'],
                'before': {f: row[f] for f in FIELDS},
                'after': {f: updated[f] for f in FIELDS},
                'detected_before': row['issues'], 'remaining_after': updated['issues'],
                'status_before': row['status'], 'status_after': updated['status'],
                'action': 'safe rule correction; see correction_log.json' if any(row[f] != updated[f] for f in FIELDS)
                          else 'quarantine for human review; no unsupported correction',
            })
        summary = {
            'snapshot_type': 'reproducible pipeline from original + synthetic fixtures; separate from live app edits',
            'generated_at': after['checked_at'], 'policy_version': after['policy']['version'],
            'original_sha256': digest_before, 'total': before['total'],
            'status_before': before['summary'], 'status_after': after['summary'],
            'issues_before': issue_counts(before), 'issues_after': issue_counts(after),
            'corrected_rows': corrections['changed'], 'exported': exported,
            'evidence': evidence,
        }
        target = ROOT/'data/cleaned/pipeline_evidence.json'
        target.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')

    assert hashlib.sha256(original.read_bytes()).hexdigest() == digest_before
    print('Original CSV checksum verified and preserved.')
    print('Status before:', summary['status_before'])
    print('Status after:', summary['status_after'])
    print('Corrected rows:', summary['corrected_rows'])
    print('Clean / quarantine:', exported['clean'], '/', exported['quarantine'])
    print('Evidence:', target.relative_to(ROOT))


if __name__ == '__main__':
    main()
