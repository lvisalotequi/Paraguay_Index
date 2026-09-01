"""Accepted B proxy. Offline processing; no cloud or article retrieval.

Input must be a completed cooccurrence extraction (audit/candidates_themes).
Outputs never overwrite raw data or human relevance adjudications.
"""
import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
CATALOGUE = ROOT / 'output/pilot_2025_01_04_06/media_catalogue_v2.json'


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def fingerprint(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def process(rows, catalogue=None, config=None):
    catalogue = load(CATALOGUE) if catalogue is None else catalogue
    config = load(ROOT / 'proxy_b_config.json') if config is None else config
    sources = {s['domain']: s for s in catalogue['sources']}
    if len(sources) != len(catalogue['sources']):
        raise ValueError('Duplicate source domain')
    required = {'month', 'url', 'url_key', 'observed_at', 'language', 'themes', 'period_start', 'period_end', 'partial_month'}
    if any(not required <= row.keys() for row in rows):
        raise ValueError('Input lacks required cooccurrence metadata, including Themes')
    audit, unique = [], {}
    for row in sorted(rows, key=lambda r: (str(r['observed_at']), r['url'])):
        key = (row['month'], row['url_key'])
        if key not in unique:
            unique[key] = row
    for row in unique.values():
        host = (urlsplit(row['url']).hostname or '').removeprefix('www.')
        source = sources.get(host, {})
        country = source.get('country_verified')
        valid_source = source.get('verification_status') == 'verified' and country in ('PY', 'US')
        text = row['themes']
        tokens = {t.strip() for t in text.split(';') if t.strip()} if isinstance(text, str) else set()
        hits = {k: [t for t in config[k] if t in tokens] for k in ('D', 'I', 'R', 'E')}
        eligible = bool(valid_source and row['language'] in ('eng', 'spa') and tokens)
        selected = bool(eligible and (hits['D'] or (hits['I'] and (hits['R'] or hits['E']))))
        reason = ('proxy_b_selected' if selected else 'source_not_verified_in_scope' if not valid_source else
                  'language_out_of_scope' if row['language'] not in ('eng', 'spa') else
                  'missing_theme_signals' if not tokens else 'rule_not_matched')
        audit.append(dict(row, proxy_b_selected=selected, proxy_reason=reason,
                          source_country_verified=country, matched_themes=hits,
                          selection_status='proxy_b_unvalidated' if selected else 'not_selected_by_proxy_b'))
    selected = [r for r in audit if r['proxy_b_selected']]
    metrics = []
    for month in sorted({r['month'] for r in audit}):
        window = [r for r in audit if r['month'] == month]
        periods = {(r['period_start'], r['period_end'], str(r['partial_month']).lower()) for r in window}
        if len(periods) != 1:
            raise ValueError('Mixed extraction windows within month')
        start, end, partial = next(iter(periods))
        for country in ('PY', 'US', 'BOTH'):
            subset = [r for r in selected if r['month'] == month and (country == 'BOTH' or r['source_country_verified'] == country)]
            item = dict(month=month, source_country=country, period_start=start, period_end=end,
                        partial_month=partial == 'true', proxy_articles=len(subset),
                        unique_domains=len({urlsplit(r['url']).hostname for r in subset}))
            for field in ('tone', 'positive_score', 'negative_score'):
                values = [number(r.get(field)) for r in subset]
                values = [v for v in values if v is not None]
                item[field + '_n'] = len(values)
                item[field + '_mean'] = sum(values) / len(values) if values else None
            metrics.append(item)
    return dict(method=config, method_hash=fingerprint(config), catalogue_hash=fingerprint(catalogue),
                input_rows=len(rows), deduplicated_rows=len(audit), selected_count=len(selected),
                reason_counts=dict(Counter(r['proxy_reason'] for r in audit)),
                metrics=metrics, articles=selected, audit=audit,
                note='Exploratory proxy, not validated articles. Country is source origin, not relation direction. No rows means unknown window; no synthetic zero months.')


def process_csv(path, output=None):
    path = Path(path)
    with path.open(encoding='utf-8-sig', newline='') as handle:
        result = process(list(csv.DictReader(handle)))
    result['input_file'] = str(path.resolve())
    result['input_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    if output is not None:
        target = Path(output)
        if target.exists() or target.resolve() == path.resolve():
            raise FileExistsError('Refusing to overwrite an existing file')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    result = process_csv(args.csv, args.output)
    print(f"Proxy B: {result['selected_count']} selected / {result['deduplicated_rows']} candidates. Saved {args.output}")
