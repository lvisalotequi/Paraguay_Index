"""Extract monthly Paraguay--United States media indicators.

The script is deliberately safe by default: BigQuery commands only perform a
free dry run unless ``--execute`` is supplied.  Executed queries also carry a
hard ``maximum_bytes_billed`` limit.

Examples
--------
Estimate one month without running it::

    python bilateral_media_extractor.py gdelt --project MY_PROJECT \
        --start 2025-01 --end 2025-01

Execute after reviewing the estimate::

    python bilateral_media_extractor.py gdelt --project MY_PROJECT \
        --start 2025-01 --end 2025-01 --execute --max-gib 1 --max-total-gib 1

Google Trends (unofficial fallback; see HANDOFF_CONTEXT.md)::

    python bilateral_media_extractor.py trends --start 2015-03 --end 2026-07
"""

from __future__ import annotations

import argparse
import calendar
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable, Sequence


GIB = 1024**3
TIB = 1024**4
GDELT_START = date(2015, 2, 19)

# Signals intentionally cover public institutions, collective citizens and
# institutional economic relations. They are configurable in code and the SQL
# is always saved beside the output for auditability.
INSTITUTION_THEME_RE = (
    r"(^|;)(GOVERNMENT|GENERAL_GOVERNMENT|LEGISLATION|PARLIAMENT|"
    r"JUDICIARY|MILITARY|ARMEDCONFLICT|SECURITY_SERVICES|POLICE|"
    r"DIPLOMATIC|DIPLOMACY|EMBASSY|FOREIGN_AID|AID_|USAID|"
    r"TAX_|TARIFF|TRADE|INVESTMENT|ECON_|SANCTIONS|"
    r"MIGRATION|IMMIGRATION|REFUGEES|CITIZEN|CIVIL_SOCIETY|"
    r"EDUCATION|UNIVERSITY|HUMAN_RIGHTS)"
)


@dataclass(frozen=True)
class MonthWindow:
    label: str
    start: date
    end: date


def parse_month(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m").date().replace(day=1)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Use YYYY-MM, for example 2025-01") from exc


def last_complete_month(today: date | None = None) -> date:
    current = (today or date.today()).replace(day=1)
    if current.month == 1:
        return date(current.year - 1, 12, 1)
    return date(current.year, current.month - 1, 1)


def month_windows(start: date, end: date) -> Iterable[MonthWindow]:
    if start > end:
        raise ValueError("--start cannot be after --end")
    cursor = start
    while cursor <= end:
        last = calendar.monthrange(cursor.year, cursor.month)[1]
        yield MonthWindow(cursor.strftime("%Y-%m"), cursor, cursor.replace(day=last))
        cursor = date(cursor.year + (cursor.month == 12), cursor.month % 12 + 1, 1)


def sql_date(value: date) -> str:
    return value.isoformat()


def pilot_window(window, days, start_day=1):
    if not days:
        if start_day != 1:
            raise ValueError('--pilot-start-day requires --pilot-days')
        return window
    last = calendar.monthrange(window.start.year, window.start.month)[1]
    if not 1 <= days <= 7 or start_day < 1 or start_day + days - 1 > last:
        raise ValueError('Pilot must fit within the selected month (1 to 7 days).')
    suffix = f'-pilot{days}d' + (f'-from{start_day:02d}' if start_day != 1 else '')
    return MonthWindow(window.label + suffix, window.start.replace(day=start_day),
                       window.start.replace(day=start_day + days - 1))


def build_gdelt_sql(window: MonthWindow, profile: str = "articles") -> str:
    """Build a compact article query or a separate strict-event cohort query."""
    from gdelt_queries import build_query, build_proxy_b_metrics_query
    if profile == 'proxy_b_metrics':
        from proxy_b import CATALOGUE, ROOT, load
        return build_proxy_b_metrics_query(window, load(ROOT / 'proxy_b_config.json'), load(CATALOGUE))
    return build_query(window, profile, INSTITUTION_THEME_RE)


def bytes_label(value: int) -> str:
    return f"{value / GIB:,.3f} GiB ({value / TIB:,.5f} TiB)"


def require_unbilled_project(project: str) -> None:
    """Read-only check; fail closed. Never enable APIs or change billing."""
    import google.auth
    from google.auth.transport.requests import AuthorizedSession
    from requests import RequestException
    credentials, _ = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
    try:
        with AuthorizedSession(credentials) as session:
            response = session.get(
                f'https://cloudbilling.googleapis.com/v1/projects/{project}/billingInfo', timeout=30
            )
            response.raise_for_status()
            info = response.json()
    except RequestException:
        # gcloud's own user login can read billingInfo even when the ADC quota
        # project cannot call this API. This is still only a read operation.
        executable = shutil.which('gcloud')
        if not executable:
            candidate = Path(os.environ.get('LOCALAPPDATA', '')) / 'Google/Cloud SDK/google-cloud-sdk/bin/gcloud.cmd'
            if candidate.is_file():
                executable = str(candidate)
        if not executable:
            raise RuntimeError('Cannot verify billing. No extraction started. gcloud is unavailable.')
        result = subprocess.run(
            [executable, 'billing', 'projects', 'describe', project, '--format=json', '--quiet'],
            capture_output=True, text=True, timeout=60, check=False,
            env={**os.environ, 'CLOUDSDK_CORE_DISABLE_PROMPTS': '1'},
        )
        if result.returncode:
            raise RuntimeError('Cannot verify billing using gcloud. No extraction started.')
        info = json.loads(result.stdout)
    validate_billing_info(info, project)


def validate_billing_info(info, project):
    if info.get('projectId') != project:
        raise RuntimeError('Billing response belongs to a different/unknown project.')
    if info.get('billingEnabled') is not False or info.get('billingAccountName'):
        raise RuntimeError('Blocked: project is billed or its unbilled state cannot be confirmed.')


def validate_estimates(estimates, per_query_cap, total_cap):
    if any(value is None or value < 0 for value in estimates):
        raise ValueError('Blocked: missing/invalid byte estimate.')
    if any(value > per_query_cap for value in estimates):
        raise ValueError('Blocked: at least one query exceeds --max-gib. No extraction started.')
    if sum(estimates) > total_cap:
        raise ValueError('Blocked: complete plan exceeds --max-total-gib. No extraction started.')


def run_gdelt(args: argparse.Namespace) -> int:
    if args.profile in ('candidates_themes', 'proxy_b_metrics'):
        from proxy_b import CATALOGUE, ROOT, load
        load(CATALOGUE)
        load(ROOT / 'proxy_b_config.json')
    try:
        import pandas as pd
        from google.cloud import bigquery
    except ImportError:
        print("Install dependency: python -m pip install google-cloud-bigquery pandas", file=sys.stderr)
        return 2

    output = Path(args.output) / args.profile
    output.mkdir(parents=True, exist_ok=True)
    client = bigquery.Client(project=args.project, location=args.location)
    planned = []
    report = []
    cached = []
    cap = int(args.max_gib * GIB)
    total_cap = int(args.max_total_gib * GIB)
    # Validate the WHOLE requested range before executing any query.
    for window in month_windows(args.start, args.end):
        window = pilot_window(window, args.pilot_days, getattr(args, 'pilot_start_day', 1))
        if window.end < GDELT_START:
            print(f"[{window.label}] skipped: before GDELT 2.0")
            continue
        sql = build_gdelt_sql(window, args.profile)
        fingerprint = hashlib.sha256(sql.encode()).hexdigest()[:20]
        stem = output / f'{window.label}_{fingerprint}'
        csv_path = stem.with_suffix('.csv')
        receipt = stem.with_suffix('.complete.json')
        reservation = stem.with_suffix('.reserved.json')
        stem.with_suffix('.sql').write_text(sql, encoding='utf-8')
        if receipt.exists() and csv_path.exists():
            saved = json.loads(receipt.read_text(encoding='utf-8'))
            if saved.get('csv_sha256') == hashlib.sha256(csv_path.read_bytes()).hexdigest():
                print(f'[{window.label}] verified local cache; no repeated query')
                cached.append(csv_path)
                report.append(dict(month=window.label, estimated_bytes=0, status='cached'))
                continue
        if reservation.exists():
            raise RuntimeError(f'Previous job needs review before retry: {reservation}')
        dry_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
        dry_job = client.query(sql, job_config=dry_config)
        if dry_job.total_bytes_processed is None:
            raise RuntimeError('BigQuery did not provide an estimate. Stopping safely.')
        estimate = int(dry_job.total_bytes_processed)
        print(f"[{window.label}] dry run: {bytes_label(estimate)}")
        report.append(dict(month=window.label, estimated_bytes=estimate, status='dry_run'))
        planned.append((window, sql, estimate, csv_path, receipt, reservation))
    pd.DataFrame(report).to_csv(output / 'dry_run_estimates.csv', index=False)
    print(f'Total planned: {bytes_label(sum(p[2] for p in planned))}')
    if not args.execute:
        print('Dry-run-only: no data query executed. Limits have not been increased.')
        return 0
    validate_estimates([p[2] for p in planned], cap, total_cap)
    planned_caps = [min(cap, max(10 * 1024**2, math.ceil(p[2] / 1024**2) * 1024**2))
                    for p in planned]
    validate_estimates(planned_caps, cap, total_cap)
    all_frames = [pd.read_csv(p) for p in cached]
    reserved_total = 0
    for window, sql, estimate, csv_path, receipt, reservation in planned:
        require_unbilled_project(args.project)
        # Reserve a bounded maximum BEFORE submission. Interrupted/uncertain
        # jobs are never automatically resubmitted on a later invocation.
        job_cap = min(cap, max(10 * 1024**2, math.ceil(estimate / 1024**2) * 1024**2))
        if reserved_total + job_cap > total_cap:
            raise RuntimeError('Rounded query caps exceed total budget; stopping.')
        reserved_total += job_cap
        job_id = 'gdelt_safe_' + uuid.uuid4().hex
        with reservation.open('x', encoding='utf-8') as handle:
            json.dump(dict(job_id=job_id, project=args.project, location=args.location,
                           maximum_bytes_billed=job_cap), handle)
        config = bigquery.QueryJobConfig(
            maximum_bytes_billed=job_cap,
            use_query_cache=True,
            labels={"project": "py_us_media", "month": window.label.replace("-", "_")},
        )
        job = client.query(sql, job_config=config, job_id=job_id, job_retry=None)
        frame = job.result().to_dataframe(create_bqstorage_client=False)
        frame["query_bytes_processed"] = int(job.total_bytes_processed or 0)
        frame["query_bytes_billed"] = int(job.total_bytes_billed or 0)
        frame.to_csv(csv_path, index=False, encoding="utf-8-sig")
        receipt.write_text(json.dumps(dict(job_id=job_id, project=args.project,
            profile=args.profile, window=window.label,
            completed_at=datetime.now().astimezone().isoformat(),
            sql_sha256=hashlib.sha256(sql.encode()).hexdigest(),
            csv_sha256=hashlib.sha256(csv_path.read_bytes()).hexdigest(),
            bytes_processed=int(job.total_bytes_processed or 0),
            bytes_billed=int(job.total_bytes_billed or 0))), encoding='utf-8')
        all_frames.append(frame)
        print(f"[{window.label}] saved {len(frame)} rows; billed {bytes_label(int(job.total_bytes_billed or 0))}")
        require_unbilled_project(args.project)
        print('Post-extraction safety check: billing disabled, no linked billing account.')

    if all_frames:
        combined = pd.concat(all_frames, ignore_index=True).sort_values(
            ["month", "source_country"] + (["direction"] if args.profile == 'events' else [])
        )
        tag = f'{args.start:%Y-%m}_{args.end:%Y-%m}'
        if args.pilot_days:
            tag += f'_pilot{args.pilot_days}d'
            if getattr(args, 'pilot_start_day', 1) != 1:
                tag += f'_from{args.pilot_start_day:02d}'
        combined.to_csv(output / f"monthly_{tag}.csv", index=False, encoding="utf-8-sig")
        print(f"Combined CSV: {output / f'monthly_{tag}.csv'}")
        if args.profile == 'candidates_themes':
            from proxy_b import process_csv
            result = process_csv(output / f'monthly_{tag}.csv')
            identity = hashlib.sha256((result['input_sha256'] + result['method_hash'] + result['catalogue_hash']).encode()).hexdigest()[:20]
            proxy_path = output / f'proxy_b_{tag}_{identity}.json'
            payload = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)
            if proxy_path.exists():
                if json.loads(proxy_path.read_text(encoding='utf-8')) != result:
                    raise RuntimeError('Existing proxy output differs; inspect before replacing.')
            else:
                proxy_path.write_text(payload, encoding='utf-8')
            print(f"Proxy B: {result['selected_count']} selected; {proxy_path}")
    return 0


TRENDS_TERMS: dict[str, list[str]] = {
    "US": [
        "Paraguay", "Paraguay trade", "Paraguay tariff", "Paraguay embassy",
        "Paraguay government", "Paraguay immigration", "Paraguay military",
        "US Paraguay relations", "US embassy Paraguay", "Paraguay Taiwan",
    ],
    "PY": [
        "Estados Unidos", "Embajada de Estados Unidos",
        "relaciones Paraguay Estados Unidos", "comercio Paraguay Estados Unidos",
        "aranceles Estados Unidos Paraguay", "cooperación Estados Unidos Paraguay",
        "USAID Paraguay", "migración Estados Unidos", "visa Estados Unidos",
        "seguridad Paraguay Estados Unidos", "DEA Paraguay",
    ],
}


def chunks(values: Sequence[str], size: int) -> Iterable[Sequence[str]]:
    for offset in range(0, len(values), size):
        yield values[offset : offset + size]


def run_trends(args: argparse.Namespace) -> int:
    """Extract independent country series through the unofficial pytrends client.

    Terms are not summed. Each batch includes a stable anchor, allowing later
    rescaling; raw 0--100 values and partial flags are retained.
    """
    try:
        import pandas as pd
        from pytrends.request import TrendReq
    except ImportError:
        print("Install dependency: python -m pip install pytrends pandas", file=sys.stderr)
        return 2

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    start = args.start.isoformat()
    end_day = args.end.replace(day=calendar.monthrange(args.end.year, args.end.month)[1]).isoformat()
    timeframe = f"{start} {end_day}"
    pytrends = TrendReq(hl="es", tz=300, retries=2, backoff_factor=0.5)
    frames: list[pd.DataFrame] = []

    for geo, terms in TRENDS_TERMS.items():
        anchor = terms[0]
        non_anchor = terms[1:]
        for batch_number, batch in enumerate(chunks(non_anchor, 4), start=1):
            keywords = [anchor, *batch]
            print(f"[{geo} batch {batch_number}] {keywords}")
            pytrends.build_payload(keywords, timeframe=timeframe, geo=geo)
            data = pytrends.interest_over_time().reset_index()
            if data.empty:
                print("  no data")
                continue
            long = data.melt(
                id_vars=["date", "isPartial"], var_name="term", value_name="interest_0_100"
            )
            long["geo"] = geo
            long["batch"] = batch_number
            long["anchor"] = anchor
            frames.append(long)
            time.sleep(args.pause)

    if not frames:
        print("Google Trends returned no observations.", file=sys.stderr)
        return 1
    result = pd.concat(frames, ignore_index=True)
    result.to_csv(output / "google_trends_raw.csv", index=False, encoding="utf-8-sig")
    monthly = result.copy()
    monthly["month"] = pd.to_datetime(monthly["date"]).dt.to_period("M").dt.to_timestamp()
    monthly = (
        monthly.groupby(["month", "geo", "batch", "anchor", "term"], as_index=False)
        .agg(interest_0_100=("interest_0_100", "mean"), is_partial=("isPartial", "max"))
        .sort_values(["geo", "term", "month"])
    )
    monthly.to_csv(output / "google_trends_monthly.csv", index=False, encoding="utf-8-sig")
    print(f"CSV: {output / 'google_trends_raw.csv'}")
    print(f"Monthly CSV: {output / 'google_trends_monthly.csv'}")
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    sub = result.add_subparsers(dest="command", required=True)

    gdelt = sub.add_parser("gdelt", help="Dry-run or execute monthly BigQuery extraction")
    gdelt.add_argument("--project", required=True, help="Your Google Cloud billing project ID")
    gdelt.add_argument("--start", type=parse_month, default=last_complete_month())
    gdelt.add_argument("--end", type=parse_month, default=last_complete_month())
    gdelt.add_argument("--location", default="US")
    gdelt.add_argument("--output", default="output/gdelt")
    gdelt.add_argument("--execute", action="store_true", help="Actually run queries; default is free dry runs")
    gdelt.add_argument("--max-gib", type=float, default=1.0, help="Hard billed-byte cap per month")
    gdelt.add_argument("--max-total-gib", type=float, default=1.0, help="Hard cumulative byte cap per run")
    gdelt.add_argument("--profile", choices=['articles', 'events', 'audit', 'candidates', 'candidates_themes', 'proxy_b_metrics'], default='candidates_themes', help='Default preserves candidates and applies proxy B locally; proxy_b_metrics returns aggregate metrics only')
    gdelt.add_argument("--pilot-days", type=int, choices=range(1, 8),
                       help="Extract N days, one month only; marked as incomplete")
    gdelt.add_argument('--pilot-start-day', type=int, default=1,
                       help='First day of pilot within selected month (default: 1)')
    gdelt.set_defaults(func=run_gdelt)

    trends = sub.add_parser("trends", help="Extract country-specific Google Trends series")
    trends.add_argument("--start", type=parse_month, default=date(2015, 3, 1))
    trends.add_argument("--end", type=parse_month, default=last_complete_month())
    trends.add_argument("--output", default="output/trends")
    trends.add_argument("--pause", type=float, default=3.0, help="Seconds between requests")
    trends.set_defaults(func=run_trends)
    return result


def main() -> int:
    args = parser().parse_args()
    for key in ('max_gib', 'max_total_gib'):
        value = getattr(args, key, 1)
        if not math.isfinite(value) or value <= 0:
            raise SystemExit(f'{key} must be finite and positive')
    if args.start > args.end or args.end > last_complete_month():
        raise SystemExit('Use an ordered range ending no later than the last complete month.')
    if args.command == 'gdelt' and not re.fullmatch(r'[a-z][a-z0-9-]{4,28}[a-z0-9]', args.project):
        raise SystemExit('Invalid project ID')
    if args.command == 'gdelt' and args.pilot_days and args.start != args.end:
        raise SystemExit('A pilot must use the same start and end month.')
    if args.command == 'gdelt':
        pilot_window(next(month_windows(args.start, args.end)), args.pilot_days, args.pilot_start_day)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
