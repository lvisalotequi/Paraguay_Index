"""Offline, reproducible two-stage recovery pilot. Never queries BigQuery.

New pilots: sample 10 candidates per historical source-country stratum before
screening. January: sample up to 5 access-problem cases per stratum. Stable
SHA256 ranking freezes selection independently of accessibility and relevance.
Unreviewed candidates are NOT classified as doubtful.
"""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SEED = 'leandro-recovery-2026-08-27-v1'


def sample(rows, n, pilot):
    if len({r['url'] for r in rows}) != len(rows):
        raise ValueError('Duplicate URLs in sampling frame')
    return sorted(rows, key=lambda r: hashlib.sha256(
        f"{SEED}|{pilot}|{r['url']}".encode()).hexdigest())[:n]


def manifest():
    baseline = json.loads((ROOT / 'output/pilot_2025_01_04_06/review_complete_v1.json').read_text(encoding='utf-8'))
    old = {r['url']: r for r in baseline['articles']}
    samples, strata = [], []
    for month in ('01', '04', '07'):
        pilot = f'2025-{month}-04_06'
        path = ROOT / f'output/pilot_2025_{month}_04_06/candidates/monthly_2025-{month}_2025-{month}_pilot3d_from04.csv'
        with path.open(encoding='utf-8-sig', newline='') as handle:
            rows = [dict(r, id=i) for i, r in enumerate(csv.DictReader(handle), 1)]
        for country in ('PY', 'US'):
            pool = [r for r in rows if r['source_country'] == country]
            if month == '01':
                pool = [r for r in pool if old[r['url']]['decision'] == 'doubtful'
                        and old[r['url']]['content_access'] in ('unavailable', 'changed')]
            selected = sample(pool, 5 if month == '01' else 10, pilot)
            strata.append(dict(pilot=pilot, source_country_gdelt=country,
                               frame='access_doubts' if month == '01' else 'all_candidates',
                               population=len(pool), sample_size=len(selected)))
            for row in selected:
                samples.append(dict(pilot=pilot, id=row['id'], url=row['url'],
                    domain=row['domain'], source_country_gdelt=country,
                    inclusion_probability=len(selected)/len(pool),
                    initial_decision='doubtful' if month == '01' else 'unreviewed',
                    previous_review=old.get(row['url']) if month == '01' else None))
    return dict(seed=SEED, strata=strata, articles=samples)


def outcome_bounds(valid, excluded, unresolved):
    """Identification bounds in the reviewed sample, NOT confidence intervals."""
    if any(not isinstance(n, int) or n < 0 for n in (valid, excluded, unresolved)):
        raise ValueError('Counts must be nonnegative integers')
    n = valid + excluded + unresolved
    return dict(n=n, confirmed_fraction=valid/n if n else None,
                possible_fraction=(valid+unresolved)/n if n else None)


if __name__ == '__main__':
    print(json.dumps(manifest(), ensure_ascii=False, indent=2))
