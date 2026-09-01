"""Offline summary; JSON stdout only. Recovery fractions are not imputations."""
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from recovery_sampling import ROOT, manifest, outcome_bounds
from review_candidate_gate import select


def summarize(review_folder=None):
    folder = ROOT / 'output/recovery_pilots_v1' if review_folder is None else Path(review_folder)
    saved_manifest = json.loads((ROOT / 'output/recovery_pilots_v1/sample_manifest.json').read_text(encoding='utf-8'))
    if saved_manifest != manifest():
        raise ValueError('Frozen sampling frame changed')
    reviewed = json.loads((folder / 'sample_review.json').read_text(encoding='utf-8'))['articles']
    expected = {(r['pilot'], r['id'], r['url']) for r in saved_manifest['articles']}
    if len(reviewed) != len(expected) or {(r['pilot'], r['id'], r['url']) for r in reviewed} != expected:
        raise ValueError('Review must cover exactly the frozen sample')
    catalogue = json.loads((ROOT / 'output/pilot_2025_01_04_06/media_catalogue_v2.json').read_text(encoding='utf-8'))
    pilots, selected = [], []
    for month in ('01', '04', '07'):
        pilot = f'2025-{month}-04_06'
        candidates = ROOT / f'output/pilot_2025_{month}_04_06/candidates'
        receipts = list(candidates.glob('*.complete.json'))
        if len(receipts) != 1:
            raise ValueError('Expected one completed data query per pilot')
        receipt = receipts[0]
        raw_path = receipt.with_name(receipt.name.replace('.complete.json', '.csv'))
        info = json.loads(receipt.read_text(encoding='utf-8'))
        if hashlib.sha256(raw_path.read_bytes()).hexdigest() != info['csv_sha256']:
            raise ValueError('Raw receipt hash mismatch')
        with raw_path.open(encoding='utf-8-sig', newline='') as handle:
            raw = list(csv.DictReader(handle))
        sample = [r for r in reviewed if r['pilot'] == pilot]
        if any(not r['reason'] or not r['evidence_urls'] for r in sample):
            raise ValueError('Missing evidence')
        if month != '01':
            gate = select(raw, dict(articles=sample), catalogue)
            selected.extend(dict(r, pilot=pilot) for r in gate['articles'])
        strata = []
        for country in ('PY', 'US'):
            recovery = [r for r in sample if r['source_country_gdelt'] == country and r['recovery_attempted']]
            counts = Counter(r['decision'] for r in recovery)
            strata.append(dict(source_country_gdelt=country,
                recovery_decisions=dict(counts),
                bounds_within_reviewed_sample=outcome_bounds(counts['include'], counts['exclude'], counts['doubtful'])))
        pilots.append(dict(pilot=pilot, downloaded_candidates=len(raw),
            sample_size=len(sample), sample_decisions=dict(Counter(r['decision'] for r in sample)),
            unsampled_candidates=len(raw)-len(sample),
            note='January sample is drawn from existing access doubts, not all candidates.' if month=='01' else 'Unsampled candidates remain unreviewed.',
            recovery_attempted=sum(r['recovery_attempted'] for r in sample),
            recovered_texts=sum(r['content_access']=='recovered' for r in sample),
            recovery_strata=strata, raw_csv_bytes=raw_path.stat().st_size,
            query_bytes_billed=info['bytes_billed'], csv_sha256=info['csv_sha256']))
    return dict(pilots=pilots, new_query_bytes_billed=sum(p['query_bytes_billed'] for p in pilots[1:]),
        new_confirmed_articles=selected,
        general_recovery_percentage=None,
        conclusion='Insufficient resolved cases for a general salvage percentage. Bounds describe sampled cases, not population confidence intervals. Never impute tone or promote unverified URLs.')


if __name__ == '__main__':
    print(json.dumps(summarize(), ensure_ascii=False, indent=2))
