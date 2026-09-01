"""Two-step low-intervention workflow: freeze a dry-run plan, then execute it."""
import argparse
import hashlib
import json
import math
from datetime import datetime
from pathlib import Path

from bilateral_media_extractor import GIB, build_gdelt_sql, month_windows, parser as extractor_parser, pilot_window, run_gdelt
from usage_ledger import LEDGER, refresh

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / 'workflow_config.json'
PLANS = ROOT / 'output/workflow/plans'


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def extractor_args(config, start, end, execute=False):
    values = ['gdelt', '--project', config['project'], '--start', start, '--end', end,
              '--profile', config['profile'], '--output', config['output'],
              '--location', config['location'], '--max-gib', str(config['per_query_gib']),
              '--max-total-gib', str(config['per_run_gib'])]
    if execute:
        values.append('--execute')
    return extractor_parser().parse_args(values)


def sql_items(args):
    result = []
    for window in month_windows(args.start, args.end):
        window = pilot_window(window, args.pilot_days, args.pilot_start_day)
        sql = build_gdelt_sql(window, args.profile)
        result.append(dict(window=window.label, sql_sha256=hashlib.sha256(sql.encode()).hexdigest()))
    return result


def make_plan(start, end, config_path=CONFIG_PATH):
    config = load(config_path)
    args = extractor_args(config, start, end)
    desired_sql = sql_items(args)
    ledger = refresh()
    completed_hashes = {e['sql_sha256']: e['receipt'] for e in ledger['entries'] if e.get('sql_sha256')}
    duplicate = [completed_hashes[i['sql_sha256']] for i in desired_sql if i['sql_sha256'] in completed_hashes]
    target = str((ROOT / config['output'] / config['profile']).resolve())
    external_duplicate = [p for p in duplicate if not p.startswith(target)]
    if external_duplicate:
        raise RuntimeError('Equivalent query already completed elsewhere; reuse its receipt instead of planning again: ' + external_duplicate[0])
    run_gdelt(args)
    estimate_path = ROOT / config['output'] / config['profile'] / 'dry_run_estimates.csv'
    import csv
    with estimate_path.open(encoding='utf-8-sig', newline='') as handle:
        estimates = list(csv.DictReader(handle))
    values = [int(r['estimated_bytes']) for r in estimates if r['status'] != 'cached']
    if any(v > config['per_query_gib'] * GIB for v in values) or sum(values) > config['per_run_gib'] * GIB:
        raise RuntimeError('Plan exceeds configured per-query or per-run budget')
    ledger = refresh()
    now_month = datetime.now().astimezone().strftime('%Y-%m')
    used = ledger['totals_by_calendar_month'].get(now_month, 0)
    reserved = sum(max(10 * 1024**2, math.ceil(v / 1024**2) * 1024**2) for v in values)
    if used + reserved > config['monthly_ledger_gib'] * GIB:
        raise RuntimeError('Plan exceeds cumulative monthly ledger budget')
    plan = dict(schema_version=1, status='planned_not_executed', created_at=datetime.now().astimezone().isoformat(),
                config=config, config_sha256=digest(config), start=start, end=end,
                estimates=estimates, estimated_new_bytes=sum(values), reserved_maximum_bytes=reserved, ledger_month=now_month,
                ledger_bytes_before=used, sql=sql_items(args))
    identity = digest(plan)[:20]
    PLANS.mkdir(parents=True, exist_ok=True)
    path = PLANS / f'{start}_{end}_{config["profile"]}_{identity}.json'
    path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Frozen plan: {path}')
    return path


def execute_plan(path):
    path = Path(path)
    plan = load(path)
    if plan.get('status') != 'planned_not_executed' or digest(plan['config']) != plan['config_sha256']:
        raise RuntimeError('Invalid or modified plan')
    args = extractor_args(plan['config'], plan['start'], plan['end'], execute=True)
    if sql_items(args) != plan['sql']:
        raise RuntimeError('SQL changed after planning; create a new plan')
    current = refresh()
    month = datetime.now().astimezone().strftime('%Y-%m')
    used = current['totals_by_calendar_month'].get(month, 0)
    if used + plan['reserved_maximum_bytes'] > plan['config']['monthly_ledger_gib'] * GIB:
        raise RuntimeError('Cumulative monthly ledger budget changed/exceeded after planning; create a new plan')
    executed = ROOT / 'output/workflow/executions' / (path.stem + '.executed.json')
    if executed.exists():
        raise RuntimeError(f'Plan already has an execution record: {executed}')
    run_gdelt(args)
    after = refresh()
    executed.parent.mkdir(parents=True, exist_ok=True)
    record = dict(plan=str(path.resolve()), completed_at=datetime.now().astimezone().isoformat(),
                  jobs_before=current['job_count'], jobs_after=after['job_count'],
                  bytes_before=current['total_bytes_billed'], bytes_after=after['total_bytes_billed'])
    executed.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Execution record: {executed}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    plan = sub.add_parser('plan')
    plan.add_argument('--start', required=True)
    plan.add_argument('--end', required=True)
    plan.add_argument('--config', default=str(CONFIG_PATH))
    execute = sub.add_parser('execute')
    execute.add_argument('--plan', required=True)
    args = parser.parse_args()
    make_plan(args.start, args.end, args.config) if args.command == 'plan' else execute_plan(args.plan)
