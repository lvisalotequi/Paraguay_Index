"""Build a cumulative, deduplicated BigQuery usage ledger from receipts."""
import argparse
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / 'output'
LEDGER = OUTPUT / 'query_usage_ledger.json'


def sha(path):
    # SQL identities are based on query text, independent of Windows/Unix
    # newline encoding on disk.
    text = path.read_text(encoding='utf-8')
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def build(output_root=OUTPUT):
    jobs = {}
    for receipt in sorted(Path(output_root).rglob('*.complete.json')):
        data = json.loads(receipt.read_text(encoding='utf-8'))
        job_id = data.get('job_id')
        billed = data.get('bytes_billed')
        if not job_id or not isinstance(billed, int) or billed < 0:
            raise ValueError(f'Invalid query receipt: {receipt}')
        sql_path = receipt.with_name(receipt.name.replace('.complete.json', '.sql'))
        sql_hash = data.get('sql_sha256') or (sha(sql_path) if sql_path.exists() else None)
        completed = data.get('completed_at')
        if completed:
            stamp = datetime.fromisoformat(completed)
            if stamp.tzinfo is None:
                raise ValueError(f'Naive completed_at: {receipt}')
        else:
            stamp = datetime.fromtimestamp(receipt.stat().st_mtime, timezone.utc)
        item = dict(job_id=job_id, project=data.get('project'), profile=data.get('profile'),
                    window=data.get('window'), completed_at=stamp.isoformat(),
                    calendar_month=stamp.strftime('%Y-%m'), bytes_billed=billed,
                    bytes_processed=data.get('bytes_processed'), sql_sha256=sql_hash,
                    csv_sha256=data.get('csv_sha256'), receipt=str(receipt.resolve()))
        if job_id in jobs and jobs[job_id] != item:
            raise ValueError(f'Conflicting duplicate job receipt: {job_id}')
        jobs[job_id] = item
    entries = sorted(jobs.values(), key=lambda x: (x['completed_at'], x['job_id']))
    per_month = defaultdict(int)
    for item in entries:
        per_month[item['calendar_month']] += item['bytes_billed']
    return dict(schema_version=1, generated_at=datetime.now(timezone.utc).isoformat(),
                source='Unique *.complete.json job receipts; legacy completion dates inferred from receipt mtime.',
                job_count=len(entries), total_bytes_billed=sum(x['bytes_billed'] for x in entries),
                totals_by_calendar_month=dict(sorted(per_month.items())), entries=entries)


def refresh(output_root=OUTPUT, ledger_path=LEDGER):
    result = build(output_root)
    Path(ledger_path).parent.mkdir(parents=True, exist_ok=True)
    Path(ledger_path).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root', default=str(OUTPUT))
    parser.add_argument('--ledger', default=str(LEDGER))
    args = parser.parse_args()
    result = refresh(args.output_root, args.ledger)
    print(f"Ledger: {result['job_count']} unique jobs, {result['total_bytes_billed']} bytes; {args.ledger}")
