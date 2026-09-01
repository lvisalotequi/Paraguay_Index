import csv
import hashlib
import json
import unittest
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlsplit
from institutional_proxy_rule import classify


class AprilContrastTests(unittest.TestCase):
    def test_frozen_contrast(self):
        root = Path(__file__).parent
        def read(path):
            return json.loads((root / path).read_text(encoding='utf-8'))
        saved = read('output/rule_contrast_april_v1/contrast.json')
        path = root / 'output/theme_estimates_v1/april_pilot/candidates_themes/2025-04-pilot3d-from04_efc7321c426cb3c7babe.csv'
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), saved['csv_sha256'])
        self.assertEqual(hashlib.sha256((root / 'institutional_proxy_rule_v1.json').read_bytes()).hexdigest(), saved['rule_sha256'])
        with path.open(encoding='utf-8-sig', newline='') as f:
            data = list(csv.DictReader(f))
        raw = {r['url']: r for r in data}
        self.assertEqual(len(raw), len(data))
        self.assertEqual(len(raw), 88)
        self.assertEqual(set(raw), {r['url'] for r in saved['rows']})
        with (root / 'output/pilot_2025_04_04_06/candidates/2025-04-pilot3d-from04_a0fe4cccdbe3b2f321f4.csv').open(encoding='utf-8-sig', newline='') as f:
            previous = {r['url']: r for r in csv.DictReader(f)}
        self.assertEqual(set(raw), set(previous))
        labels = {r['url']: r for r in read('output/recovery_pilots_v2/sample_review.json')['articles'] if r['pilot'] == '2025-04-04_06'}
        catalogue = {s['domain']: s for s in read('output/pilot_2025_01_04_06/media_catalogue_v2.json')['sources']}
        counts = defaultdict(Counter)
        for r in saved['rows']:
            row = raw[r['url']]
            for field in ('observed_at', 'language', 'url_key', 'source_country'):
                self.assertEqual(row[field], previous[r['url']][field])
            source = catalogue.get((urlsplit(r['url']).hostname or '').removeprefix('www.'), {})
            base = source.get('verification_status') == 'verified' and source.get('country_verified') in ('PY', 'US') and row['language'] in ('eng', 'spa')
            result = classify(row['themes'], base)
            self.assertEqual(result['group'], r['group'])
            self.assertEqual(classify(row['themes'], True)['hits'], r['hits'])
            ref = labels.get(r['url'])
            self.assertEqual(ref is None, r['reference'] is None)
            if ref:
                self.assertEqual(ref['decision'], r['reference']['decision'])
                self.assertEqual(ref['id'], r['reference']['id'])
            counts[r['group']][ref['decision'] if ref else 'unreviewed'] += 1
        self.assertEqual(sum(r['reference'] is not None for r in saved['rows']), 20)
        for group, values in saved['groups'].items():
            for label, count in values.items():
                self.assertEqual(counts[group][label], count)
        self.assertEqual(counts['core_proxy']['include'], 0)
        self.assertEqual(counts['extended_only']['include'], 2)
