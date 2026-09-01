"""Offline, fail-closed selection. Unreviewed/doubtful rows never enter metrics.

No network, no cloud queries, no file writes. CLI emits JSON to stdout.
"""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit


def select(rows, reviews, catalogue):
    sources = {s['domain']: s for s in catalogue['sources']}
    annotations = {r['url']: r for r in reviews['articles']}
    if len(annotations) != len(reviews['articles']):
        raise ValueError('Duplicate review URL')
    urls = {r['url'] for r in rows}
    if len(urls) != len(rows) or not set(annotations) <= urls:
        raise ValueError('Duplicate input or review URL missing from input')
    selected, audit = [], []
    for row in rows:
        review = annotations.get(row['url'], {})
        host = (urlsplit(row['url']).hostname or '').removeprefix('www.')
        source = sources.get(host, {})
        country = source.get('country_verified')
        accepted = (review.get('decision') == 'include'
                    and review.get('content_access') == 'full'
                    and review.get('focus') in ('central', 'contextual')
                    and bool(review.get('reason'))
                    and bool(review.get('evidence_urls'))
                    and source.get('verification_status') == 'verified'
                    and country in ('PY', 'US')
                    and row['language'] in ('eng', 'spa'))
        audit.append(dict(url=row['url'], decision=review.get('decision', 'pending'),
                          eligible_for_confirmed_metrics=accepted,
                          source_country_verified=country))
        if accepted:
            selected.append({**row, 'selection_status': 'reviewed_valid',
                             'source_country_verified': country, 'review': review})
    return dict(selection='include_only', counts=dict(Counter(r['decision'] for r in audit)),
                selected_count=len(selected), articles=selected, audit=audit,
                note='Incomplete review is not an estimate of precision or recall. Tone describes the whole document.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv')
    parser.add_argument('review')
    parser.add_argument('catalogue')
    args = parser.parse_args()
    with open(args.csv, encoding='utf-8-sig', newline='') as handle:
        rows = list(csv.DictReader(handle))
    print(json.dumps(select(rows, json.loads(Path(args.review).read_text(encoding='utf-8')),
                            json.loads(Path(args.catalogue).read_text(encoding='utf-8'))),
                     ensure_ascii=False, indent=2))
