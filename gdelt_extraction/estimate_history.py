"""Parallel BigQuery dry-run estimator; no data extraction or billing changes."""
import argparse
import csv
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from pathlib import Path

from bilateral_media_extractor import GIB, MonthWindow, build_gdelt_sql, month_windows, parse_month
from usage_ledger import refresh

ROOT = Path(__file__).resolve().parent


def batches(rows, cap_bytes):
    result, current, total = [], [], 0
    for row in rows:
        value = 0 if row['status'] == 'completed' else row['estimated_bytes']
        if value > cap_bytes:
            raise ValueError(f"A single month exceeds batch target: {row['month']}")
        if current and total + value > cap_bytes:
            result.append(dict(months=[r['month'] for r in current], estimated_new_bytes=total))
            current, total = [], 0
        current.append(row)
        total += value
    if current:
        result.append(dict(months=[r['month'] for r in current], estimated_new_bytes=total))
    return result


def reconcile_completed(rows, ledger):
    """Mark matching dry-run rows completed without repeating dry runs."""
    completed = {e['sql_sha256']: e for e in ledger['entries'] if e.get('sql_sha256')}
    result = []
    for original in rows:
        row = dict(original)
        item = completed.get(row['sql_sha256'])
        if item:
            row['status'] = 'completed'
            row['completed_job_id'] = item['job_id']
            row['receipt'] = item['receipt']
        result.append(row)
    return result


def estimate(project, start, end, output, workers=4, batch_gib=100):
    from google.cloud import bigquery
    ledger = refresh()
    completed = {e['sql_sha256']: e for e in ledger['entries'] if e.get('sql_sha256')}
    work, rows = [], []
    for window in month_windows(start, end):
        sql = build_gdelt_sql(window, 'proxy_b_metrics')
        sql_hash = hashlib.sha256(sql.encode()).hexdigest()
        if sql_hash in completed:
            item = completed[sql_hash]
            value = item.get('bytes_processed')
            rows.append(dict(month=window.label, period_start=max(window.start, date(2015, 2, 19)).isoformat(),
                             period_end=window.end.isoformat(), partial_month=window.start < date(2015, 2, 19),
                             status='completed', estimated_bytes=value if isinstance(value, int) else item['bytes_billed'],
                             sql_sha256=sql_hash, completed_job_id=item['job_id'], receipt=item['receipt']))
        else:
            work.append((window, sql, sql_hash))
    def dry(item):
        window, sql, sql_hash = item
        client = bigquery.Client(project=project, location='US')
        job = client.query(sql, job_config=bigquery.QueryJobConfig(dry_run=True, use_query_cache=False))
        if job.total_bytes_processed is None:
            raise RuntimeError(f'Missing estimate: {window.label}')
        return dict(month=window.label, period_start=max(window.start, date(2015, 2, 19)).isoformat(),
                    period_end=window.end.isoformat(), partial_month=window.start < date(2015, 2, 19),
                    status='dry_run', estimated_bytes=int(job.total_bytes_processed),
                    sql_sha256=sql_hash, completed_job_id=None, receipt=None)
    total_months = len(work) + len(rows)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(dry, item) for item in work]
        for future in as_completed(futures):
            row = future.result()
            rows.append(row)
            print(f"[{len(rows)}/{total_months}] {row['month']}: {row['estimated_bytes']/GIB:.3f} GiB", flush=True)
    rows.sort(key=lambda r: r['month'])
    groups = batches(rows, int(batch_gib * GIB))
    result = dict(schema_version=1, generated_at=datetime.now().astimezone().isoformat(), project=project,
                  profile='proxy_b_metrics', start=start.isoformat(), end=end.isoformat(),
                  note='Dry runs do not extract data. Completed SQL hashes are reused and excluded from new-byte batch totals.',
                  total_months=len(rows), completed_months=sum(r['status']=='completed' for r in rows),
                  total_estimated_bytes=sum(r['estimated_bytes'] for r in rows),
                  new_estimated_bytes=sum(r['estimated_bytes'] for r in rows if r['status']!='completed'),
                  batch_target_gib=batch_gib, batches=groups, months=rows)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / f'estimate_{start:%Y-%m}_{end:%Y-%m}.json'
    csv_path = output / f'estimate_{start:%Y-%m}_{end:%Y-%m}.csv'
    if json_path.exists() or csv_path.exists():
        raise FileExistsError('Refusing to overwrite an existing historical estimate')
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    with csv_path.open('x', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    print(f"Estimate: {result['total_estimated_bytes']/GIB:.3f} GiB total; {result['new_estimated_bytes']/GIB:.3f} GiB new; {len(groups)} batches. {json_path}")
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', default='leandro-gdelt-2026-abc')
    parser.add_argument('--start', type=parse_month)
    parser.add_argument('--end', type=parse_month)
    parser.add_argument('--output', default='output/historical_estimates')
    parser.add_argument('--workers', type=int, choices=range(1, 9), default=4)
    parser.add_argument('--batch-gib', type=float, default=100)
    parser.add_argument('--reconcile', help='Existing estimate JSON to reconcile with completed-query receipts; no BigQuery calls')
    args = parser.parse_args()
    if args.reconcile:
        source = Path(args.reconcile)
        prior = json.loads(source.read_text(encoding='utf-8'))
        rows = reconcile_completed(prior['months'], refresh())
        prior['generated_at'] = datetime.now().astimezone().isoformat()
        prior['note'] = 'Reconciled locally with completed SQL hashes; no BigQuery calls were made.'
        prior['completed_months'] = sum(r['status'] == 'completed' for r in rows)
        prior['new_estimated_bytes'] = sum(r['estimated_bytes'] for r in rows if r['status'] != 'completed')
        prior['batches'] = batches(rows, int(args.batch_gib * GIB))
        prior['months'] = rows
        destination = source.with_name(source.stem + '_reconciled.json')
        if destination.exists():
            raise FileExistsError(f'Refusing to overwrite {destination}')
        destination.write_text(json.dumps(prior, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"Reconciled locally: {prior['completed_months']} completed; "
              f"{prior['new_estimated_bytes']/GIB:.3f} GiB new; {len(prior['batches'])} batches. {destination}")
        raise SystemExit(0)
    if args.start is None or args.end is None:
        raise SystemExit('--start and --end are required unless --reconcile is used')
    if args.start > args.end or args.start < date(2015, 2, 1):
        raise SystemExit('Use an ordered range beginning no earlier than 2015-02')
    estimate(args.project, args.start, args.end, args.output, args.workers, args.batch_gib)
